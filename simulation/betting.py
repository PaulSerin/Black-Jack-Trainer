"""
betting.py - Logique de mise pour la simulation Monte Carlo.

Séparé de simulator.py pour permettre de tester et modifier
la rampe de mise indépendamment du moteur de simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from simulation.config import BettingConfig


# ---------------------------------------------------------------------------
# Betting ramp
# ---------------------------------------------------------------------------

# Chaque breakpoint est (tc_threshold, units).
# La rampe est parcourue dans l'ordre ; le premier seuil ≥ tc gagne.
# Si aucun seuil ne correspond, on utilise spread_max.
DEFAULT_RAMP: List[Tuple[float, int]] = [
    (0.0,  1),    # TC ≤ 0  → 1 unité
    (1.0,  2),    # TC == 1 → 2 unités
    (2.0,  4),    # TC == 2 → 4 unités
    (3.0,  8),    # TC == 3 → 8 unités
    (4.0,  9999), # TC ≥ 4  → spread_max (capé par compute_bet via min)
]


@dataclass
class BettingRamp:
    """
    Rampe de mise configurable.

    breakpoints : liste triée de (tc_threshold, units).
    La mise est déterminée par le premier breakpoint dont le TC est ≥ threshold.
    Au-delà du dernier breakpoint, la mise est spread_max.
    """
    breakpoints: List[Tuple[float, int]] = field(
        default_factory=lambda: list(DEFAULT_RAMP)
    )

    def __post_init__(self) -> None:
        # Trier les breakpoints par seuil croissant
        self.breakpoints = sorted(self.breakpoints, key=lambda x: x[0])


def compute_bet(tc: float, config: BettingConfig, ramp: BettingRamp) -> float:
    """
    Calcule la mise en euros pour un true count donné.

    Algorithme :
    1. Si tc ≤ premier seuil de la rampe → spread_min unités
    2. Parcourir les breakpoints ; utiliser le dernier dont tc ≥ seuil
    3. Plafonner à spread_max unités

    Retourne la mise en euros (units × unit_size).
    """
    units = config.spread_min

    for threshold, bp_units in ramp.breakpoints:
        if tc >= threshold:
            units = bp_units
        else:
            break

    # Plafonner entre spread_min et spread_max
    units = max(config.spread_min, min(config.spread_max, units))
    return units * config.unit_size
