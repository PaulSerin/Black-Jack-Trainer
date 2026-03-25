"""
simulator.py — Moteur Monte Carlo (basic strategy uniquement).

Usage CLI :
    python -m simulation.simulator --hands 500000 --spread 1-12 --unit-size 25
    python -m simulation.simulator --hands 100000 --spread 1-4 --bankroll 50000
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple

from simulation.config import BettingConfig, SimConfig, SimulationResult, TableRules
from simulation.betting import BettingRamp, compute_bet
from simulation.counting import HiLoCounter
from simulation.engine import (
    Card, Hand, Shoe,
    can_split, can_double, can_surrender,
    split_hand, dealer_must_hit, compute_hand_result,
)
from simulation.strategy import get_basic_strategy, HARD_STRATEGY, _normalize_upcard


# ---------------------------------------------------------------------------
# Résolution d'action (stratégie → action réalisable)
# ---------------------------------------------------------------------------

def _resolve_action(
    action: str,
    hand: Hand,
    dealer_upcard: Card,
    rules: TableRules,
    num_split_hands: int,
) -> str:
    """
    Traduit une action de stratégie en action réalisable selon les règles.

    - D / Ds  → double si disponible, sinon H (D) ou S (Ds)
    - SUR     → surrender si autorisé et main initiale, sinon H
    - Y       → split si possible, sinon lookup hard total
    - Y/N     → split SEULEMENT si DAS autorisé (rules.double_after_split),
                sinon lookup hard total
    """
    if action in ("D", "Ds"):
        if can_double(hand):
            return "D"
        return "S" if action == "Ds" else "H"

    if action == "SUR":
        if rules.surrender_allowed and can_surrender(hand, dealer_upcard):
            return "SUR"
        return "H"

    if action == "Y":
        if can_split(hand) and num_split_hands < rules.max_split_hands:
            return "Y"
        return _hard_fallback(hand, dealer_upcard)

    if action == "Y/N":
        # Y/N = split seulement si DAS autorisé
        if (rules.double_after_split
                and can_split(hand)
                and num_split_hands < rules.max_split_hands):
            return "Y"
        return _hard_fallback(hand, dealer_upcard)

    return action


def _hard_fallback(hand: Hand, dealer_upcard: Card) -> str:
    """Hard total lookup (ignore la paire pour éviter la récursion)."""
    upcard = _normalize_upcard(dealer_upcard.rank)
    total  = hand.value
    if total <= 7:
        return "H"
    if total >= 18:
        return "S"
    return HARD_STRATEGY.get((total, upcard), "S")


# ---------------------------------------------------------------------------
# Jeu d'une main (récursif pour les splits)
# ---------------------------------------------------------------------------

def _play_hand(
    hand: Hand,
    dealer_upcard: Card,
    shoe: Shoe,
    counter: HiLoCounter,
    rules: TableRules,
    bet: float,
    num_split_hands: int = 1,
) -> List[Tuple[Hand, float]]:
    """
    Joue une main jusqu'à la fin (basic strategy).
    Met à jour le counter pour chaque carte tirée.
    Retourne une liste de (Hand, mise_finale).
    """
    while True:
        action = _resolve_action(
            get_basic_strategy(hand, dealer_upcard),
            hand, dealer_upcard, rules, num_split_hands,
        )

        if action == "SUR":
            return [(hand, bet * 0.5)]

        if action == "Y":
            hand1, hand2 = split_hand(hand, shoe)
            # Les 2 nouvelles cartes (une par main) viennent d'être tirées : les compter
            counter.update(hand1.cards[-1])
            counter.update(hand2.cards[-1])
            new_count = num_split_hands + 1
            return (
                _play_hand(hand1, dealer_upcard, shoe, counter, rules, bet, new_count)
                + _play_hand(hand2, dealer_upcard, shoe, counter, rules, bet, new_count)
            )

        if action == "D":
            card = shoe.deal()
            counter.update(card)
            hand.add_card(card)
            hand.doubled = True
            return [(hand, bet * 2)]

        if action == "H":
            card = shoe.deal()
            counter.update(card)
            hand.add_card(card)
            if hand.is_bust:
                return [(hand, bet)]
            continue  # prochaine action

        # Stand (ou fallback)
        return [(hand, bet)]


# ---------------------------------------------------------------------------
# Simulation principale
# ---------------------------------------------------------------------------

def simulate(config: SimConfig) -> SimulationResult:
    """Lance une simulation Monte Carlo et retourne les métriques."""
    if config.seed is not None:
        random.seed(config.seed)

    shoe    = Shoe(num_decks=config.decks, penetration=config.penetration)
    counter = HiLoCounter()
    ramp    = BettingRamp()

    bankroll      = config.initial_bankroll
    total_profit  = 0.0
    total_wagered = 0.0
    max_bankroll  = bankroll
    min_bankroll  = bankroll

    wins = losses = pushes = blackjacks = surrenders = busts = 0
    positive_tc_rounds = 0

    # Welford en ligne pour l'écart-type du profit par round
    welf_n, welf_mean, welf_M2 = 0, 0.0, 0.0

    rounds_played = 0

    for _ in range(config.hands):
        if shoe.needs_shuffle:
            shoe.shuffle()
            counter.reset()

        tc  = counter.true_count(shoe)
        bet = compute_bet(tc, config.betting, ramp)

        if tc > 0:
            positive_tc_rounds += 1

        # ── Donne initiale ──────────────────────────────────────────────────
        # Convention américaine :
        #   P1 (face up) → D1/upcard (face up) → P2 (face up) → D2/hole (face down)
        # On compte P1, D1(upcard), P2 immédiatement (visibles).
        # La hole card (D2) est comptée après le jeu du joueur, à sa révélation.
        player_hand = Hand()
        dealer_hand = Hand()

        p1 = shoe.deal(); counter.update(p1); player_hand.add_card(p1)
        d1 = shoe.deal(); counter.update(d1); dealer_hand.add_card(d1)   # upcard
        p2 = shoe.deal(); counter.update(p2); player_hand.add_card(p2)
        d2 = shoe.deal();                     dealer_hand.add_card(d2)   # hole card — pas encore comptée

        dealer_upcard = dealer_hand.cards[0]  # d1 = upcard visible

        # ── Blackjack joueur ────────────────────────────────────────────────
        if player_hand.is_blackjack:
            counter.update(d2)   # hole card révélée
            if dealer_hand.is_blackjack:
                profit = 0.0
                pushes += 1
            else:
                profit = bet * config.rules.blackjack_payout
                blackjacks += 1
                wins += 1
            bankroll     += profit
            total_profit += profit
            total_wagered += bet
            rounds_played += 1
            welf_n, welf_mean, welf_M2 = _welford(welf_n, welf_mean, welf_M2, profit)
            max_bankroll = max(max_bankroll, bankroll)
            min_bankroll = min(min_bankroll, bankroll)
            continue

        # ── Blackjack dealer ────────────────────────────────────────────────
        if dealer_hand.is_blackjack:
            counter.update(d2)   # hole card révélée
            profit = -bet
            losses += 1
            bankroll     += profit
            total_profit += profit
            total_wagered += bet
            rounds_played += 1
            welf_n, welf_mean, welf_M2 = _welford(welf_n, welf_mean, welf_M2, profit)
            max_bankroll = max(max_bankroll, bankroll)
            min_bankroll = min(min_bankroll, bankroll)
            continue

        # ── Le joueur joue (hole card encore inconnue) ──────────────────────
        hand_results = _play_hand(player_hand, dealer_upcard, shoe, counter, config.rules, bet)

        # Hole card révélée maintenant
        counter.update(d2)

        # Surrender détecté : une seule main 2 cartes, mise = bet/2
        is_surrender = (
            len(hand_results) == 1
            and hand_results[0][1] == bet * 0.5
            and len(hand_results[0][0].cards) == 2
        )
        if is_surrender:
            profit = -(bet * 0.5)
            surrenders += 1
            losses += 1
            bankroll     += profit
            total_profit += profit
            total_wagered += bet
            rounds_played += 1
            welf_n, welf_mean, welf_M2 = _welford(welf_n, welf_mean, welf_M2, profit)
            max_bankroll = max(max_bankroll, bankroll)
            min_bankroll = min(min_bankroll, bankroll)
            continue

        # ── Le dealer joue ──────────────────────────────────────────────────
        while dealer_must_hit(dealer_hand, config.rules.dealer_hits_soft_17):
            card = shoe.deal()
            counter.update(card)
            dealer_hand.add_card(card)

        # ── Résultats ───────────────────────────────────────────────────────
        hand_profit  = 0.0
        hand_wagered = 0.0

        for h, final_bet in hand_results:
            hand_wagered += final_bet
            result = compute_hand_result(h, dealer_hand)

            if result == "blackjack":
                p = final_bet * config.rules.blackjack_payout
                blackjacks += 1
                wins += 1
            elif result == "win":
                p = final_bet
                wins += 1
            elif result == "push":
                p = 0.0
                pushes += 1
            elif result == "bust":
                p = -final_bet
                busts += 1
                losses += 1
            else:  # lose
                p = -final_bet
                losses += 1

            hand_profit += p

        bankroll     += hand_profit
        total_profit += hand_profit
        total_wagered += hand_wagered
        rounds_played += 1
        welf_n, welf_mean, welf_M2 = _welford(welf_n, welf_mean, welf_M2, hand_profit)
        max_bankroll = max(max_bankroll, bankroll)
        min_bankroll = min(min_bankroll, bankroll)

    # ── Métriques finales ────────────────────────────────────────────────────
    profit_std       = math.sqrt(welf_M2 / welf_n) if welf_n > 1 else 0.0
    profit_std_units = profit_std / config.betting.unit_size if config.betting.unit_size else 0.0
    ev_per_round     = total_profit / rounds_played if rounds_played else 0.0
    ev_percent       = (total_profit / total_wagered * 100) if total_wagered else 0.0
    avg_bet          = total_wagered / rounds_played if rounds_played else 0.0
    pos_tc_ratio     = positive_tc_rounds / rounds_played if rounds_played else 0.0

    return SimulationResult(
        hands_played      = rounds_played,
        strategy_mode     = "basic",
        decks             = config.decks,
        penetration       = config.penetration,
        total_profit      = total_profit,
        total_wagered     = total_wagered,
        ev_per_hand       = ev_per_round,
        ev_per_100_hands  = ev_per_round * 100,
        ev_percent        = ev_percent,
        average_bet       = avg_bet,
        final_bankroll    = bankroll,
        max_bankroll      = max_bankroll,
        min_bankroll      = min_bankroll,
        wins              = wins,
        losses            = losses,
        pushes            = pushes,
        blackjacks        = blackjacks,
        surrenders        = surrenders,
        busts             = busts,
        positive_tc_hands = positive_tc_rounds,
        positive_tc_ratio = pos_tc_ratio,
        profit_std        = profit_std,
        profit_std_units  = profit_std_units,
    )


# ---------------------------------------------------------------------------
# Welford online algorithm
# ---------------------------------------------------------------------------

def _welford(n: int, mean: float, M2: float, x: float) -> tuple[int, float, float]:
    n    += 1
    delta = x - mean
    mean += delta / n
    M2   += delta * (x - mean)
    return n, mean, M2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Blackjack Monte Carlo — Basic Strategy")
    parser.add_argument("--hands",     type=int,   default=500_000)
    parser.add_argument("--spread",    type=str,   default="1-1",
                        help="Bet spread ex. '1-12' (defaut: flat 1-1)")
    parser.add_argument("--unit-size", type=float, default=25.0)
    parser.add_argument("--bankroll",  type=float, default=500_000.0)
    parser.add_argument("--decks",     type=int,   default=6)
    parser.add_argument("--pen",       type=float, default=0.75)
    parser.add_argument("--seed",      type=int,   default=None)
    parser.add_argument("--h17",       action="store_true",
                        help="Dealer hits soft 17 (defaut: S17)")
    args = parser.parse_args()

    betting = BettingConfig.from_string(args.spread, unit_size=args.unit_size)
    rules   = TableRules(dealer_hits_soft_17=args.h17)

    config = SimConfig(
        hands            = args.hands,
        decks            = args.decks,
        penetration      = args.pen,
        betting          = betting,
        rules            = rules,
        initial_bankroll = args.bankroll,
        seed             = args.seed,
    )

    print(f"Simulation en cours ({config.hands:,} rounds, spread {args.spread}, "
          f"unit {args.unit_size}EUR, bankroll {args.bankroll:,.0f}EUR)...")
    result = simulate(config)
    print(result.summary())
