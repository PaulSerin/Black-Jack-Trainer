"""
test_engine.py — Tests unitaires pour simulation/engine.py
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simulation.engine import (
    Card, Hand, Shoe, GameState,
    RANKS, SUITS,
    can_split, can_double, can_surrender, split_hand,
    dealer_must_hit, compute_hand_result,
)


# ===========================================================================
# Card
# ===========================================================================

class TestCard:
    def test_valid_card(self):
        c = Card("A", "♠")
        assert c.rank == "A"
        assert c.suit == "♠"

    def test_invalid_rank(self):
        with pytest.raises(ValueError):
            Card("1", "♠")

    def test_invalid_suit(self):
        with pytest.raises(ValueError):
            Card("A", "X")

    def test_ace_value(self):
        assert Card("A", "♠").value == 11

    def test_face_card_value(self):
        assert Card("K", "♥").value == 10
        assert Card("Q", "♦").value == 10
        assert Card("J", "♣").value == 10

    def test_ten_value(self):
        assert Card("10", "♠").value == 10

    def test_numeric_values(self):
        for rank in ("2", "3", "4", "5", "6", "7", "8", "9"):
            assert Card(rank, "♠").value == int(rank)

    def test_is_ace(self):
        assert Card("A", "♠").is_ace is True
        assert Card("K", "♠").is_ace is False

    def test_frozen(self):
        c = Card("5", "♦")
        with pytest.raises(Exception):
            c.rank = "6"  # type: ignore[misc]

    def test_str(self):
        assert str(Card("A", "♠")) == "A♠"

    def test_repr(self):
        assert repr(Card("10", "♥")) == "Card('10', '♥')"


# ===========================================================================
# Hand — value & soft
# ===========================================================================

class TestHandValue:
    def test_simple_total(self):
        h = Hand()
        h.add_card(Card("7", "♠"))
        h.add_card(Card("8", "♥"))
        assert h.value == 15

    def test_ace_counted_11(self):
        h = Hand()
        h.add_card(Card("A", "♠"))
        h.add_card(Card("6", "♥"))
        assert h.value == 17

    def test_ace_reduced_to_1(self):
        h = Hand()
        h.add_card(Card("A", "♠"))
        h.add_card(Card("6", "♥"))
        h.add_card(Card("9", "♦"))
        # A+6+9 = 26 → A vaut 1 → 16
        assert h.value == 16

    def test_two_aces(self):
        h = Hand()
        h.add_card(Card("A", "♠"))
        h.add_card(Card("A", "♥"))
        # 11+11=22 → premier As réduit : 11+1=12
        assert h.value == 12

    def test_ace_then_bust_scenario(self):
        h = Hand()
        h.add_card(Card("A", "♠"))
        h.add_card(Card("A", "♥"))
        h.add_card(Card("9", "♦"))
        h.add_card(Card("K", "♣"))
        # 11+11+9+10=41 → 1+11+9+10=31 → 1+1+9+10=21
        assert h.value == 21

    def test_blackjack_value(self):
        h = Hand()
        h.add_card(Card("A", "♠"))
        h.add_card(Card("K", "♥"))
        assert h.value == 21

    def test_bust(self):
        h = Hand()
        h.add_card(Card("K", "♠"))
        h.add_card(Card("Q", "♥"))
        h.add_card(Card("5", "♦"))
        assert h.value == 25
        assert h.is_bust is True

    def test_soft_hand(self):
        h = Hand()
        h.add_card(Card("A", "♠"))
        h.add_card(Card("6", "♥"))
        assert h.is_soft is True

    def test_not_soft_when_ace_is_1(self):
        h = Hand()
        h.add_card(Card("A", "♠"))
        h.add_card(Card("6", "♥"))
        h.add_card(Card("9", "♦"))
        # As doit valoir 1 pour éviter le bust → main dure
        assert h.is_soft is False

    def test_hard_hand_no_ace(self):
        h = Hand()
        h.add_card(Card("7", "♠"))
        h.add_card(Card("8", "♥"))
        assert h.is_soft is False


# ===========================================================================
# Hand — blackjack & is_pair
# ===========================================================================

class TestHandBlackjack:
    def test_natural_blackjack(self):
        h = Hand()
        h.add_card(Card("A", "♠"))
        h.add_card(Card("K", "♥"))
        assert h.is_blackjack is True

    def test_blackjack_with_10(self):
        h = Hand()
        h.add_card(Card("10", "♣"))
        h.add_card(Card("A", "♦"))
        assert h.is_blackjack is True

    def test_21_three_cards_not_blackjack(self):
        h = Hand()
        h.add_card(Card("7", "♠"))
        h.add_card(Card("7", "♥"))
        h.add_card(Card("7", "♦"))
        assert h.is_blackjack is False

    def test_split_hand_not_blackjack(self):
        h = Hand(is_split_hand=True)
        h.add_card(Card("A", "♠"))
        h.add_card(Card("K", "♥"))
        assert h.is_blackjack is False

    def test_is_pair(self):
        h = Hand()
        h.add_card(Card("8", "♠"))
        h.add_card(Card("8", "♥"))
        assert h.is_pair is True

    def test_is_pair_faces_same_value(self):
        h = Hand()
        h.add_card(Card("K", "♠"))
        h.add_card(Card("Q", "♥"))
        # valeur 10 == 10
        assert h.is_pair is True

    def test_not_pair_different_value(self):
        h = Hand()
        h.add_card(Card("8", "♠"))
        h.add_card(Card("9", "♥"))
        assert h.is_pair is False

    def test_not_pair_three_cards(self):
        h = Hand()
        h.add_card(Card("8", "♠"))
        h.add_card(Card("8", "♥"))
        h.add_card(Card("8", "♦"))
        assert h.is_pair is False


# ===========================================================================
# Shoe
# ===========================================================================

class TestShoe:
    def test_total_cards_6_decks(self):
        shoe = Shoe(num_decks=6)
        assert shoe.total_cards == 312

    def test_total_cards_1_deck(self):
        shoe = Shoe(num_decks=1)
        assert shoe.total_cards == 52

    def test_deal_reduces_remaining(self):
        shoe = Shoe()
        initial = shoe.cards_remaining
        shoe.deal()
        assert shoe.cards_remaining == initial - 1

    def test_deal_returns_card(self):
        shoe = Shoe()
        c = shoe.deal()
        assert isinstance(c, Card)
        assert c.rank in RANKS
        assert c.suit in SUITS

    def test_cards_dealt_counter(self):
        shoe = Shoe()
        for _ in range(10):
            shoe.deal()
        assert shoe.cards_dealt == 10

    def test_decks_remaining(self):
        shoe = Shoe(num_decks=6)
        assert shoe.decks_remaining == pytest.approx(6.0)
        for _ in range(52):
            shoe.deal()
        assert shoe.decks_remaining == pytest.approx(5.0)

    def test_needs_shuffle_false_initially(self):
        shoe = Shoe(penetration=0.75)
        assert shoe.needs_shuffle is False

    def test_needs_shuffle_true_at_penetration(self):
        shoe = Shoe(num_decks=1, penetration=0.5)
        # 52 * 0.5 = 26 cartes
        for _ in range(26):
            shoe.deal()
        assert shoe.needs_shuffle is True

    def test_shuffle_resets(self):
        shoe = Shoe()
        for _ in range(50):
            shoe.deal()
        shoe.shuffle()
        assert shoe.cards_dealt == 0
        assert shoe.cards_remaining == shoe.total_cards

    def test_empty_shoe_raises(self):
        shoe = Shoe(num_decks=1)
        for _ in range(52):
            shoe.deal()
        with pytest.raises(RuntimeError):
            shoe.deal()

    def test_invalid_num_decks(self):
        with pytest.raises(ValueError):
            Shoe(num_decks=0)

    def test_invalid_penetration(self):
        with pytest.raises(ValueError):
            Shoe(penetration=0.0)
        with pytest.raises(ValueError):
            Shoe(penetration=1.1)

    def test_all_ranks_present(self):
        """Un sabot 1 deck doit contenir exactement 4 de chaque rang."""
        shoe = Shoe(num_decks=1)
        from collections import Counter
        counts: Counter = Counter()
        while not shoe.needs_shuffle:
            c = shoe.deal()
            counts[c.rank] += 1
        # Avec pénétration 75% on ne distribue que 39 cartes ; forçons tout
        shoe.shuffle()
        all_cards = [shoe.deal() for _ in range(52)]
        rank_counts = Counter(c.rank for c in all_cards)
        for rank in RANKS:
            assert rank_counts[rank] == 4, f"Rang {rank}: {rank_counts[rank]} ≠ 4"

    def test_composition_6_decks(self):
        """6 decks → 24 de chaque rang, 312 cartes au total."""
        shoe = Shoe(num_decks=6)
        from collections import Counter
        all_cards = [shoe.deal() for _ in range(312)]
        rank_counts = Counter(c.rank for c in all_cards)
        for rank in RANKS:
            assert rank_counts[rank] == 24


# ===========================================================================
# GameState
# ===========================================================================

class TestGameState:
    def test_deal_initial_creates_hands(self):
        state = GameState(shoe=Shoe())
        state.deal_initial()
        assert len(state.player_hands) == 1
        assert len(state.player_hands[0]) == 2
        assert len(state.dealer_hand) == 2

    def test_deal_initial_deals_4_cards(self):
        shoe = Shoe()
        initial_remaining = shoe.cards_remaining
        state = GameState(shoe=shoe)
        state.deal_initial()
        assert shoe.cards_remaining == initial_remaining - 4

    def test_active_hand(self):
        state = GameState(shoe=Shoe())
        state.deal_initial()
        assert state.active_hand is state.player_hands[0]

    def test_deal_initial_shuffles_if_needed(self):
        shoe = Shoe(num_decks=1, penetration=0.5)
        # Épuiser la pénétration
        for _ in range(26):
            shoe.deal()
        assert shoe.needs_shuffle is True
        state = GameState(shoe=shoe)
        state.deal_initial()
        # Après le mélange automatique, les 4 cartes sont distribuées
        assert shoe.cards_dealt == 4


# ===========================================================================
# can_split
# ===========================================================================

class TestCanSplit:
    def test_can_split_pair(self):
        h = Hand()
        h.add_card(Card("8", "♠"))
        h.add_card(Card("8", "♥"))
        assert can_split(h) is True

    def test_cannot_split_different_values(self):
        h = Hand()
        h.add_card(Card("7", "♠"))
        h.add_card(Card("8", "♥"))
        assert can_split(h) is False

    def test_cannot_split_three_cards(self):
        h = Hand()
        h.add_card(Card("8", "♠"))
        h.add_card(Card("8", "♥"))
        h.add_card(Card("2", "♦"))
        assert can_split(h) is False

    def test_can_split_aces(self):
        h = Hand()
        h.add_card(Card("A", "♠"))
        h.add_card(Card("A", "♥"))
        assert can_split(h) is True

    def test_can_split_faces_same_value(self):
        h = Hand()
        h.add_card(Card("K", "♠"))
        h.add_card(Card("Q", "♥"))
        assert can_split(h) is True


# ===========================================================================
# can_double
# ===========================================================================

class TestCanDouble:
    def test_can_double_two_cards(self):
        h = Hand()
        h.add_card(Card("5", "♠"))
        h.add_card(Card("6", "♥"))
        assert can_double(h) is True

    def test_cannot_double_three_cards(self):
        h = Hand()
        h.add_card(Card("5", "♠"))
        h.add_card(Card("3", "♥"))
        h.add_card(Card("2", "♦"))
        assert can_double(h) is False


# ===========================================================================
# can_surrender
# ===========================================================================

class TestCanSurrender:
    def test_can_surrender_initial_hand(self):
        h = Hand()
        h.add_card(Card("9", "♠"))
        h.add_card(Card("7", "♥"))
        upcard = Card("A", "♦")
        assert can_surrender(h, upcard) is True

    def test_cannot_surrender_after_hit(self):
        h = Hand()
        h.add_card(Card("9", "♠"))
        h.add_card(Card("7", "♥"))
        h.add_card(Card("2", "♦"))
        upcard = Card("A", "♣")
        assert can_surrender(h, upcard) is False

    def test_cannot_surrender_split_hand(self):
        h = Hand(is_split_hand=True)
        h.add_card(Card("9", "♠"))
        h.add_card(Card("7", "♥"))
        upcard = Card("A", "♦")
        assert can_surrender(h, upcard) is False


# ===========================================================================
# split_hand
# ===========================================================================

class TestSplitHand:
    def test_split_produces_two_hands(self):
        shoe = Shoe()
        h = Hand()
        h.add_card(Card("8", "♠"))
        h.add_card(Card("8", "♥"))
        h1, h2 = split_hand(h, shoe)
        assert len(h1) == 2
        assert len(h2) == 2

    def test_split_hands_are_marked(self):
        shoe = Shoe()
        h = Hand()
        h.add_card(Card("8", "♠"))
        h.add_card(Card("8", "♥"))
        h1, h2 = split_hand(h, shoe)
        assert h1.is_split_hand is True
        assert h2.is_split_hand is True

    def test_split_keeps_original_cards(self):
        shoe = Shoe()
        h = Hand()
        h.add_card(Card("8", "♠"))
        h.add_card(Card("8", "♥"))
        h1, h2 = split_hand(h, shoe)
        assert h1.cards[0].rank == "8"
        assert h2.cards[0].rank == "8"

    def test_split_invalid_hand_raises(self):
        shoe = Shoe()
        h = Hand()
        h.add_card(Card("7", "♠"))
        h.add_card(Card("8", "♥"))
        with pytest.raises(ValueError):
            split_hand(h, shoe)

    def test_split_deals_two_extra_cards(self):
        shoe = Shoe()
        initial = shoe.cards_remaining
        h = Hand()
        h.add_card(Card("8", "♠"))
        h.add_card(Card("8", "♥"))
        split_hand(h, shoe)
        assert shoe.cards_remaining == initial - 2


# ===========================================================================
# dealer_must_hit
# ===========================================================================

class TestDealerMustHit:
    def test_dealer_hits_below_17(self):
        h = Hand()
        h.add_card(Card("7", "♠"))
        h.add_card(Card("9", "♥"))
        # valeur = 16
        assert dealer_must_hit(h) is True

    def test_dealer_stands_on_17(self):
        h = Hand()
        h.add_card(Card("7", "♠"))
        h.add_card(Card("10", "♥"))
        assert dealer_must_hit(h) is False

    def test_dealer_stands_soft_17_default(self):
        h = Hand()
        h.add_card(Card("A", "♠"))
        h.add_card(Card("6", "♥"))
        # Soft 17, hits_soft_17=False (règle du projet)
        assert dealer_must_hit(h, hits_soft_17=False) is False

    def test_dealer_hits_soft_17_when_rule_active(self):
        h = Hand()
        h.add_card(Card("A", "♠"))
        h.add_card(Card("6", "♥"))
        assert dealer_must_hit(h, hits_soft_17=True) is True

    def test_dealer_stands_above_17(self):
        h = Hand()
        h.add_card(Card("10", "♠"))
        h.add_card(Card("9", "♥"))
        assert dealer_must_hit(h) is False


# ===========================================================================
# compute_hand_result
# ===========================================================================

class TestComputeHandResult:
    def _make_hand(self, *ranks: str) -> Hand:
        h = Hand()
        for rank in ranks:
            h.add_card(Card(rank, "♠"))
        return h

    def test_player_bust(self):
        p = self._make_hand("K", "Q", "5")
        d = self._make_hand("7", "10")
        assert compute_hand_result(p, d) == "bust"

    def test_player_blackjack_wins(self):
        p = Hand()
        p.add_card(Card("A", "♠"))
        p.add_card(Card("K", "♥"))
        d = self._make_hand("7", "10")
        assert compute_hand_result(p, d) == "blackjack"

    def test_both_blackjack_is_push(self):
        p = Hand()
        p.add_card(Card("A", "♠"))
        p.add_card(Card("K", "♥"))
        d = Hand()
        d.add_card(Card("A", "♦"))
        d.add_card(Card("Q", "♣"))
        # Les deux ont blackjack → push
        assert compute_hand_result(p, d) == "push"

    def test_dealer_blackjack_player_loses(self):
        p = self._make_hand("10", "9")
        d = Hand()
        d.add_card(Card("A", "♦"))
        d.add_card(Card("Q", "♣"))
        assert compute_hand_result(p, d) == "lose"

    def test_dealer_bust_player_wins(self):
        p = self._make_hand("10", "8")
        d = self._make_hand("10", "7", "9")
        assert compute_hand_result(p, d) == "win"

    def test_player_higher_wins(self):
        p = self._make_hand("10", "9")
        d = self._make_hand("10", "7")
        assert compute_hand_result(p, d) == "win"

    def test_dealer_higher_loses(self):
        p = self._make_hand("10", "7")
        d = self._make_hand("10", "9")
        assert compute_hand_result(p, d) == "lose"

    def test_push_same_value(self):
        p = self._make_hand("10", "8")
        d = self._make_hand("10", "8")
        assert compute_hand_result(p, d) == "push"
