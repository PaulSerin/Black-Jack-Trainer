"""
test_strategy.py — Tests unitaires pour simulation/strategy.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from simulation.engine import Card, Hand
from simulation.strategy import (
    HARD_STRATEGY, SOFT_STRATEGY, SPLIT_STRATEGY, SURRENDER,
    UPCARDS, get_basic_strategy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hard_hand(*ranks: str) -> Hand:
    h = Hand()
    for r in ranks:
        h.add_card(Card(r, "♠"))
    return h


def soft_hand(non_ace_rank: str) -> Hand:
    """Crée une main A + non_ace_rank."""
    h = Hand()
    h.add_card(Card("A", "♠"))
    h.add_card(Card(non_ace_rank, "♥"))
    return h


def pair_hand(rank: str) -> Hand:
    h = Hand()
    h.add_card(Card(rank, "♠"))
    h.add_card(Card(rank, "♥"))
    return h


def up(rank: str) -> Card:
    return Card(rank, "♦")


# ===========================================================================
# Intégrité des tables
# ===========================================================================

class TestTableIntegrity:
    def test_hard_strategy_size(self):
        # 10 totaux (8–17) × 10 upcards
        assert len(HARD_STRATEGY) == 100

    def test_soft_strategy_size(self):
        # 8 valeurs (2–9) × 10 upcards
        assert len(SOFT_STRATEGY) == 80

    def test_split_strategy_size(self):
        # 10 paires × 10 upcards
        assert len(SPLIT_STRATEGY) == 100

    def test_all_hard_keys_present(self):
        for total in range(8, 18):
            for u in UPCARDS:
                assert (total, u) in HARD_STRATEGY, f"Manquant hard ({total},{u})"

    def test_all_soft_keys_present(self):
        for nav in range(2, 10):
            for u in UPCARDS:
                assert (nav, u) in SOFT_STRATEGY, f"Manquant soft ({nav},{u})"

    def test_all_split_keys_present(self):
        for pv in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
            for u in UPCARDS:
                assert (pv, u) in SPLIT_STRATEGY, f"Manquant split ({pv},{u})"

    def test_hard_actions_valid(self):
        valid = {"H", "S", "D", "Ds", "SUR"}
        for k, v in HARD_STRATEGY.items():
            assert v in valid, f"Hard {k}: {v!r} invalide"

    def test_soft_actions_valid(self):
        valid = {"H", "S", "D", "Ds"}
        for k, v in SOFT_STRATEGY.items():
            assert v in valid, f"Soft {k}: {v!r} invalide"

    def test_split_actions_valid(self):
        valid = {"Y", "Y/N", "N", "S"}
        for k, v in SPLIT_STRATEGY.items():
            assert v in valid, f"Split {k}: {v!r} invalide"


# ===========================================================================
# HARD STRATEGY — cas clés
# ===========================================================================

class TestHardStrategy:
    @pytest.mark.parametrize("ranks, dealer_rank, expected", [
        # Hard 16 vs 9 → SUR
        (("10", "6"), "9",  "SUR"),
        # Hard 16 vs 10 → SUR
        (("10", "6"), "10", "SUR"),
        # Hard 12 vs 4 → S
        (("7",  "5"), "4",  "S"),
        # Hard 11 vs 6 → D
        (("6",  "5"), "6",  "D"),
        # Hard 9 vs 3 → D
        (("5",  "4"), "3",  "D"),
        # Hard 8 vs 5 → H
        (("5",  "3"), "5",  "H"),
        # Hard 13 vs 7 → H
        (("7",  "6"), "7",  "H"),
        # Hard 17 vs A → S
        (("10", "7"), "A",  "S"),
        # Hard 10 vs 10 → H
        (("6",  "4"), "10", "H"),
        # Hard 15 vs 10 → SUR
        (("10", "5"), "10", "SUR"),
    ])
    def test_hard(self, ranks, dealer_rank, expected):
        h = hard_hand(*ranks)
        assert get_basic_strategy(h, up(dealer_rank)) == expected

    def test_hard_16_vs_7_is_hit(self):
        h = hard_hand("10", "6")
        assert get_basic_strategy(h, up("7")) == "H"

    def test_hard_16_vs_6_is_stand(self):
        h = hard_hand("10", "6")
        assert get_basic_strategy(h, up("6")) == "S"

    def test_hard_12_vs_2_is_hit(self):
        h = hard_hand("7", "5")
        assert get_basic_strategy(h, up("2")) == "H"

    def test_hard_12_vs_6_is_stand(self):
        h = hard_hand("7", "5")
        assert get_basic_strategy(h, up("6")) == "S"

    def test_hard_total_below_8_is_hit(self):
        h = hard_hand("3", "4")   # hard 7
        assert get_basic_strategy(h, up("6")) == "H"

    def test_hard_total_above_17_is_stand(self):
        h = hard_hand("10", "9")  # hard 19
        assert get_basic_strategy(h, up("A")) == "S"

    def test_hard_11_vs_ace_is_hit(self):
        # Pour 6 decks S17 : hard 11 vs A → H (pas D)
        h = hard_hand("7", "4")
        assert get_basic_strategy(h, up("A")) == "H"

    def test_hard_10_vs_ace_is_hit(self):
        h = hard_hand("6", "4")
        assert get_basic_strategy(h, up("A")) == "H"

    def test_hard_9_vs_2_is_hit(self):
        h = hard_hand("5", "4")
        assert get_basic_strategy(h, up("2")) == "H"


# ===========================================================================
# SOFT STRATEGY — cas clés
# ===========================================================================

class TestSoftStrategy:
    @pytest.mark.parametrize("non_ace, dealer_rank, expected", [
        # A,7 soft 18 vs 3 → Ds
        ("7", "3",  "Ds"),
        # A,7 soft 18 vs 9 → H
        ("7", "9",  "H"),
        # A,8 soft 19 vs 6 → Ds
        ("8", "6",  "Ds"),
        # A,8 soft 19 vs 5 → S
        ("8", "5",  "S"),
        # A,6 soft 17 vs 4 → D
        ("6", "4",  "D"),
        # A,6 soft 17 vs 2 → H
        ("6", "2",  "H"),
        # A,2 soft 13 vs 5 → D
        ("2", "5",  "D"),
        # A,2 soft 13 vs 4 → H
        ("2", "4",  "H"),
        # A,4 soft 15 vs 6 → D
        ("4", "6",  "D"),
        # A,9 soft 20 vs A → S
        ("9", "A",  "S"),
    ])
    def test_soft(self, non_ace, dealer_rank, expected):
        h = soft_hand(non_ace)
        assert get_basic_strategy(h, up(dealer_rank)) == expected

    def test_soft_18_vs_7_is_stand(self):
        h = soft_hand("7")
        assert get_basic_strategy(h, up("7")) == "S"

    def test_soft_18_vs_2_is_double_stand(self):
        h = soft_hand("7")
        assert get_basic_strategy(h, up("2")) == "Ds"

    def test_soft_17_vs_7_is_hit(self):
        h = soft_hand("6")
        assert get_basic_strategy(h, up("7")) == "H"

    def test_soft_16_vs_4_is_double(self):
        h = soft_hand("5")
        assert get_basic_strategy(h, up("4")) == "D"

    def test_soft_14_vs_5_is_double(self):
        h = soft_hand("3")
        assert get_basic_strategy(h, up("5")) == "D"

    def test_soft_hand_is_recognised(self):
        h = soft_hand("6")
        assert h.is_soft is True
        assert h.value == 17


# ===========================================================================
# SPLIT STRATEGY — cas clés
# ===========================================================================

class TestSplitStrategy:
    @pytest.mark.parametrize("rank, dealer_rank, expected", [
        # A,A toujours splitter
        ("A", "5", "Y"),
        ("A", "A", "Y"),
        # 8,8 toujours splitter
        ("8", "10", "Y"),
        ("8", "A",  "Y"),
        # 9,9 vs 7 → S (stand)
        ("9", "7",  "S"),
        # 9,9 vs 2 → Y
        ("9", "2",  "Y"),
        # 9,9 vs 10 → S
        ("9", "10", "S"),
        # 5,5 → N split → fallback hard 10 vs 6 → D
        ("5", "6",  "D"),
        # 10,10 → N split → fallback hard 20 → S
        ("10","5",  "S"),
        # 3,3 vs 2 → Y/N
        ("3", "2",  "Y/N"),
        # 3,3 vs 4 → Y
        ("3", "4",  "Y"),
        # 6,6 vs 2 → Y/N
        ("6", "2",  "Y/N"),
        # 4,4 vs 5 → Y/N
        ("4", "5",  "Y/N"),
        # 7,7 vs 8 → N split → fallback hard 14 vs 8 → H
        ("7", "8",  "H"),
    ])
    def test_split(self, rank, dealer_rank, expected):
        h = pair_hand(rank)
        assert get_basic_strategy(h, up(dealer_rank)) == expected

    def test_pair_55_treated_as_hard_10_vs_6(self):
        """5,5 → N split → fallback hard 10 → D vs 6."""
        h = pair_hand("5")
        assert get_basic_strategy(h, up("6")) == "D"

    def test_pair_55_vs_10_is_hit(self):
        """5,5 vs 10 → N split → hard 10 vs 10 → H."""
        h = pair_hand("5")
        assert get_basic_strategy(h, up("10")) == "H"

    def test_pair_77_vs_8_is_hit(self):
        """7,7 → N split → hard 14 vs 8 → H."""
        h = pair_hand("7")
        assert get_basic_strategy(h, up("8")) == "H"

    def test_pair_1010_vs_5_is_stand(self):
        """10,10 → N split → hard 20 vs 5 → S."""
        h = pair_hand("10")
        assert get_basic_strategy(h, up("5")) == "S"

    def test_pair_99_vs_7_falls_through_to_stand(self):
        """9,9 vs 7 → 'S' directement depuis la table split."""
        h = pair_hand("9")
        assert get_basic_strategy(h, up("7")) == "S"

    def test_pair_aa_split_not_soft(self):
        """A,A doit retourner 'Y' et non consulter soft strategy."""
        h = pair_hand("A")
        assert get_basic_strategy(h, up("6")) == "Y"


# ===========================================================================
# SURRENDER
# ===========================================================================

class TestSurrenderDict:
    def test_surrender_16_vs_9(self):
        assert SURRENDER[(16, "9")] is True

    def test_surrender_16_vs_10(self):
        assert SURRENDER[(16, "10")] is True

    def test_surrender_16_vs_ace(self):
        assert SURRENDER[(16, "A")] is True

    def test_surrender_15_vs_10(self):
        assert SURRENDER[(15, "10")] is True

    def test_surrender_15_vs_ace(self):
        assert SURRENDER[(15, "A")] is True

    def test_no_surrender_14(self):
        assert (14, "10") not in SURRENDER

    def test_hard_strategy_has_sur_for_surrender_cases(self):
        for (total, upcard) in SURRENDER:
            assert HARD_STRATEGY[(total, upcard)] == "SUR", (
                f"Attendu SUR pour ({total},{upcard})"
            )
