"""
config.py — Dataclasses de configuration pour le module de simulation.

Séparé de simulator.py pour permettre :
- l'import de la config depuis une future interface (React, Streamlit, etc.)
- des tests unitaires ciblés sur la config seule
- une évolution facile des paramètres

Aucune dépendance sur le moteur de jeu ici.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Règles de table
# ---------------------------------------------------------------------------

@dataclass
class TableRules:
    """Règles de table configurables."""
    dealer_hits_soft_17: bool = False   # S17 par défaut (stands on soft 17)
    double_after_split:  bool = True    # DAS autorisé
    surrender_allowed:   bool = True    # Late surrender autorisé
    max_split_hands:     int  = 4       # max mains après splits (1 original + 3 splits)
    blackjack_payout:    float = 1.5    # 3:2 standard

    def __post_init__(self) -> None:
        if self.max_split_hands < 1:
            raise ValueError("max_split_hands doit être ≥ 1")
        if self.blackjack_payout <= 0:
            raise ValueError("blackjack_payout doit être > 0")


# ---------------------------------------------------------------------------
# Configuration de mise (betting)
# ---------------------------------------------------------------------------

@dataclass
class BettingConfig:
    """Paramètres de mise en unités + taille d'une unité."""
    spread_min: int   = 1       # mise minimale en unités (au TC neutre/négatif)
    spread_max: int   = 12      # mise maximale en unités (au TC élevé)
    unit_size:  float = 25.0    # valeur d'une unité en € (ou toute devise)

    def __post_init__(self) -> None:
        if self.spread_min < 1:
            raise ValueError("spread_min doit être ≥ 1")
        if self.spread_max < self.spread_min:
            raise ValueError("spread_max doit être ≥ spread_min")
        if self.unit_size <= 0:
            raise ValueError("unit_size doit être > 0")

    @classmethod
    def from_string(cls, spread_str: str, unit_size: float = 25.0) -> "BettingConfig":
        """
        Parse une chaîne du type '1-12' en BettingConfig.
        Exemple : BettingConfig.from_string('1-12', unit_size=25)
        """
        try:
            parts = spread_str.strip().split("-")
            if len(parts) != 2:
                raise ValueError
            return cls(
                spread_min=int(parts[0]),
                spread_max=int(parts[1]),
                unit_size=unit_size,
            )
        except (ValueError, IndexError):
            raise ValueError(
                f"Format de spread invalide : {spread_str!r}. Attendu : 'MIN-MAX' ex. '1-12'"
            )


# ---------------------------------------------------------------------------
# Configuration de simulation
# ---------------------------------------------------------------------------

@dataclass
class SimConfig:
    """Configuration complète d'une simulation Monte Carlo."""
    hands:            int           = 100_000
    decks:            int           = 6
    penetration:      float         = 0.75
    betting:          BettingConfig = field(default_factory=BettingConfig)
    rules:            TableRules    = field(default_factory=TableRules)
    initial_bankroll: float         = 10_000.0
    seed:             Optional[int] = None
    use_deviations:   bool          = False   # True = Illustrious 18 on top of basic strategy
    track_history:    bool          = False   # True = record bankroll snapshots every N rounds
    history_interval: int           = 500     # sample bankroll every N rounds (if track_history)

    def __post_init__(self) -> None:
        if self.hands < 1:
            raise ValueError("hands doit être ≥ 1")
        if self.decks < 1:
            raise ValueError("decks doit être ≥ 1")
        if not (0.0 < self.penetration <= 1.0):
            raise ValueError("penetration doit être dans ]0, 1]")


# ---------------------------------------------------------------------------
# Résultat de simulation
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """Métriques retournées après une simulation complète."""

    # ── Paramètres de la simulation ──────────────────────────────────────
    hands_played:     int
    strategy_mode:    str
    decks:            int
    penetration:      float

    # ── Métriques financières ─────────────────────────────────────────────
    total_profit:     float   # profit net total (peut être négatif)
    total_wagered:    float   # total des mises placées
    ev_per_hand:      float   # profit moyen par main
    ev_per_100_hands: float   # profit pour 100 mains jouées
    ev_percent:       float   # EV% = total_profit / total_wagered × 100
    average_bet:      float   # mise moyenne (total_wagered / hands_played)
    final_bankroll:   float
    max_bankroll:     float
    min_bankroll:     float

    # ── Résultats des mains ───────────────────────────────────────────────
    wins:       int
    losses:     int
    pushes:     int
    blackjacks: int   # BJ joueur (pait 3:2)
    surrenders: int
    busts:      int   # joueur bust

    # ── Statistiques de comptage ──────────────────────────────────────────
    positive_tc_hands: int
    positive_tc_ratio: float   # positive_tc_hands / hands_played

    # ── Dispersion ────────────────────────────────────────────────────────
    profit_std:        float   # écart-type du profit par main (en €)
    profit_std_units:  float   # écart-type normalisé par unit_size

    # ── Historique bankroll (optionnel) ───────────────────────────────────
    bankroll_history:  list    = field(default_factory=list)  # [(round_index, bankroll), ...]

    def summary(self) -> str:
        """Résumé lisible en une page."""
        sep = "-" * 52
        lines = [
            sep,
            f"  Blackjack Trainer - Simulation Results",
            sep,
            f"  Hands played      : {self.hands_played:>12,}",
            f"  Strategy          : {self.strategy_mode}",
            f"  Decks / Pen.      : {self.decks} / {self.penetration:.0%}",
            sep,
            f"  Total wagered     : {self.total_wagered:>12,.2f} €",
            f"  Total profit      : {self.total_profit:>+12,.2f} €",
            f"  EV per hand       : {self.ev_per_hand:>+12,.4f} €",
            f"  EV per 100 hands  : {self.ev_per_100_hands:>+12,.2f} €",
            f"  EV %              : {self.ev_percent:>+11.4f} %",
            f"  Average bet       : {self.average_bet:>12,.2f} €",
            f"  Profit std / hand : {self.profit_std:>12,.2f} €",
            sep,
            f"  Wins              : {self.wins:>12,}  ({self.wins/self.hands_played:.1%})",
            f"  Losses            : {self.losses:>12,}  ({self.losses/self.hands_played:.1%})",
            f"  Pushes            : {self.pushes:>12,}  ({self.pushes/self.hands_played:.1%})",
            f"  Blackjacks        : {self.blackjacks:>12,}  ({self.blackjacks/self.hands_played:.2%})",
            f"  Surrenders        : {self.surrenders:>12,}",
            f"  Player busts      : {self.busts:>12,}",
            sep,
            f"  Positive-TC hands : {self.positive_tc_hands:>12,}  ({self.positive_tc_ratio:.1%})",
            f"  Final bankroll    : {self.final_bankroll:>12,.2f} €",
            f"  Peak  bankroll    : {self.max_bankroll:>12,.2f} €",
            f"  Low   bankroll    : {self.min_bankroll:>12,.2f} €",
            sep,
        ]
        return "\n".join(lines)
