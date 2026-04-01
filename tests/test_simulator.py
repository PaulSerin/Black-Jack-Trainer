"""
test_simulator.py - Tests unitaires pour la simulation Monte Carlo.
"""

import pytest

from simulation.config import BettingConfig, SimConfig, TableRules, SimulationResult
from simulation.betting import BettingRamp, compute_bet
from simulation.simulator import simulate


# ---------------------------------------------------------------------------
# BettingConfig
# ---------------------------------------------------------------------------

class TestBettingConfig:
    def test_valid_spread(self):
        bc = BettingConfig.from_string("1-12")
        assert bc.spread_min == 1
        assert bc.spread_max == 12

    def test_custom_unit(self):
        bc = BettingConfig.from_string("2-8", unit_size=50.0)
        assert bc.unit_size == 50.0

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            BettingConfig.from_string("12")

    def test_min_must_be_positive(self):
        with pytest.raises(ValueError):
            BettingConfig.from_string("0-12")

    def test_max_gte_min(self):
        with pytest.raises(ValueError):
            BettingConfig.from_string("8-1")


# ---------------------------------------------------------------------------
# BettingRamp
# ---------------------------------------------------------------------------

class TestComputeBet:
    def setup_method(self):
        self.config = BettingConfig(spread_min=1, spread_max=12, unit_size=25.0)
        self.ramp   = BettingRamp()

    def test_negative_tc_returns_min(self):
        assert compute_bet(-2.0, self.config, self.ramp) == 25.0

    def test_zero_tc_returns_min(self):
        assert compute_bet(0.0, self.config, self.ramp) == 25.0

    def test_tc1_returns_2_units(self):
        assert compute_bet(1.0, self.config, self.ramp) == 50.0

    def test_tc2_returns_4_units(self):
        assert compute_bet(2.0, self.config, self.ramp) == 100.0

    def test_tc3_returns_8_units(self):
        assert compute_bet(3.0, self.config, self.ramp) == 200.0

    def test_tc4_returns_max(self):
        assert compute_bet(4.0, self.config, self.ramp) == 12 * 25.0

    def test_tc10_capped_at_max(self):
        assert compute_bet(10.0, self.config, self.ramp) == 12 * 25.0


# ---------------------------------------------------------------------------
# SimConfig
# ---------------------------------------------------------------------------

class TestSimConfig:
    def test_default_config(self):
        cfg = SimConfig()
        assert cfg.hands == 100_000
        assert cfg.decks == 6
        assert cfg.penetration == 0.75

    def test_invalid_hands(self):
        with pytest.raises(ValueError):
            SimConfig(hands=0)

    def test_invalid_decks(self):
        with pytest.raises(ValueError):
            SimConfig(decks=0)

    def test_invalid_penetration(self):
        with pytest.raises(ValueError):
            SimConfig(penetration=0.0)


# ---------------------------------------------------------------------------
# Simulation smoke tests
# ---------------------------------------------------------------------------

class TestSimulate:

    def _run(self, hands=500, seed=42, spread="1-1", unit_size=25.0, bankroll=50000.0):
        cfg = SimConfig(
            hands            = hands,
            decks            = 6,
            penetration      = 0.75,
            betting          = BettingConfig.from_string(spread, unit_size=unit_size),
            rules            = TableRules(),
            initial_bankroll = bankroll,
            seed             = seed,
        )
        return simulate(cfg)

    def test_returns_simulation_result(self):
        assert isinstance(self._run(), SimulationResult)

    def test_hands_played_equals_config(self):
        assert self._run(hands=200).hands_played == 200

    def test_wins_losses_pushes_cover_all_outcomes(self):
        r = self._run(hands=500)
        # wins+losses+pushes ≥ hands_played (splits génèrent plusieurs sous-mains)
        assert r.wins + r.losses + r.pushes >= r.hands_played

    def test_total_wagered_positive(self):
        assert self._run().total_wagered > 0

    def test_reproducible_with_seed(self):
        r1 = self._run(seed=123)
        r2 = self._run(seed=123)
        assert r1.total_profit == r2.total_profit

    def test_different_seeds_differ(self):
        assert self._run(seed=1).total_profit != self._run(seed=2).total_profit

    def test_bankroll_tracking(self):
        r = self._run(hands=500)
        assert r.max_bankroll >= r.final_bankroll
        assert r.min_bankroll <= r.final_bankroll

    def test_blackjacks_nonzero(self):
        assert self._run(hands=1000, seed=7).blackjacks > 0

    def test_profit_std_positive(self):
        assert self._run(hands=500).profit_std >= 0.0

    def test_summary_contains_key_fields(self):
        s = self._run(hands=100).summary()
        assert "EV" in s
        assert "Wins" in s


# ---------------------------------------------------------------------------
# Test EV - le plus important
# EV flat bet basic strategy 6 decks S17 DAS SUR ≈ -0.5%
# Tolérance large pour 1M mains : [-1.0%, 0.0%]
# ---------------------------------------------------------------------------

class TestEV:

    def test_flat_bet_ev_near_minus_half_percent(self):
        """
        Flat bet (spread 1-1) + basic strategy + règles favorables
        doit converger vers ~-0.5% EV.
        Tolérance : [-1.0%, 0.0%].
        """
        cfg = SimConfig(
            hands            = 1_000_000,
            decks            = 6,
            penetration      = 0.75,
            betting          = BettingConfig(spread_min=1, spread_max=1, unit_size=10.0),
            rules            = TableRules(
                dealer_hits_soft_17 = False,  # S17
                double_after_split  = True,   # DAS
                surrender_allowed   = True,   # Late surrender
                blackjack_payout    = 1.5,    # 3:2
            ),
            initial_bankroll = 10_000_000.0,
            seed             = 0,
        )
        result = simulate(cfg)
        ev = result.ev_percent

        assert result.hands_played == 1_000_000, \
            f"Bankroll epuisee apres {result.hands_played} mains - augmenter initial_bankroll"
        assert -1.0 <= ev <= 0.0, (
            f"EV = {ev:.4f}% hors de la plage attendue [-1.0%, 0.0%].\n"
            f"Verifier get_basic_strategy() et la normalisation J/Q/K."
        )
