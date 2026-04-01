"""
test_strategy.py - Tests unitaires pour simulation/strategy.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from simulation.engine import Card, Hand
from simulation.strategy import (
    HARD_STRATEGY, SOFT_STRATEGY, SPLIT_STRATEGY, SURRENDER,
    UPCARDS, get_basic_strategy, _normalize_upcard,
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
# Normalisation des upcards figures
# ===========================================================================

class TestNormalizeUpcard:
    def test_j_normalized_to_10(self):
        assert _normalize_upcard("J") == "10"

    def test_q_normalized_to_10(self):
        assert _normalize_upcard("Q") == "10"

    def test_k_normalized_to_10(self):
        assert _normalize_upcard("K") == "10"

    def test_10_unchanged(self):
        assert _normalize_upcard("10") == "10"

    def test_a_unchanged(self):
        assert _normalize_upcard("A") == "A"

    def test_numeric_ranks_unchanged(self):
        for r in ("2", "3", "4", "5", "6", "7", "8", "9"):
            assert _normalize_upcard(r) == r


# ===========================================================================
# Bug fix : J/Q/K doivent donner le même résultat que "10"
# ===========================================================================

class TestFigureUpcardNormalization:
    """
    Avant le fix, J/Q/K retournaient "S" (défaut) au lieu de la vraie action.
    Ces tests vérifient que la normalisation fonctionne.
    """

    @pytest.mark.parametrize("figure", ["J", "Q", "K"])
    def test_hard_11_vs_figure_is_double(self, figure):
        """Hard 11 vs 10 → D. Avec J/Q/K le bug retournait 'S'."""
        h = hard_hand("7", "4")
        assert get_basic_strategy(h, up(figure)) == "D"

    @pytest.mark.parametrize("figure", ["J", "Q", "K"])
    def test_hard_16_vs_figure_is_surrender(self, figure):
        """Hard 16 vs 10 → SUR. Avec J/Q/K le bug retournait 'S'."""
        h = hard_hand("10", "6")
        assert get_basic_strategy(h, up(figure)) == "SUR"

    @pytest.mark.parametrize("figure", ["J", "Q", "K"])
    def test_hard_15_vs_figure_is_surrender(self, figure):
        """Hard 15 vs 10 → SUR."""
        h = hard_hand("10", "5")
        assert get_basic_strategy(h, up(figure)) == "SUR"

    @pytest.mark.parametrize("figure", ["J", "Q", "K"])
    def test_hard_10_vs_figure_is_hit(self, figure):
        """Hard 10 vs 10 → H (pas D, pas S)."""
        h = hard_hand("6", "4")
        assert get_basic_strategy(h, up(figure)) == "H"

    @pytest.mark.parametrize("figure", ["J", "Q", "K"])
    def test_hard_12_vs_figure_is_hit(self, figure):
        """Hard 12 vs 10 → H."""
        h = hard_hand("7", "5")
        assert get_basic_strategy(h, up(figure)) == "H"

    @pytest.mark.parametrize("figure", ["J", "Q", "K"])
    def test_figure_same_as_10(self, figure):
        """Pour toute main, J/Q/K doit donner le même résultat que '10'."""
        hands = [
            hard_hand("9", "7"),    # hard 16
            hard_hand("7", "5"),    # hard 12
            hard_hand("6", "4"),    # hard 10
            hard_hand("7", "4"),    # hard 11
            hard_hand("5", "4"),    # hard 9
            soft_hand("7"),         # A,7 soft 18
            pair_hand("8"),         # 8,8
        ]
        for h in hands:
            assert get_basic_strategy(h, up(figure)) == get_basic_strategy(h, up("10")), \
                f"Discordance pour {[str(c) for c in h.cards]} vs {figure}"


# ===========================================================================
# Intégrité des tables
# ===========================================================================

class TestTableIntegrity:
    def test_hard_strategy_size(self):
        assert len(HARD_STRATEGY) == 10 * 10  # 10 totaux × 10 upcards

    def test_soft_strategy_size(self):
        assert len(SOFT_STRATEGY) == 8 * 10

    def test_split_strategy_size(self):
        assert len(SPLIT_STRATEGY) == 10 * 10

    def test_all_hard_keys_present(self):
        for total in range(8, 18):
            for upcard in UPCARDS:
                assert (total, upcard) in HARD_STRATEGY

    def test_all_soft_keys_present(self):
        for nav in range(2, 10):
            for upcard in UPCARDS:
                assert (nav, upcard) in SOFT_STRATEGY

    def test_all_split_keys_present(self):
        for pv in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
            for upcard in UPCARDS:
                assert (pv, upcard) in SPLIT_STRATEGY

    def test_hard_actions_valid(self):
        valid = {"H", "S", "D", "Ds", "SUR"}
        for key, action in HARD_STRATEGY.items():
            assert action in valid, f"Action invalide {key}: {action!r}"

    def test_soft_actions_valid(self):
        valid = {"H", "S", "D", "Ds"}
        for key, action in SOFT_STRATEGY.items():
            assert action in valid, f"Action invalide {key}: {action!r}"

    def test_split_actions_valid(self):
        valid = {"Y", "Y/N", "N", "S"}
        for key, action in SPLIT_STRATEGY.items():
            assert action in valid, f"Action invalide {key}: {action!r}"


# ===========================================================================
# Hard strategy - cas clés
# ===========================================================================

class TestHardStrategy:
    @pytest.mark.parametrize("ranks,upcard,expected", [
        (("9","7"),  "9",  "SUR"),   # 16 vs 9 → SUR
        (("9","7"),  "10", "SUR"),   # 16 vs 10 → SUR
        (("10","6"), "4",  "S"),     # 16 vs 4 → S
        (("10","5"), "3",  "S"),     # hard 15 vs 3 → S
        (("8","4"),  "6",  "S"),     # hard 12 vs 6 → S
        (("6","4"),  "7",  "D"),     # hard 10 vs 7 → D
        (("6","5"),  "5",  "D"),     # hard 11 vs 5 → D
        (("7","4"),  "A",  "H"),     # hard 11 vs A → H
        (("7","5"),  "10", "H"),     # hard 12 vs 10 → H
        (("10","3"), "A",  "H"),     # hard 13 vs A → H
    ])
    def test_hard(self, ranks, upcard, expected):
        h = hard_hand(*ranks)
        assert get_basic_strategy(h, up(upcard)) == expected

    def test_hard_16_vs_7_is_hit(self):
        assert get_basic_strategy(hard_hand("9", "7"), up("7")) == "H"

    def test_hard_16_vs_6_is_stand(self):
        assert get_basic_strategy(hard_hand("9", "7"), up("6")) == "S"

    def test_hard_12_vs_2_is_hit(self):
        assert get_basic_strategy(hard_hand("7", "5"), up("2")) == "H"

    def test_hard_12_vs_6_is_stand(self):
        assert get_basic_strategy(hard_hand("7", "5"), up("6")) == "S"

    def test_hard_total_below_8_is_hit(self):
        assert get_basic_strategy(hard_hand("3", "4"), up("6")) == "H"

    def test_hard_total_above_17_is_stand(self):
        assert get_basic_strategy(hard_hand("10", "9"), up("7")) == "S"

    def test_hard_11_vs_ace_is_hit(self):
        assert get_basic_strategy(hard_hand("6", "5"), up("A")) == "H"

    def test_hard_10_vs_ace_is_hit(self):
        assert get_basic_strategy(hard_hand("6", "4"), up("A")) == "H"

    def test_hard_9_vs_2_is_hit(self):
        assert get_basic_strategy(hard_hand("5", "4"), up("2")) == "H"


# ===========================================================================
# Soft strategy - cas clés
# ===========================================================================

class TestSoftStrategy:
    @pytest.mark.parametrize("non_ace,upcard,expected", [
        ("7", "3",  "Ds"),  # A,7 vs 3 → Ds
        ("7", "9",  "H"),   # A,7 vs 9 → H
        ("8", "6",  "Ds"),  # A,8 vs 6 → Ds
        ("8", "5",  "S"),   # A,8 vs 5 → S
        ("6", "4",  "D"),   # A,6 vs 4 → D
        ("6", "2",  "H"),   # A,6 vs 2 → H
        ("2", "5",  "D"),   # A,2 vs 5 → D
        ("2", "4",  "H"),   # A,2 vs 4 → H
        ("4", "6",  "D"),   # A,4 vs 6 → D
        ("9", "A",  "S"),   # A,9 vs A → S
    ])
    def test_soft(self, non_ace, upcard, expected):
        h = soft_hand(non_ace)
        assert get_basic_strategy(h, up(upcard)) == expected

    def test_soft_18_vs_7_is_stand(self):
        assert get_basic_strategy(soft_hand("7"), up("7")) == "S"

    def test_soft_18_vs_2_is_double_stand(self):
        assert get_basic_strategy(soft_hand("7"), up("2")) == "Ds"

    def test_soft_17_vs_7_is_hit(self):
        assert get_basic_strategy(soft_hand("6"), up("7")) == "H"

    def test_soft_hand_is_recognised(self):
        h = soft_hand("6")
        assert h.is_soft is True
        assert h.value == 17


# ===========================================================================
# Split strategy - cas clés
# ===========================================================================

class TestSplitStrategy:
    @pytest.mark.parametrize("rank,dealer_rank,expected", [
        ("A", "5",  "Y"),    # A,A vs 5 → Y
        ("A", "A",  "Y"),    # A,A vs A → Y
        ("8", "10", "Y"),    # 8,8 vs 10 → Y
        ("8", "A",  "Y"),    # 8,8 vs A → Y
        ("9", "7",  "S"),    # 9,9 vs 7 → S
        ("9", "2",  "Y"),    # 9,9 vs 2 → Y
        ("9", "10", "S"),    # 9,9 vs 10 → S
        ("5", "6",  "D"),    # 5,5 → N → hard 10 vs 6 → D
        ("10","5",  "S"),    # 10,10 → N → hard 20 → S
        ("3", "2",  "Y/N"),  # 3,3 vs 2 → Y/N
        ("3", "4",  "Y"),    # 3,3 vs 4 → Y
        ("6", "2",  "Y/N"),  # 6,6 vs 2 → Y/N
        ("4", "5",  "Y/N"),  # 4,4 vs 5 → Y/N
        ("7", "8",  "H"),    # 7,7 → N → hard 14 vs 8 → H
    ])
    def test_split(self, rank, dealer_rank, expected):
        h = pair_hand(rank)
        assert get_basic_strategy(h, up(dealer_rank)) == expected

    def test_pair_55_treated_as_hard_10_vs_6(self):
        assert get_basic_strategy(pair_hand("5"), up("6")) == "D"

    def test_pair_1010_vs_5_is_stand(self):
        assert get_basic_strategy(pair_hand("10"), up("5")) == "S"

    def test_pair_aa_split_not_soft(self):
        assert get_basic_strategy(pair_hand("A"), up("6")) == "Y"

    # Figures en tant que paire
    @pytest.mark.parametrize("figure", ["J", "Q", "K"])
    def test_pair_figures_same_as_pair_10(self, figure):
        """K,K doit être traité identiquement à 10,10."""
        for upcard in ("2", "5", "10", "A"):
            h_fig = pair_hand(figure)
            h_ten = pair_hand("10")
            assert get_basic_strategy(h_fig, up(upcard)) == \
                   get_basic_strategy(h_ten, up(upcard)), \
                   f"Discordance paire {figure} vs upcard {upcard}"


# ===========================================================================
# SURRENDER dict
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
            assert HARD_STRATEGY[(total, upcard)] == "SUR"
