"""
test_counting.py — Tests unitaires pour simulation/counting.py
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simulation.engine import Card, Shoe
from simulation.counting import card_value, HiLoCounter, _round_half


# ===========================================================================
# card_value — valeurs Hi-Lo
# ===========================================================================

class TestCardValue:
    @pytest.mark.parametrize("rank", ["2", "3", "4", "5", "6"])
    def test_low_cards_plus_one(self, rank: str):
        assert card_value(Card(rank, "♠")) == 1

    @pytest.mark.parametrize("rank", ["7", "8", "9"])
    def test_neutral_cards_zero(self, rank: str):
        assert card_value(Card(rank, "♠")) == 0

    @pytest.mark.parametrize("rank", ["10", "J", "Q", "K", "A"])
    def test_high_cards_minus_one(self, rank: str):
        assert card_value(Card(rank, "♠")) == -1

    def test_deck_is_balanced(self):
        """Un deck complet Hi-Lo doit sommer à 0."""
        from simulation.engine import RANKS, SUITS
        total = sum(
            card_value(Card(rank, suit))
            for rank in RANKS
            for suit in SUITS
        )
        assert total == 0

    def test_six_deck_shoe_balanced(self):
        """6 decks entiers → somme Hi-Lo = 0."""
        from simulation.engine import RANKS, SUITS
        total = sum(
            card_value(Card(rank, suit))
            for _ in range(6)
            for rank in RANKS
            for suit in SUITS
        )
        assert total == 0


# ===========================================================================
# _round_half — arrondi au 0.5 le plus proche
# ===========================================================================

class TestRoundHalf:
    @pytest.mark.parametrize("value, expected", [
        (0.0,   0.0),
        (0.24,  0.0),
        (0.25,  0.5),
        (0.5,   0.5),
        (0.74,  0.5),
        (0.75,  1.0),
        (1.0,   1.0),
        (1.3,   1.5),
        (2.74,  2.5),
        (2.75,  3.0),
        (-0.25, 0.0),   # vers zéro (floor sémantique)
        (-0.5,  -0.5),
        (-0.75, -0.5),
        (-1.0,  -1.0),
        (-1.3,  -1.5),
        (3.0,   3.0),
    ])
    def test_rounding(self, value: float, expected: float):
        assert _round_half(value) == pytest.approx(expected)

    def test_no_floor_applied(self):
        """Vérifier qu'on n'applique pas de floor avant l'arrondi."""
        # RC=2, decks=1.8 → 2/1.8 ≈ 1.111 → arrondi 0.5 → 1.0 (pas 1)
        # Mais surtout : RC=3, decks=2 → 1.5 → doit rester 1.5 et non 1
        assert _round_half(1.5) == 1.5
        assert _round_half(2.5) == 2.5
        assert _round_half(-1.5) == -1.5


# ===========================================================================
# HiLoCounter — running count
# ===========================================================================

class TestHiLoCounterRunningCount:
    def test_initial_state(self):
        c = HiLoCounter()
        assert c.running_count == 0
        assert c.cards_seen == 0

    def test_update_low_card_increments(self):
        c = HiLoCounter()
        c.update(Card("5", "♠"))
        assert c.running_count == 1
        assert c.cards_seen == 1

    def test_update_neutral_card_no_change(self):
        c = HiLoCounter()
        c.update(Card("8", "♥"))
        assert c.running_count == 0
        assert c.cards_seen == 1

    def test_update_high_card_decrements(self):
        c = HiLoCounter()
        c.update(Card("K", "♦"))
        assert c.running_count == -1
        assert c.cards_seen == 1

    def test_update_ace_decrements(self):
        c = HiLoCounter()
        c.update(Card("A", "♣"))
        assert c.running_count == -1

    def test_update_multiple_cards(self):
        c = HiLoCounter()
        cards = [
            Card("2", "♠"),   # +1 → RC=1
            Card("K", "♥"),   # -1 → RC=0
            Card("5", "♦"),   # +1 → RC=1
            Card("A", "♣"),   # -1 → RC=0
            Card("7", "♠"),   #  0 → RC=0
            Card("3", "♥"),   # +1 → RC=1
        ]
        for card in cards:
            c.update(card)
        assert c.running_count == 1
        assert c.cards_seen == 6

    def test_running_count_can_be_negative(self):
        c = HiLoCounter()
        for _ in range(5):
            c.update(Card("A", "♠"))
        assert c.running_count == -5

    def test_cards_seen_increments_for_all_ranks(self):
        c = HiLoCounter()
        from simulation.engine import RANKS
        for rank in RANKS:
            c.update(Card(rank, "♠"))
        assert c.cards_seen == len(RANKS)


# ===========================================================================
# HiLoCounter — true count
# ===========================================================================

class TestHiLoCounterTrueCount:
    def test_true_count_zero_when_rc_zero(self):
        shoe = Shoe(num_decks=6)
        c = HiLoCounter()
        assert c.true_count(shoe) == pytest.approx(0.0)

    def test_true_count_basic(self):
        """RC=6, 6 decks restants → TC = 1.0."""
        shoe = Shoe(num_decks=6)
        c = HiLoCounter(running_count=6)
        assert c.true_count(shoe) == pytest.approx(1.0)

    def test_true_count_rounds_to_half(self):
        """RC=3, ~2 decks → 3/2=1.5 → arrondi 0.5 = 1.5."""
        shoe = Shoe(num_decks=2)
        c = HiLoCounter(running_count=3)
        assert c.true_count(shoe) == pytest.approx(1.5)

    def test_true_count_negative(self):
        """RC=-6, 6 decks → TC=-1.0."""
        shoe = Shoe(num_decks=6)
        c = HiLoCounter(running_count=-6)
        assert c.true_count(shoe) == pytest.approx(-1.0)

    def test_true_count_decreases_as_cards_dealt(self):
        """
        RC fixé à 6 ; à mesure qu'on distribue des cartes neutres
        (sans changer le RC), les decks restants diminuent → TC augmente.
        """
        shoe = Shoe(num_decks=6)
        c = HiLoCounter(running_count=6)
        tc_start = c.true_count(shoe)

        # Distribuer 156 cartes neutres (3 decks)
        for _ in range(156):
            shoe.deal()

        tc_after = c.true_count(shoe)
        assert tc_after > tc_start

    def test_true_count_uses_decks_remaining_not_dealt(self):
        """
        Vérifier qu'on divise par les decks RESTANTS (pas les decks distribués).
        RC=3, 1 deck restant (52 cartes) → TC=3.0.
        """
        shoe = Shoe(num_decks=2)
        # Distribuer exactement 52 cartes → 1 deck restant
        for _ in range(52):
            shoe.deal()
        c = HiLoCounter(running_count=3)
        assert c.true_count(shoe) == pytest.approx(3.0)

    def test_true_count_empty_shoe_raises(self):
        shoe = Shoe(num_decks=1)
        for _ in range(52):
            shoe.deal()
        c = HiLoCounter(running_count=5)
        with pytest.raises(ZeroDivisionError):
            c.true_count(shoe)

    def test_true_count_no_floor(self):
        """
        TC = 1.3 doit donner 1.5 (arrondi 0.5), pas 1 (floor).
        RC=4, ~3 decks → 4/3 ≈ 1.333 → 1.5.
        """
        shoe = Shoe(num_decks=3)
        c = HiLoCounter(running_count=4)
        tc = c.true_count(shoe)
        assert tc == pytest.approx(1.5)

    def test_true_count_rounding_examples(self):
        """Série de cas vérifiant l'arrondi au 0.5."""
        shoe = Shoe(num_decks=6)

        cases = [
            # (RC, cartes_à_distribuer, TC_attendu)
            # 6 decks = 312 cartes ; distribuer N cartes neutres pour ajuster
            (5,  0,   1.0),   # 5/6 ≈ 0.833 → 1.0
            (8,  0,   1.5),   # 8/6 ≈ 1.333 → 1.5
            (11, 0,   2.0),   # 11/6 ≈ 1.833 → 2.0
        ]

        for rc, dealt, expected_tc in cases:
            s = Shoe(num_decks=6)
            counter = HiLoCounter(running_count=rc)
            tc = counter.true_count(s)
            assert tc == pytest.approx(expected_tc), (
                f"RC={rc}, TC attendu={expected_tc}, obtenu={tc}"
            )


# ===========================================================================
# HiLoCounter — reset
# ===========================================================================

class TestHiLoCounterReset:
    def test_reset_clears_running_count(self):
        c = HiLoCounter()
        for _ in range(10):
            c.update(Card("5", "♠"))
        c.reset()
        assert c.running_count == 0

    def test_reset_clears_cards_seen(self):
        c = HiLoCounter()
        for _ in range(10):
            c.update(Card("5", "♠"))
        c.reset()
        assert c.cards_seen == 0

    def test_reset_then_update(self):
        c = HiLoCounter()
        c.update(Card("A", "♠"))
        c.update(Card("K", "♥"))
        c.reset()
        c.update(Card("3", "♦"))
        assert c.running_count == 1
        assert c.cards_seen == 1

    def test_reset_called_on_new_shoe(self):
        """Simulation d'un enchaînement : sabot épuisé → reset → nouveau sabot."""
        shoe = Shoe(num_decks=1)
        c = HiLoCounter()

        # Jouer tout le sabot
        while shoe.cards_remaining > 0:
            card = shoe.deal()
            c.update(card)

        # Vérifier que le RC est 0 (deck équilibré)
        assert c.running_count == 0

        # Nouveau sabot
        shoe.shuffle()
        c.reset()
        assert c.running_count == 0
        assert c.cards_seen == 0

        # Reprendre le jeu
        c.update(shoe.deal())
        assert c.cards_seen == 1


# ===========================================================================
# Intégration : comptage sur un sabot complet
# ===========================================================================

class TestCountingIntegration:
    def test_full_shoe_sums_to_zero(self):
        """Compter toutes les cartes d'un sabot doit donner RC=0."""
        shoe = Shoe(num_decks=6)
        c = HiLoCounter()
        while shoe.cards_remaining > 0:
            c.update(shoe.deal())
        assert c.running_count == 0

    def test_cards_seen_matches_dealt(self):
        shoe = Shoe(num_decks=6)
        c = HiLoCounter()
        n = 100
        for _ in range(n):
            c.update(shoe.deal())
        assert c.cards_seen == n

    def test_true_count_evolves_correctly(self):
        """
        En distribuant seulement des cartes basses (+1),
        le RC et donc le TC augmentent au fil du temps.
        """
        from unittest.mock import patch

        shoe = Shoe(num_decks=6)
        c = HiLoCounter()

        tc_prev = c.true_count(shoe)
        # Simuler 30 cartes basses consécutives via update direct
        for _ in range(30):
            c.running_count += 1
            c.cards_seen += 1
            shoe.deal()  # réduire le sabot aussi
            tc_curr = c.true_count(shoe)

        # Après 30 incréments, TC doit être nettement positif
        assert c.true_count(shoe) > tc_prev
