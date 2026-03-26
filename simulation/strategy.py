"""
strategy.py — Basic strategy complète pour 6 decks, dealer stands on soft 17.

Source : https://wizardofodds.com/games/blackjack/strategy/6-decks/

Actions :
  H   = Hit
  S   = Stand
  D   = Double if allowed, otherwise Hit
  Ds  = Double if allowed, otherwise Stand
  SUR = Late Surrender (si non dispo : H pour 15, H pour 16)
  Y   = Split
  Y/N = Split seulement si DAS autorisé
  N   = Ne pas splitter (traiter comme hard total)

Point d'entrée principal : get_basic_strategy(hand, dealer_upcard)
"""

from __future__ import annotations

import argparse

from simulation.engine import Card, Hand


# ---------------------------------------------------------------------------
# Normalisation du rang de l'upcard
# J, Q, K ont la même valeur que "10" — les tables utilisent "10"
# ---------------------------------------------------------------------------

def _normalize_upcard(rank: str) -> str:
    """Retourne '10' pour J, Q, K ; inchangé pour les autres rangs."""
    return "10" if rank in ("J", "Q", "K") else rank


# ---------------------------------------------------------------------------
# Colonnes upcard (2 à A — "10" représente toutes les cartes de valeur 10)
# ---------------------------------------------------------------------------

UPCARDS: tuple[str, ...] = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "A")


# ---------------------------------------------------------------------------
# HARD_STRATEGY
# Clé   : (player_total: int, dealer_upcard_rank: str)  — upcard normalisé
# Totaux couverts : 8–17  (≤7 → H, ≥18 → S par défaut)
# ---------------------------------------------------------------------------

_HARD_ROWS: dict[int, list[str]] = {
    #          2     3     4     5     6     7     8     9    10     A
    8:  ["H", "H",  "H",  "H",  "H",  "H",  "H",  "H",  "H",  "H"],
    9:  ["H", "D",  "D",  "D",  "D",  "H",  "H",  "H",  "H",  "H"],
    10: ["D", "D",  "D",  "D",  "D",  "D",  "D",  "D",  "H",  "H"],
    11: ["D", "D",  "D",  "D",  "D",  "D",  "D",  "D",  "D",  "H"],
    12: ["H", "H",  "S",  "S",  "S",  "H",  "H",  "H",  "H",  "H"],
    13: ["S", "S",  "S",  "S",  "S",  "H",  "H",  "H",  "H",  "H"],
    14: ["S", "S",  "S",  "S",  "S",  "H",  "H",  "H",  "H",  "H"],
    15: ["S", "S",  "S",  "S",  "S",  "H",  "H",  "H",  "SUR","SUR"],
    16: ["S", "S",  "S",  "S",  "S",  "H",  "H",  "SUR","SUR","SUR"],
    17: ["S", "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S"],
}

HARD_STRATEGY: dict[tuple[int, str], str] = {
    (total, upcard): action
    for total, row in _HARD_ROWS.items()
    for upcard, action in zip(UPCARDS, row)
}


# ---------------------------------------------------------------------------
# SOFT_STRATEGY
# Clé : (non_ace_value: int, dealer_upcard_rank: str)  — upcard normalisé
# non_ace_value = valeur de la carte non-As : A,2 → 2 … A,9 → 9
# ---------------------------------------------------------------------------

_SOFT_ROWS: dict[int, list[str]] = {
    #          2     3     4     5     6     7     8     9    10     A
    2:  ["H", "H",  "H",  "D",  "D",  "H",  "H",  "H",  "H",  "H"],   # A,2 (soft 13)
    3:  ["H", "H",  "H",  "D",  "D",  "H",  "H",  "H",  "H",  "H"],   # A,3 (soft 14)
    4:  ["H", "H",  "D",  "D",  "D",  "H",  "H",  "H",  "H",  "H"],   # A,4 (soft 15)
    5:  ["H", "H",  "D",  "D",  "D",  "H",  "H",  "H",  "H",  "H"],   # A,5 (soft 16)
    6:  ["H", "D",  "D",  "D",  "D",  "H",  "H",  "H",  "H",  "H"],   # A,6 (soft 17)
    7:  ["Ds","Ds", "Ds", "Ds", "Ds", "S",  "S",  "H",  "H",  "H"],   # A,7 (soft 18)
    8:  ["S", "S",  "S",  "S",  "Ds", "S",  "S",  "S",  "S",  "S"],   # A,8 (soft 19)
    9:  ["S", "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S"],   # A,9 (soft 20)
}

SOFT_STRATEGY: dict[tuple[int, str], str] = {
    (nav, upcard): action
    for nav, row in _SOFT_ROWS.items()
    for upcard, action in zip(UPCARDS, row)
}


# ---------------------------------------------------------------------------
# SPLIT_STRATEGY
# Clé : (pair_card_value: int, dealer_upcard_rank: str)  — upcard normalisé
# pair_card_value : valeur d'une carte de la paire (As=11, figures=10)
# ---------------------------------------------------------------------------

_SPLIT_ROWS: dict[int, list[str]] = {
    #           2      3      4      5      6      7      8      9     10      A
    11: ["Y",  "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y"],   # A,A
    10: ["N",  "N",   "N",   "N",   "N",   "N",   "N",   "N",   "N",   "N"],   # 10,10
     9: ["Y",  "Y",   "Y",   "Y",   "Y",   "S",   "Y",   "Y",   "S",   "S"],   # 9,9
     8: ["Y",  "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y"],   # 8,8
     7: ["Y",  "Y",   "Y",   "Y",   "Y",   "Y",   "N",   "N",   "N",   "N"],   # 7,7
     6: ["Y/N","Y",   "Y",   "Y",   "Y",   "N",   "N",   "N",   "N",   "N"],   # 6,6
     5: ["N",  "N",   "N",   "N",   "N",   "N",   "N",   "N",   "N",   "N"],   # 5,5
     4: ["N",  "N",   "N",   "Y/N", "Y/N", "N",   "N",   "N",   "N",   "N"],   # 4,4
     3: ["Y/N","Y/N", "Y",   "Y",   "Y",   "Y",   "N",   "N",   "N",   "N"],   # 3,3
     2: ["Y/N","Y/N", "Y",   "Y",   "Y",   "Y",   "N",   "N",   "N",   "N"],   # 2,2
}

SPLIT_STRATEGY: dict[tuple[int, str], str] = {
    (pv, upcard): action
    for pv, row in _SPLIT_ROWS.items()
    for upcard, action in zip(UPCARDS, row)
}


# ---------------------------------------------------------------------------
# SURRENDER (index rapide — déjà intégré dans HARD_STRATEGY via "SUR")
# ---------------------------------------------------------------------------

SURRENDER: dict[tuple[int, str], bool] = {
    (16, "9"): True,
    (16, "10"): True,
    (16, "A"): True,
    (15, "10"): True,
    (15, "A"): True,
}


# ---------------------------------------------------------------------------
# get_basic_strategy — point d'entrée principal
# ---------------------------------------------------------------------------

def get_basic_strategy(hand: Hand, dealer_upcard: Card) -> str:
    """
    Retourne l'action de basic strategy pour une main donnée.

    Priorité :
      1. Paires    → SPLIT_STRATEGY (si action != "N")
      2. Mains soft → SOFT_STRATEGY
      3. Mains hard → HARD_STRATEGY

    Les upcards J/Q/K sont normalisées en "10" avant toute lookup.
    Les totaux ≤ 7 retournent "H", les totaux ≥ 18 retournent "S".
    """
    upcard = _normalize_upcard(dealer_upcard.rank)

    # 1. Paires
    if hand.is_pair:
        pair_val = hand.cards[0].value
        split_action = SPLIT_STRATEGY.get((pair_val, upcard), "N")
        if split_action != "N":
            return split_action
        # "N" → ne pas splitter, traiter comme hard total

    # 2. Mains soft
    if hand.is_soft:
        ace_plus = hand.value - 11   # composante non-As
        if 2 <= ace_plus <= 9:
            action = SOFT_STRATEGY.get((ace_plus, upcard))
            if action is not None:
                return action

    # 3. Hard strategy
    total = hand.value
    if total <= 7:
        return "H"
    if total >= 18:
        return "S"
    return HARD_STRATEGY.get((total, upcard), "S")


# ---------------------------------------------------------------------------
# get_action — unified entry point (basic or basic+deviations)
# ---------------------------------------------------------------------------

def get_action(
    hand: Hand,
    dealer_upcard: Card,
    strategy_mode: str,
    true_count: float = 0.0,
) -> str:
    """
    Return the recommended action for the given hand.

    strategy_mode:
      "basic"            → basic strategy only
      "basic_deviations" → Illustrious 18 deviations override basic if TC justifies it
    """
    if strategy_mode == "basic_deviations":
        from simulation.deviations import get_deviation
        dev = get_deviation(hand, dealer_upcard, true_count)
        if dev is not None:
            return dev
    return get_basic_strategy(hand, dealer_upcard)


# ---------------------------------------------------------------------------
# CLI de vérification
# ---------------------------------------------------------------------------

def _verify() -> None:
    errors: list[str] = []

    for total in range(8, 18):
        for upcard in UPCARDS:
            if (total, upcard) not in HARD_STRATEGY:
                errors.append(f"HARD manquant : ({total}, {upcard!r})")

    for nav in range(2, 10):
        for upcard in UPCARDS:
            if (nav, upcard) not in SOFT_STRATEGY:
                errors.append(f"SOFT manquant : ({nav}, {upcard!r})")

    for pv in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
        for upcard in UPCARDS:
            if (pv, upcard) not in SPLIT_STRATEGY:
                errors.append(f"SPLIT manquant : ({pv}, {upcard!r})")

    valid_hard  = {"H", "S", "D", "Ds", "SUR"}
    valid_soft  = {"H", "S", "D", "Ds"}
    valid_split = {"Y", "Y/N", "N", "S"}

    for (total, upcard), action in HARD_STRATEGY.items():
        if action not in valid_hard:
            errors.append(f"HARD action invalide ({total},{upcard}): {action!r}")
    for (nav, upcard), action in SOFT_STRATEGY.items():
        if action not in valid_soft:
            errors.append(f"SOFT action invalide ({nav},{upcard}): {action!r}")
    for (pv, upcard), action in SPLIT_STRATEGY.items():
        if action not in valid_split:
            errors.append(f"SPLIT action invalide ({pv},{upcard}): {action!r}")

    if errors:
        for e in errors:
            print(f"ERREUR : {e}")
        raise SystemExit(1)

    n = len(HARD_STRATEGY) + len(SOFT_STRATEGY) + len(SPLIT_STRATEGY)
    print(f"OK — {len(HARD_STRATEGY)} hard, {len(SOFT_STRATEGY)} soft, "
          f"{len(SPLIT_STRATEGY)} split ({n} entrees au total)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        _verify()