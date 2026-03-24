"""
deviations.py — Illustrious 18 deviations Hi-Lo pour Blackjack Trainer Pro.

Source : "Blackjack Attack" de Don Schlesinger.
Applicable : 6 decks, dealer stands on soft 17, Hi-Lo counting.

Les deviations priment TOUJOURS sur la basic strategy quand le TC le justifie.

Opérateurs :
  ">=" : dévier si true_count >= tc_threshold
  "<=" : dévier si true_count <= tc_threshold

Remarque sur les paires vs déviations hard :
  Les déviations "hard" ne s'appliquent qu'aux mains non-paires.
  Pour une paire (ex. 8,8), la décision de split prime.
  La déviation 10,10 vs 5/6 est gérée via hand_type="pair".
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from simulation.engine import Card, Hand
from simulation.strategy import get_basic_strategy


# ---------------------------------------------------------------------------
# Dataclass Deviation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Deviation:
    situation: str          # description lisible
    hand_type: str          # "hard" | "pair" | "insurance"
    player_value: int       # total hard ou valeur de chaque carte de la paire ;
                            # -1 pour insurance
    dealer_rank: str        # rang de l'upcard du dealer ("2"-"A") ;
                            # "A" pour insurance
    tc_threshold: float     # seuil de true count déclencheur
    operator: str           # ">=" ou "<="
    action: str             # action à jouer : "S","D","H","Y","INS"


# ---------------------------------------------------------------------------
# Illustrious 18
# ---------------------------------------------------------------------------

ILLUSTRIOUS_18: list[Deviation] = [
    # ── Positive deviations (TC >= seuil → changer l'action) ──────────────

    # Insurance : prendre si TC >= +3
    Deviation("Insurance",         "insurance",  -1, "A",  3.0, ">=", "INS"),

    # 16 vs 10 : standing au lieu de SUR/H
    Deviation("16 vs 10",          "hard",       16, "10", 0.0, ">=", "S"),

    # 15 vs 10 : standing au lieu de SUR
    Deviation("15 vs 10",          "hard",       15, "10", 4.0, ">=", "S"),

    # 10,10 vs 5 : splitter au lieu de S
    Deviation("10,10 vs 5",        "pair",       10, "5",  5.0, ">=", "Y"),

    # 10,10 vs 6 : splitter au lieu de S
    Deviation("10,10 vs 6",        "pair",       10, "6",  4.0, ">=", "Y"),

    # Hard 10 vs 10 : doubler au lieu de H
    Deviation("Hard 10 vs 10",     "hard",       10, "10", 4.0, ">=", "D"),

    # 12 vs 3 : stand au lieu de H
    Deviation("12 vs 3",           "hard",       12, "3",  2.0, ">=", "S"),

    # 12 vs 2 : stand au lieu de H
    Deviation("12 vs 2",           "hard",       12, "2",  3.0, ">=", "S"),

    # 11 vs A : doubler au lieu de H
    Deviation("11 vs A",           "hard",       11, "A",  1.0, ">=", "D"),

    # 9 vs 2 : doubler au lieu de H
    Deviation("9 vs 2",            "hard",        9, "2",  1.0, ">=", "D"),

    # Hard 10 vs A : doubler au lieu de H
    Deviation("Hard 10 vs A",      "hard",       10, "A",  4.0, ">=", "D"),

    # Hard 9 vs 7 : doubler au lieu de H
    Deviation("Hard 9 vs 7",       "hard",        9, "7",  3.0, ">=", "D"),

    # 16 vs 9 : stand au lieu de H/SUR
    Deviation("16 vs 9",           "hard",       16, "9",  5.0, ">=", "S"),

    # ── Negative deviations (TC <= seuil → changer l'action) ──────────────

    # 13 vs 2 : hit au lieu de S
    Deviation("13 vs 2",           "hard",       13, "2", -1.0, "<=", "H"),

    # 12 vs 4 : hit au lieu de S
    Deviation("12 vs 4",           "hard",       12, "4",  0.0, "<=", "H"),

    # 12 vs 5 : hit au lieu de S
    Deviation("12 vs 5",           "hard",       12, "5", -2.0, "<=", "H"),

    # 12 vs 6 : hit au lieu de S
    Deviation("12 vs 6",           "hard",       12, "6", -1.0, "<=", "H"),

    # 13 vs 3 : hit au lieu de S
    Deviation("13 vs 3",           "hard",       13, "3", -2.0, "<=", "H"),
]

assert len(ILLUSTRIOUS_18) == 18, f"I18 contient {len(ILLUSTRIOUS_18)} entrées, attendu 18"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tc_matches(true_count: float, threshold: float, operator: str) -> bool:
    if operator == ">=":
        return true_count >= threshold
    if operator == "<=":
        return true_count <= threshold
    return False


# ---------------------------------------------------------------------------
# get_deviation
# ---------------------------------------------------------------------------

def should_take_insurance(dealer_upcard: Card, true_count: float) -> bool:
    """
    Retourne True si Hi-Lo recommande de prendre l'assurance.
    Condition : dealer montre un As ET TC >= +3.
    C'est une décision de mise annexe, distincte du jeu de la main.
    """
    ins = next(d for d in ILLUSTRIOUS_18 if d.hand_type == "insurance")
    return (
        dealer_upcard.rank == ins.dealer_rank
        and _tc_matches(true_count, ins.tc_threshold, ins.operator)
    )


def get_deviation(hand: Hand, dealer_upcard: Card, true_count: float) -> str | None:
    """
    Retourne l'action de déviation Illustrious 18 applicable, ou None
    si la basic strategy s'applique.

    Ordre de priorité interne : l'ordre de ILLUSTRIOUS_18
    (les déviations les plus importantes sont en tête de liste).

    Notes :
    - L'assurance ("insurance") est exclue de cette fonction : c'est une
      décision de mise séparée gérée par should_take_insurance().
    - Les déviations "hard" ne s'appliquent pas aux mains soft ni aux paires
      (pour les paires, seules les déviations "pair" sont éligibles).
    """
    upcard_rank = dealer_upcard.rank

    for dev in ILLUSTRIOUS_18:

        # ── Insurance : gérée séparément ───────────────────────────────────
        if dev.hand_type == "insurance":
            continue

        # Filtre upcard commun à pair et hard
        if dev.dealer_rank != upcard_rank:
            continue

        # ── Pair (ex. 10,10 vs 5/6) ────────────────────────────────────────
        if dev.hand_type == "pair":
            if (
                hand.is_pair
                and hand.cards[0].value == dev.player_value
                and _tc_matches(true_count, dev.tc_threshold, dev.operator)
            ):
                return dev.action
            continue

        # ── Hard ────────────────────────────────────────────────────────────
        if dev.hand_type == "hard":
            # Les déviations hard ne s'appliquent pas aux mains soft ni aux paires
            if hand.is_soft or hand.is_pair:
                continue
            if hand.value != dev.player_value:
                continue
            if _tc_matches(true_count, dev.tc_threshold, dev.operator):
                return dev.action

    return None


# ---------------------------------------------------------------------------
# get_action — point d'entrée combiné
# ---------------------------------------------------------------------------

def get_action(hand: Hand, dealer_upcard: Card, true_count: float) -> str:
    """
    Retourne l'action recommandée en tenant compte des déviations I18.

    1. Vérifie get_deviation() — si une déviation s'applique, elle prime.
    2. Sinon, retombe sur get_basic_strategy().
    """
    deviation = get_deviation(hand, dealer_upcard, true_count)
    if deviation is not None:
        return deviation
    return get_basic_strategy(hand, dealer_upcard)


# ---------------------------------------------------------------------------
# CLI de vérification
# ---------------------------------------------------------------------------

def _verify() -> None:
    """Vérifie l'intégrité de la liste ILLUSTRIOUS_18."""
    valid_hand_types = {"hard", "pair", "insurance"}
    valid_operators = {">=", "<="}
    valid_actions = {"S", "D", "H", "Y", "INS"}
    valid_ranks = {"2", "3", "4", "5", "6", "7", "8", "9", "10", "A"}
    errors: list[str] = []

    for i, dev in enumerate(ILLUSTRIOUS_18):
        if dev.hand_type not in valid_hand_types:
            errors.append(f"[{i}] hand_type invalide : {dev.hand_type!r}")
        if dev.operator not in valid_operators:
            errors.append(f"[{i}] operator invalide : {dev.operator!r}")
        if dev.action not in valid_actions:
            errors.append(f"[{i}] action invalide : {dev.action!r}")
        if dev.hand_type != "insurance" and dev.dealer_rank not in valid_ranks:
            errors.append(f"[{i}] dealer_rank invalide : {dev.dealer_rank!r}")

    if len(ILLUSTRIOUS_18) != 18:
        errors.append(f"Nombre de déviations : {len(ILLUSTRIOUS_18)} ≠ 18")

    if errors:
        for e in errors:
            print(f"ERREUR : {e}")
        raise SystemExit(1)

    print(f"OK — {len(ILLUSTRIOUS_18)} déviations Illustrious 18 validées")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        _verify()
