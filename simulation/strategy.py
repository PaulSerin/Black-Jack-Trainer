"""
strategy.py — Basic strategy complète pour 6 decks, dealer stands on soft 17.

Source : https://wizardofodds.com/games/blackjack/strategy/6-decks/

Actions :
  H   = Hit
  S   = Stand
  D   = Double if allowed, otherwise Hit
  Ds  = Double if allowed, otherwise Stand
  SUR = Late Surrender (if not available, use H for 15, H for 16)
  Y   = Split the pair
  Y/N = Split only if Double After Split (DAS) is allowed
  N   = Don't split (treat as hard total)
"""

from __future__ import annotations

import argparse

from simulation.engine import Card, Hand

# ---------------------------------------------------------------------------
# Colonnes upcard dans l'ordre de la table (2 à A)
# ---------------------------------------------------------------------------
UPCARDS: tuple[str, ...] = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "A")

# ---------------------------------------------------------------------------
# HARD_STRATEGY
# Clé   : (player_total: int, dealer_upcard_rank: str)
# Valeur: action string
# Totaux couverts : 8–17
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
# Clé   : (non_ace_value: int, dealer_upcard_rank: str)
# non_ace_value = valeur de la carte non-As (2–9)
# A,2 = clé 2 (soft 13) … A,9 = clé 9 (soft 20)
# ---------------------------------------------------------------------------
_SOFT_ROWS: dict[int, list[str]] = {
    #          2     3     4     5     6     7     8     9    10     A
    2:  ["H", "H",  "H",  "D",  "D",  "H",  "H",  "H",  "H",  "H"],   # A,2 soft 13
    3:  ["H", "H",  "H",  "D",  "D",  "H",  "H",  "H",  "H",  "H"],   # A,3 soft 14
    4:  ["H", "H",  "D",  "D",  "D",  "H",  "H",  "H",  "H",  "H"],   # A,4 soft 15
    5:  ["H", "H",  "D",  "D",  "D",  "H",  "H",  "H",  "H",  "H"],   # A,5 soft 16
    6:  ["H", "D",  "D",  "D",  "D",  "H",  "H",  "H",  "H",  "H"],   # A,6 soft 17
    7:  ["Ds","Ds", "Ds", "Ds", "Ds", "S",  "S",  "H",  "H",  "H"],   # A,7 soft 18
    8:  ["S", "S",  "S",  "S",  "Ds", "S",  "S",  "S",  "S",  "S"],   # A,8 soft 19
    9:  ["S", "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S"],   # A,9 soft 20
}

SOFT_STRATEGY: dict[tuple[int, str], str] = {
    (nav, upcard): action
    for nav, row in _SOFT_ROWS.items()
    for upcard, action in zip(UPCARDS, row)
}

# ---------------------------------------------------------------------------
# SPLIT_STRATEGY
# Clé   : (pair_card_value: int, dealer_upcard_rank: str)
# pair_card_value : valeur de chaque carte de la paire
#   As = 11, figures/10 = 10, autres = valeur nominale
# ---------------------------------------------------------------------------
_SPLIT_ROWS: dict[int, list[str]] = {
    #           2      3      4      5      6      7      8      9     10      A
    11: ["Y",  "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y"],   # A,A
    10: ["N",  "N",   "N",   "N",   "N",   "N",   "N",   "N",   "N",   "N"],   # 10,10
    9:  ["Y",  "Y",   "Y",   "Y",   "Y",   "S",   "Y",   "Y",   "S",   "S"],   # 9,9
    8:  ["Y",  "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y",   "Y"],   # 8,8
    7:  ["Y",  "Y",   "Y",   "Y",   "Y",   "Y",   "N",   "N",   "N",   "N"],   # 7,7
    6:  ["Y/N","Y",   "Y",   "Y",   "Y",   "N",   "N",   "N",   "N",   "N"],   # 6,6
    5:  ["N",  "N",   "N",   "N",   "N",   "N",   "N",   "N",   "N",   "N"],   # 5,5
    4:  ["N",  "N",   "N",   "Y/N", "Y/N", "N",   "N",   "N",   "N",   "N"],   # 4,4
    3:  ["Y/N","Y/N", "Y",   "Y",   "Y",   "Y",   "N",   "N",   "N",   "N"],   # 3,3
    2:  ["Y/N","Y/N", "Y",   "Y",   "Y",   "Y",   "N",   "N",   "N",   "N"],   # 2,2
}

SPLIT_STRATEGY: dict[tuple[int, str], str] = {
    (pv, upcard): action
    for pv, row in _SPLIT_ROWS.items()
    for upcard, action in zip(UPCARDS, row)
}

# ---------------------------------------------------------------------------
# SURRENDER
# Clé   : (player_total: int, dealer_upcard_rank: str)
# Valeur: True si late surrender recommandé
# (déjà intégré dans HARD_STRATEGY via "SUR" ; ce dict sert d'index rapide)
# ---------------------------------------------------------------------------
SURRENDER: dict[tuple[int, str], bool] = {
    (16, "9"): True,
    (16, "10"): True,
    (16, "A"): True,
    (15, "10"): True,
    (15, "A"): True,
}


# ---------------------------------------------------------------------------
# get_basic_strategy
# ---------------------------------------------------------------------------

def get_basic_strategy(hand: Hand, dealer_upcard: Card) -> str:
    """
    Retourne l'action de basic strategy pour une main donnée.

    Priorité :
      1. Paires    → SPLIT_STRATEGY (si action != "N", retourner directement)
      2. Mains soft → SOFT_STRATEGY
      3. Mains hard → HARD_STRATEGY

    Pour les paires dont l'action est "N" (ex. 5,5), on retombe sur
    la hard strategy correspondant au total de la main.

    Retourne "H" pour les totaux < 8 et "S" pour les totaux >= 18
    non couverts par les tables.
    """
    upcard = dealer_upcard.rank

    # 1. Paires
    if hand.is_pair:
        pair_val = hand.cards[0].value
        split_action = SPLIT_STRATEGY.get((pair_val, upcard), "N")
        if split_action != "N":
            return split_action
        # "N" → ne pas splitter, traiter comme hard total

    # 2. Mains soft
    if hand.is_soft:
        ace_plus = hand.value - 11   # composante non-As (11 comptée pour l'As)
        if 2 <= ace_plus <= 9:
            action = SOFT_STRATEGY.get((ace_plus, upcard))
            if action is not None:
                return action
        # Soft total hors table (ex. soft 21) → traiter comme hard

    # 3. Hard strategy (y compris paires "N" et soft hors table)
    total = hand.value
    if total <= 7:
        return "H"
    if total >= 18:
        return "S"
    return HARD_STRATEGY.get((total, upcard), "S")


# ---------------------------------------------------------------------------
# CLI de vérification
# ---------------------------------------------------------------------------

def _verify() -> None:
    """Vérifie quelques invariants de cohérence des tables."""
    errors: list[str] = []

    # Toutes les clés hard attendues sont présentes
    for total in range(8, 18):
        for upcard in UPCARDS:
            if (total, upcard) not in HARD_STRATEGY:
                errors.append(f"HARD manquant : ({total}, {upcard!r})")

    # Toutes les clés soft attendues sont présentes
    for nav in range(2, 10):
        for upcard in UPCARDS:
            if (nav, upcard) not in SOFT_STRATEGY:
                errors.append(f"SOFT manquant : ({nav}, {upcard!r})")

    # Toutes les clés split attendues sont présentes
    for pv in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
        for upcard in UPCARDS:
            if (pv, upcard) not in SPLIT_STRATEGY:
                errors.append(f"SPLIT manquant : ({pv}, {upcard!r})")

    # Actions valides
    valid_hard = {"H", "S", "D", "Ds", "SUR"}
    valid_soft = {"H", "S", "D", "Ds"}
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

    total_entries = len(HARD_STRATEGY) + len(SOFT_STRATEGY) + len(SPLIT_STRATEGY)
    print(f"OK — {len(HARD_STRATEGY)} hard, {len(SOFT_STRATEGY)} soft, "
          f"{len(SPLIT_STRATEGY)} split ({total_entries} entrées au total)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        _verify()
