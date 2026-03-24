"""
test_deviations.py — Tests unitaires pour simulation/deviations.py
Couvre les 18 deviations Illustrious 18 + override sur basic strategy.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from simulation.engine import Card, Hand
from simulation.deviations import (
    ILLUSTRIOUS_18, Deviation,
    get_deviation, get_action, should_take_insurance,
)
from simulation.strategy import get_basic_strategy


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
# Intégrité de la liste ILLUSTRIOUS_18
# ===========================================================================

class TestI18Integrity:
    def test_exactly_18_deviations(self):
        assert len(ILLUSTRIOUS_18) == 18

    def test_all_operators_valid(self):
        for dev in ILLUSTRIOUS_18:
            assert dev.operator in (">=", "<="), f"{dev.situation}: opérateur invalide"

    def test_all_hand_types_valid(self):
        for dev in ILLUSTRIOUS_18:
            assert dev.hand_type in ("hard", "pair", "insurance")

    def test_all_actions_valid(self):
        for dev in ILLUSTRIOUS_18:
            assert dev.action in ("S", "D", "H", "Y", "INS")

    def test_one_insurance_deviation(self):
        ins = [d for d in ILLUSTRIOUS_18 if d.hand_type == "insurance"]
        assert len(ins) == 1
        assert ins[0].tc_threshold == 3.0
        assert ins[0].action == "INS"

    def test_two_pair_deviations(self):
        pairs = [d for d in ILLUSTRIOUS_18 if d.hand_type == "pair"]
        assert len(pairs) == 2
        situations = {d.situation for d in pairs}
        assert "10,10 vs 5" in situations
        assert "10,10 vs 6" in situations

    def test_fifteen_hard_deviations(self):
        # 1 insurance + 2 pair + 15 hard = 18
        hards = [d for d in ILLUSTRIOUS_18 if d.hand_type == "hard"]
        assert len(hards) == 15

    def test_positive_deviations_have_gte_operator(self):
        """Les déviations qui recommandent S/D/Y sur une action plus passive → >=."""
        positive_actions = {"S", "D", "Y"}
        for dev in ILLUSTRIOUS_18:
            if dev.hand_type == "insurance":
                continue
            if dev.operator == ">=":
                assert dev.action in positive_actions | {"INS"}

    def test_negative_deviations_have_lte_operator(self):
        """Les déviations qui recommandent H (hit au lieu de stand) → <=."""
        for dev in ILLUSTRIOUS_18:
            if dev.action == "H":
                assert dev.operator == "<="


# ===========================================================================
# Les 18 déviations — test individuel (seuil, en dessous, au dessus)
# ===========================================================================

class TestEachDeviation:
    """
    Pour chaque déviation :
      - Au seuil exact       → la déviation s'applique
      - Juste de l'autre côté → None (basic strategy)
    """

    # ── Insurance (via should_take_insurance) ──────────────────────────────

    def test_insurance_at_threshold(self):
        assert should_take_insurance(up("A"), 3.0) is True

    def test_insurance_above_threshold(self):
        assert should_take_insurance(up("A"), 5.0) is True

    def test_insurance_below_threshold(self):
        assert should_take_insurance(up("A"), 2.5) is False

    def test_insurance_only_vs_ace(self):
        """Insurance ne s'offre que si dealer montre un As."""
        assert should_take_insurance(up("10"), 5.0) is False
        assert should_take_insurance(up("2"), 5.0) is False

    def test_insurance_not_in_get_deviation(self):
        """get_deviation ne retourne jamais INS (décision séparée)."""
        h = hard_hand("9", "7")
        assert get_deviation(h, up("A"), 10.0) != "INS"

    # ── 16 vs 10 ───────────────────────────────────────────────────────────

    def test_16_vs_10_at_zero(self):
        h = hard_hand("10", "6")
        assert get_deviation(h, up("10"), 0.0) == "S"

    def test_16_vs_10_negative_tc(self):
        h = hard_hand("10", "6")
        assert get_deviation(h, up("10"), -0.5) is None

    def test_16_vs_10_positive_tc(self):
        h = hard_hand("10", "6")
        assert get_deviation(h, up("10"), 2.0) == "S"

    # ── 15 vs 10 ───────────────────────────────────────────────────────────

    def test_15_vs_10_at_threshold(self):
        h = hard_hand("10", "5")
        assert get_deviation(h, up("10"), 4.0) == "S"

    def test_15_vs_10_below_threshold(self):
        h = hard_hand("10", "5")
        assert get_deviation(h, up("10"), 3.5) is None

    # ── 10,10 vs 5 ─────────────────────────────────────────────────────────

    def test_10_10_vs_5_at_threshold(self):
        h = pair_hand("10")
        assert get_deviation(h, up("5"), 5.0) == "Y"

    def test_10_10_vs_5_below_threshold(self):
        h = pair_hand("10")
        assert get_deviation(h, up("5"), 4.5) is None

    def test_10_10_vs_5_with_face_pair(self):
        """K,K est une paire de valeur 10, même règle."""
        h = pair_hand("K")
        assert get_deviation(h, up("5"), 5.0) == "Y"

    # ── 10,10 vs 6 ─────────────────────────────────────────────────────────

    def test_10_10_vs_6_at_threshold(self):
        h = pair_hand("10")
        assert get_deviation(h, up("6"), 4.0) == "Y"

    def test_10_10_vs_6_below_threshold(self):
        h = pair_hand("10")
        assert get_deviation(h, up("6"), 3.5) is None

    # ── Hard 10 vs 10 ──────────────────────────────────────────────────────

    def test_hard_10_vs_10_at_threshold(self):
        h = hard_hand("6", "4")   # hard 10, non-paire
        assert get_deviation(h, up("10"), 4.0) == "D"

    def test_hard_10_vs_10_below_threshold(self):
        h = hard_hand("6", "4")
        assert get_deviation(h, up("10"), 3.5) is None

    def test_hard_10_vs_10_not_triggered_for_pair_55(self):
        """5,5 est une paire ; la déviation hard ne s'applique pas."""
        h = pair_hand("5")
        assert get_deviation(h, up("10"), 5.0) is None

    # ── 12 vs 3 ────────────────────────────────────────────────────────────

    def test_12_vs_3_at_threshold(self):
        h = hard_hand("7", "5")
        assert get_deviation(h, up("3"), 2.0) == "S"

    def test_12_vs_3_below_threshold(self):
        h = hard_hand("7", "5")
        assert get_deviation(h, up("3"), 1.5) is None

    # ── 12 vs 2 ────────────────────────────────────────────────────────────

    def test_12_vs_2_at_threshold(self):
        h = hard_hand("7", "5")
        assert get_deviation(h, up("2"), 3.0) == "S"

    def test_12_vs_2_below_threshold(self):
        h = hard_hand("7", "5")
        assert get_deviation(h, up("2"), 2.5) is None

    # ── 11 vs A ────────────────────────────────────────────────────────────

    def test_11_vs_a_at_threshold(self):
        h = hard_hand("7", "4")
        assert get_deviation(h, up("A"), 1.0) == "D"

    def test_11_vs_a_below_threshold(self):
        h = hard_hand("7", "4")
        assert get_deviation(h, up("A"), 0.5) is None

    # ── 9 vs 2 ─────────────────────────────────────────────────────────────

    def test_9_vs_2_at_threshold(self):
        h = hard_hand("5", "4")
        assert get_deviation(h, up("2"), 1.0) == "D"

    def test_9_vs_2_below_threshold(self):
        h = hard_hand("5", "4")
        assert get_deviation(h, up("2"), 0.5) is None

    # ── Hard 10 vs A ───────────────────────────────────────────────────────

    def test_hard_10_vs_a_at_threshold(self):
        h = hard_hand("6", "4")
        assert get_deviation(h, up("A"), 4.0) == "D"

    def test_hard_10_vs_a_below_threshold(self):
        h = hard_hand("6", "4")
        assert get_deviation(h, up("A"), 3.5) is None

    # ── Hard 9 vs 7 ────────────────────────────────────────────────────────

    def test_hard_9_vs_7_at_threshold(self):
        h = hard_hand("5", "4")
        assert get_deviation(h, up("7"), 3.0) == "D"

    def test_hard_9_vs_7_below_threshold(self):
        h = hard_hand("5", "4")
        assert get_deviation(h, up("7"), 2.5) is None

    # ── 16 vs 9 ────────────────────────────────────────────────────────────

    def test_16_vs_9_at_threshold(self):
        h = hard_hand("10", "6")
        assert get_deviation(h, up("9"), 5.0) == "S"

    def test_16_vs_9_below_threshold(self):
        h = hard_hand("10", "6")
        assert get_deviation(h, up("9"), 4.5) is None

    # ── 13 vs 2 (negative) ─────────────────────────────────────────────────

    def test_13_vs_2_at_threshold(self):
        h = hard_hand("7", "6")
        assert get_deviation(h, up("2"), -1.0) == "H"

    def test_13_vs_2_above_threshold(self):
        """TC = -0.5 > -1.0 → pas de déviation, basic strategy (S)."""
        h = hard_hand("7", "6")
        assert get_deviation(h, up("2"), -0.5) is None

    def test_13_vs_2_well_below_threshold(self):
        h = hard_hand("7", "6")
        assert get_deviation(h, up("2"), -3.0) == "H"

    # ── 12 vs 4 (negative) ─────────────────────────────────────────────────

    def test_12_vs_4_at_threshold(self):
        h = hard_hand("7", "5")
        assert get_deviation(h, up("4"), 0.0) == "H"

    def test_12_vs_4_above_threshold(self):
        h = hard_hand("7", "5")
        assert get_deviation(h, up("4"), 0.5) is None

    # ── 12 vs 5 (negative) ─────────────────────────────────────────────────

    def test_12_vs_5_at_threshold(self):
        h = hard_hand("7", "5")
        assert get_deviation(h, up("5"), -2.0) == "H"

    def test_12_vs_5_above_threshold(self):
        h = hard_hand("7", "5")
        assert get_deviation(h, up("5"), -1.5) is None

    # ── 12 vs 6 (negative) ─────────────────────────────────────────────────

    def test_12_vs_6_at_threshold(self):
        h = hard_hand("7", "5")
        assert get_deviation(h, up("6"), -1.0) == "H"

    def test_12_vs_6_above_threshold(self):
        h = hard_hand("7", "5")
        assert get_deviation(h, up("6"), -0.5) is None

    # ── 13 vs 3 (negative) ─────────────────────────────────────────────────

    def test_13_vs_3_at_threshold(self):
        h = hard_hand("7", "6")
        assert get_deviation(h, up("3"), -2.0) == "H"

    def test_13_vs_3_above_threshold(self):
        h = hard_hand("7", "6")
        assert get_deviation(h, up("3"), -1.5) is None


# ===========================================================================
# Isolation : soft hands ne déclenchent pas les déviations hard
# ===========================================================================

class TestSoftHandsIgnoreHardDeviations:
    def test_soft_16_vs_10_not_triggered(self):
        """A,5 = soft 16. La déviation '16 vs 10' est hard-only."""
        h = soft_hand("5")
        assert h.is_soft is True
        assert h.value == 16
        assert get_deviation(h, up("10"), 2.0) is None

    def test_soft_12_vs_3_not_triggered(self):
        """A,A = soft 12. La déviation '12 vs 3' ne doit pas s'appliquer."""
        h = pair_hand("A")
        # is_pair = True et is_soft = True pour A,A ; le test pair prime
        # Ici on crée une main soft 12 non-paire : impossible avec 2 cartes
        # → on vérifie juste que la déviation hard ne s'applique pas à soft 16
        h2 = soft_hand("5")  # soft 16, pas 12 — test de principe
        assert get_deviation(h2, up("3"), 3.0) is None

    def test_soft_hand_is_never_matched_by_hard_deviation(self):
        """Parcourir toutes les déviations hard : aucune ne doit s'appliquer
        à une main soft dont le total correspond à player_value."""
        hard_devs = [d for d in ILLUSTRIOUS_18 if d.hand_type == "hard"]
        for dev in hard_devs:
            total = dev.player_value
            if total < 11:
                continue   # soft 9, 10 irréalistes
            ace_plus = total - 11
            if 2 <= ace_plus <= 9:
                h = soft_hand(str(ace_plus))
                result = get_deviation(h, up(dev.dealer_rank), dev.tc_threshold + 100)
                assert result is None, (
                    f"Déviation hard '{dev.situation}' appliquée à soft {total}"
                )


# ===========================================================================
# Override : déviation > basic strategy (get_action)
# ===========================================================================

class TestDeviationOverridesBasicStrategy:
    def test_16_vs_10_tc_zero_overrides_sur(self):
        """Basic: SUR. Déviation TC=0: S. get_action doit retourner S."""
        h = hard_hand("10", "6")
        dealer = up("10")
        assert get_basic_strategy(h, dealer) == "SUR"
        assert get_action(h, dealer, 0.0) == "S"

    def test_16_vs_10_negative_tc_returns_basic(self):
        """TC=-1 → pas de déviation → get_action retourne SUR (basic)."""
        h = hard_hand("10", "6")
        dealer = up("10")
        assert get_action(h, dealer, -1.0) == "SUR"

    def test_15_vs_10_tc4_overrides_sur(self):
        """Basic: SUR. Déviation TC=4: S."""
        h = hard_hand("10", "5")
        dealer = up("10")
        assert get_basic_strategy(h, dealer) == "SUR"
        assert get_action(h, dealer, 4.0) == "S"

    def test_12_vs_3_tc2_overrides_hit(self):
        """Basic: H. Déviation TC=2: S."""
        h = hard_hand("7", "5")
        dealer = up("3")
        assert get_basic_strategy(h, dealer) == "H"
        assert get_action(h, dealer, 2.0) == "S"

    def test_11_vs_ace_tc1_overrides_hit(self):
        """Basic: H. Déviation TC=1: D."""
        h = hard_hand("7", "4")
        dealer = up("A")
        assert get_basic_strategy(h, dealer) == "H"
        assert get_action(h, dealer, 1.0) == "D"

    def test_9_vs_2_tc1_overrides_hit(self):
        """Basic: H. Déviation TC=1: D."""
        h = hard_hand("5", "4")
        dealer = up("2")
        assert get_basic_strategy(h, dealer) == "H"
        assert get_action(h, dealer, 1.0) == "D"

    def test_10_10_vs_6_tc4_overrides_stand(self):
        """Basic: S (10,10 split=N → hard 20). Déviation TC=4: Y (split)."""
        h = pair_hand("10")
        dealer = up("6")
        # 10,10 split table = N → fallback hard 20 → S
        assert get_basic_strategy(h, dealer) == "S"
        assert get_action(h, dealer, 4.0) == "Y"

    def test_13_vs_2_negative_tc_overrides_stand(self):
        """Basic: S. Déviation TC=-1: H."""
        h = hard_hand("7", "6")
        dealer = up("2")
        assert get_basic_strategy(h, dealer) == "S"
        assert get_action(h, dealer, -1.0) == "H"

    def test_12_vs_4_tc_zero_overrides_stand(self):
        """Basic: S. Déviation TC=0: H."""
        h = hard_hand("7", "5")
        dealer = up("4")
        assert get_basic_strategy(h, dealer) == "S"
        assert get_action(h, dealer, 0.0) == "H"

    def test_12_vs_4_positive_tc_uses_basic(self):
        """TC=0.5 > 0 → pas de déviation → S (basic)."""
        h = hard_hand("7", "5")
        dealer = up("4")
        assert get_action(h, dealer, 0.5) == "S"

    def test_16_vs_9_tc5_overrides_sur(self):
        """Basic: SUR. Déviation TC=5: S."""
        h = hard_hand("10", "6")
        dealer = up("9")
        assert get_basic_strategy(h, dealer) == "SUR"
        assert get_action(h, dealer, 5.0) == "S"

    def test_insurance_decision_via_should_take_insurance(self):
        """should_take_insurance est la bonne API pour l'assurance."""
        assert should_take_insurance(up("A"), 3.0) is True
        assert should_take_insurance(up("A"), 2.5) is False

    def test_insurance_not_in_get_action(self):
        """get_action ne retourne jamais INS ; l'assurance est décidée séparément."""
        h = hard_hand("9", "7")
        # TC=10 : aucune déviation pour 16 vs A dans I18 → SUR (basic)
        assert get_action(h, up("A"), 10.0) == "SUR"

    def test_hard_10_vs_a_tc4_overrides_hit(self):
        """Basic: H. Déviation TC=4: D."""
        h = hard_hand("6", "4")
        dealer = up("A")
        assert get_basic_strategy(h, dealer) == "H"
        assert get_action(h, dealer, 4.0) == "D"

    def test_pair_88_vs_9_tc5_stays_split(self):
        """8,8 est toujours split. La déviation '16 vs 9' (hard) ne s'applique pas."""
        h = pair_hand("8")
        dealer = up("9")
        # Basic strategy → Y (always split 8s)
        assert get_basic_strategy(h, dealer) == "Y"
        # Avec TC=5, on ne doit PAS retourner "S" (déviation hard 16 vs 9)
        assert get_action(h, dealer, 5.0) == "Y"
