"""
counting.py - Comptage de cartes Hi-Lo pour Blackjack Trainer Pro.

Règles Hi-Lo :
  +1 : 2, 3, 4, 5, 6
   0 : 7, 8, 9
  -1 : 10, J, Q, K, A

True count = running count / decks restants, arrondi au 0.5 le plus proche.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from simulation.engine import Card, Shoe


# ---------------------------------------------------------------------------
# Fonction pure de valeur Hi-Lo
# ---------------------------------------------------------------------------

def card_value(card: Card) -> int:
    """
    Retourne la valeur Hi-Lo d'une carte.
      +1 : 2–6
       0 : 7–9
      -1 : 10, J, Q, K, A
    """
    if card.rank in ("2", "3", "4", "5", "6"):
        return 1
    if card.rank in ("7", "8", "9"):
        return 0
    # 10, J, Q, K, A
    return -1


# ---------------------------------------------------------------------------
# Arrondi au 0.5 le plus proche
# ---------------------------------------------------------------------------

def _round_half(value: float) -> float:
    """Arrondit à la demie-unité la plus proche (ex: 2.3 → 2.5, 2.7 → 2.5)."""
    return math.floor(value * 2 + 0.5) / 2


# ---------------------------------------------------------------------------
# HiLoCounter
# ---------------------------------------------------------------------------

@dataclass
class HiLoCounter:
    running_count: int = field(default=0)
    cards_seen: int = field(default=0)

    def update(self, card: Card) -> None:
        """Met à jour le running count avec la carte distribuée."""
        self.running_count += card_value(card)
        self.cards_seen += 1

    def true_count(self, shoe: Shoe) -> float:
        """
        True count = running count / decks restants.
        Arrondi au 0.5 le plus proche. Pas de floor.

        Lève ZeroDivisionError si le sabot est vide.
        """
        decks_left = shoe.decks_remaining
        if decks_left <= 0:
            raise ZeroDivisionError("Aucun deck restant dans le sabot.")
        return _round_half(self.running_count / decks_left)

    def reset(self) -> None:
        """Remet le compteur à zéro (nouveau sabot)."""
        self.running_count = 0
        self.cards_seen = 0


# ---------------------------------------------------------------------------
# Point d'entrée CLI (debug)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    from simulation.engine import Shoe

    parser = argparse.ArgumentParser(description="Debug comptage Hi-Lo")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    shoe = Shoe()
    counter = HiLoCounter()

    print(f"Sabot : {shoe.total_cards} cartes")
    for i in range(20):
        card = shoe.deal()
        counter.update(card)
        tc = counter.true_count(shoe)
        print(
            f"  {i+1:>2}. {card!s:<5} | "
            f"val={card_value(card):+d} | "
            f"RC={counter.running_count:+d} | "
            f"TC={tc:+.1f} | "
            f"vus={counter.cards_seen}"
        )
