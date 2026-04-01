"""
app_simulation.py - Blackjack EV Lab
Deux pages accessibles depuis la sidebar :
  • Monte Carlo Simulator - EV, variance, historique bankroll, analyse par TC
  • EV Playground        - EV par action pour une main précise à un TC cible

Lancement : streamlit run app_simulation.py
"""

from __future__ import annotations

import os
import sys
import random
import time
from collections import Counter

try:
    from dotenv import load_dotenv
    load_dotenv()  # charge .env à la racine si présent
except ImportError:
    pass  # python-dotenv optionnel, fallback sur les vars d'environnement système

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation.simulator import simulate
from simulation.config import BettingConfig, SimConfig, TableRules
from simulation.engine import Card, Hand
from simulation.strategy import get_basic_strategy
from simulation.deviations import get_deviation


# ═══════════════════════════════════════════════════════════════
# Helpers graphes - thème sombre partagé entre les deux pages
# ═══════════════════════════════════════════════════════════════

_BG   = '#1a1a2e'   # fond figure + axes
_GRID = '#2a2a3e'   # couleur grille et bordures
_TEXT = '#e0e0e0'   # textes et labels


def _dark_fig(w: float = 10, h: float = 4):
    """Retourne (fig, ax) avec thème sombre cohérent."""
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    for sp in ax.spines.values():
        sp.set_color(_GRID)
    ax.tick_params(colors=_TEXT, labelsize=9)
    ax.xaxis.label.set_color(_TEXT)
    ax.yaxis.label.set_color(_TEXT)
    ax.title.set_color(_TEXT)
    ax.grid(color=_GRID, linestyle=':', linewidth=0.7)
    return fig, ax


def _eur(x, _=None) -> str:
    """Formateur matplotlib : montant en € avec séparateur milliers."""
    return f"{x:,.0f} €"


# ═══════════════════════════════════════════════════════════════
# Page config
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Blackjack EV Lab",
    page_icon="🃏",
    layout="wide",
)

# URL du jeu React - configurable via .env (STREAMLIT_GAME_URL)
_GAME_URL = os.getenv("STREAMLIT_GAME_URL", "http://localhost:5173")

# ── Sidebar : navigation + lien vers le jeu ───────────────────
_PAGES = ["📊 Monte Carlo Simulator", "🔬 EV Playground"]
if "page" not in st.session_state:
    st.session_state.page = _PAGES[0]

with st.sidebar:
    st.markdown("## 🃏 Blackjack EV Lab")
    st.divider()
    for _p in _PAGES:
        _active = st.session_state.page == _p
        if st.button(
            _p,
            use_container_width=True,
            type="primary" if _active else "secondary",
            key=f"nav_{_p}",
        ):
            st.session_state.page = _p
            st.rerun()
    st.divider()
    st.markdown(
        """
        <style>
        .open-game-btn a {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            width: 100%;
            padding: 0.25rem 0.75rem;
            min-height: 38px;
            box-sizing: border-box;
            background: transparent;
            border: 1px solid rgba(250, 250, 250, 0.2);
            border-radius: 0.5rem;
            color: rgb(250, 250, 250);
            font-size: 0.875rem;
            font-weight: 400;
            text-decoration: none;
            cursor: pointer;
            transition: border-color 150ms, background 150ms;
            font-family: "Source Sans Pro", sans-serif;
        }
        .open-game-btn a:hover {
            border-color: rgba(250, 250, 250, 0.6);
            background: rgba(250, 250, 250, 0.05);
            color: rgb(250, 250, 250);
            text-decoration: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="open-game-btn"><a href="{_GAME_URL}" target="_blank">🃏 Open Game</a></div>',
        unsafe_allow_html=True,
    )

page = st.session_state.page


# ═══════════════════════════════════════════════════════════════
# ── PAGE 1 : Monte Carlo Simulator ───────────────────────────
# ═══════════════════════════════════════════════════════════════
if page == "📊 Monte Carlo Simulator":

    st.title("📊 Monte Carlo Simulator")
    st.caption("Long-run simulation - configurable strategy, Hi-Lo bet spread")
    st.divider()

    # ── Parameters ───────────────────────────────────────────
    col_p1, col_p2, col_p3 = st.columns(3)

    with col_p1:
        st.subheader("Simulation")
        hands = st.number_input(
            "Hands (rounds)", min_value=1_000, max_value=10_000_000,
            value=500_000, step=100_000,
        )
        spread = st.selectbox(
            "Bet spread",
            ["1-1","1-2","1-4","1-6","1-8","1-10","1-12"],
            index=0,
            help="MIN–MAX in units. 1-1 = flat bet."
        )
        unit_size = st.number_input(
            "Unit size (€)", min_value=1., max_value=10_000., value=10., step=5.
        )
        bankroll = st.number_input(
            "Initial bankroll (€)", min_value=100., max_value=1e8,
            value=1_000_000., step=10_000.
        )
        use_seed = st.checkbox("Fix random seed", value=False)
        seed = None
        if use_seed:
            seed = st.number_input("Seed", min_value=0, max_value=999_999, value=42, step=1)

    with col_p2:
        st.subheader("Table Rules")
        decks       = st.selectbox("Number of decks", [1,2,4,6,8], index=3)
        _pen_pct    = st.slider("Penetration", 50, 95, 75, 5, format="%d%%")
        penetration = _pen_pct / 100
        dealer_h17  = st.checkbox("Dealer hits soft 17 (H17)", value=False)
        das_sim     = st.checkbox("Double after split (DAS)", value=True)
        surrender_sim = st.checkbox("Late surrender", value=True)

    with col_p3:
        st.subheader("Options")
        max_split   = st.selectbox("Max split hands", [2,3,4], index=2)
        bj_payout_s = st.selectbox(
            "Blackjack payout", ["3:2 (1.5)","6:5 (1.2)"], index=0
        )
        bj_payout_v = 1.5 if bj_payout_s.startswith("3") else 1.2
        st.markdown("**Strategy**")
        _strategy_mode = st.radio(
            "Strategy",
            ["Basic Strategy", "Advanced (Basic + I18 Deviations)"],
            index=0,
            label_visibility="collapsed",
            help=(
                "**Basic Strategy**: pure table-based optimal play, ignores count.\n\n"
                "**Advanced**: applies Illustrious 18 index plays when the True Count justifies it "
                "(deviations override basic strategy)."
            ),
        )
        use_deviations_sim = _strategy_mode.startswith("Advanced")
        st.markdown("")
        run_variance = st.checkbox(
            "Run variance analysis (5 seeds)",
            value=False,
            help=(
                "Runs the simulation 5 times with different random seeds "
                "to visualize long-run variance. Takes ~5× longer."
            ),
        )
        st.markdown("")
        run_btn_sim = st.button(
            "▶ Run Simulation", type="primary", use_container_width=True
        )

    st.divider()

    # ── Results ───────────────────────────────────────────────
    if not run_btn_sim:
        st.info("Configure the parameters above, then click **▶ Run Simulation**.")
    else:
        try:
            cfg = SimConfig(
                hands            = int(hands),
                decks            = decks,
                penetration      = penetration,
                betting          = BettingConfig.from_string(spread, unit_size=float(unit_size)),
                rules            = TableRules(
                    dealer_hits_soft_17 = dealer_h17,
                    double_after_split  = das_sim,
                    surrender_allowed   = surrender_sim,
                    max_split_hands     = max_split,
                    blackjack_payout    = bj_payout_v,
                ),
                initial_bankroll     = float(bankroll),
                seed                 = int(seed) if seed is not None else None,
                use_deviations       = use_deviations_sim,
                track_history        = True,
                history_interval     = max(1, int(hands) // 2000),
                track_hand_outcomes  = True,
            )
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            st.stop()

        with st.spinner(f"Simulating {hands:,} hands…"):
            t0 = time.perf_counter()
            r  = simulate(cfg)
            elapsed = time.perf_counter() - t0

        st.success(f"✅ Done in {elapsed:.1f}s - {r.hands_played:,} rounds played.")

        # ── Section 1 : Key Metrics ────────────────────────────────────────
        st.subheader("📋 Key Metrics")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("EV %",           f"{r.ev_percent:+.4f}%")
        c2.metric("EV / hand",      f"{r.ev_per_hand:+.4f} €")
        c3.metric("EV / 100 hands", f"{r.ev_per_100_hands:+.2f} €")
        c4.metric("Total profit",   f"{r.total_profit:+,.0f} €")
        c5.metric("Total wagered",  f"{r.total_wagered:,.0f} €")
        b1,b2,b3,b4,b5 = st.columns(5)
        b1.metric("Final bankroll", f"{r.final_bankroll:,.0f} €",
                  delta=f"{r.final_bankroll-bankroll:+,.0f} €")
        b2.metric("Peak bankroll",  f"{r.max_bankroll:,.0f} €")
        b3.metric("Low bankroll",   f"{r.min_bankroll:,.0f} €")
        b4.metric("Average bet",    f"{r.average_bet:.2f} €")
        b5.metric("Std dev / hand", f"{r.profit_std:.3f} €",
                  delta=f"+TC ratio: {r.positive_tc_ratio:.1%}")

        # ── Section 2 : Bankroll Progression ──────────────────────────────
        st.subheader("📈 Bankroll Progression")
        if r.bankroll_history:
            xs = [h[0] for h in r.bankroll_history]
            ys = [h[1] for h in r.bankroll_history]
            fig, ax = _dark_fig(10, 4)
            ax.plot(xs, ys, color='#4a9eff', linewidth=1.2, zorder=3)
            # Zone colorée au-dessus/dessous de la bankroll initiale
            ax.fill_between(xs, ys, bankroll,
                            where=[y >= bankroll for y in ys],
                            color='#22c55e', alpha=0.15, interpolate=True)
            ax.fill_between(xs, ys, bankroll,
                            where=[y < bankroll for y in ys],
                            color='#ef4444', alpha=0.15, interpolate=True)
            # Lignes horizontales
            ax.axhline(bankroll,         color='#6b7280', linestyle='--', linewidth=1,
                       label=f"Initial  {bankroll:,.0f} €")
            fin_col = '#22c55e' if r.final_bankroll >= bankroll else '#ef4444'
            ax.axhline(r.final_bankroll, color=fin_col, linestyle=':', linewidth=1,
                       label=f"Final  {r.final_bankroll:,.0f} €")
            # Annotations peak / low
            peak_idx = int(np.argmax(ys)); low_idx = int(np.argmin(ys))
            ax.scatter([xs[peak_idx]], [ys[peak_idx]], color='#22c55e', s=40, zorder=5)
            ax.scatter([xs[low_idx]],  [ys[low_idx]],  color='#ef4444', s=40, zorder=5)
            ax.annotate(f"Peak\n{ys[peak_idx]:,.0f} €",
                        (xs[peak_idx], ys[peak_idx]), textcoords="offset points",
                        xytext=(0, 10), ha='center', fontsize=8, color='#22c55e')
            ax.annotate(f"Low\n{ys[low_idx]:,.0f} €",
                        (xs[low_idx], ys[low_idx]), textcoords="offset points",
                        xytext=(0, -18), ha='center', fontsize=8, color='#ef4444')
            ax.set_title(f"Bankroll progression over {r.hands_played:,} hands", fontweight='bold', fontsize=11)
            ax.set_xlabel("Hand #", color=_TEXT)
            ax.set_ylabel("Bankroll (€)", color=_TEXT)
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(_eur))
            ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x):,}"))
            leg = ax.legend(fontsize=8, facecolor=_BG, edgecolor=_GRID, labelcolor=_TEXT)
            plt.tight_layout(); st.pyplot(fig); plt.close(fig)
        else:
            st.info("Enable track_history to see bankroll progression.")

        # ── Section 3 : True Count Analysis ───────────────────────────────
        with st.expander("📊 True Count Analysis", expanded=True):
            buckets = r.tc_bucket_ev
            labels, ev_vals, counts = [], [], []
            for k in range(-3, 6):
                cnt = buckets[k]['count'] if k in buckets else 0
                profit = buckets[k]['profit'] if k in buckets else 0.0
                lbl = f"TC {'+' if k > 0 else ''}{k}" if k < 5 else "TC +5+"
                labels.append(lbl)
                ev_vals.append((profit / cnt) if cnt > 0 else 0.0)
                counts.append(cnt)
            colors = ['#ef4444' if v < 0 else '#22c55e' for v in ev_vals]
            fig, ax = _dark_fig(9, 4)
            bars = ax.barh(labels, ev_vals, color=colors, edgecolor='none', height=0.55)
            ax.axvline(0, color=_TEXT, linewidth=0.8)
            # Labels count à droite
            x_max = max(abs(v) for v in ev_vals) if ev_vals else 1
            for i, (bar, cnt) in enumerate(zip(bars, counts)):
                xpos = bar.get_width()
                ha = 'left' if xpos >= 0 else 'right'
                offset = x_max * 0.03 if xpos >= 0 else -x_max * 0.03
                ax.text(xpos + offset, bar.get_y() + bar.get_height()/2,
                        f"{cnt:,} hands", va='center', ha=ha, fontsize=7.5, color=_TEXT, alpha=0.7)
            ax.set_title("EV per hand by True Count bucket", fontweight='bold', fontsize=11)
            ax.set_xlabel("Average profit per hand (€)", color=_TEXT)
            ax.xaxis.set_major_formatter(mticker.FuncFormatter(_eur))
            plt.tight_layout(); st.pyplot(fig); plt.close(fig)

        # ── Section 4 : Hand Distribution ─────────────────────────────────
        with st.expander("📉 Hand Outcome Distribution", expanded=False):
            if r.hand_outcomes:
                outcomes = np.array(r.hand_outcomes, dtype=np.float32)
                ev_mean = float(np.mean(outcomes))
                fig, ax = _dark_fig(10, 4)
                # Histogramme avec couleurs séparées perte/gain
                max_abs = float(np.percentile(np.abs(outcomes), 99.5))
                bins = np.linspace(-max_abs, max_abs, 80)
                neg_mask = outcomes < 0; pos_mask = outcomes > 0; zero_mask = outcomes == 0
                ax.hist(outcomes[neg_mask], bins=bins, color='#ef4444', alpha=0.75,
                        label='Loss', edgecolor='none')
                ax.hist(outcomes[pos_mask], bins=bins, color='#22c55e', alpha=0.75,
                        label='Win', edgecolor='none')
                ax.hist(outcomes[zero_mask], bins=3, color='#6b7280', alpha=0.6,
                        label='Push', edgecolor='none')
                ax.axvline(ev_mean, color='#f0c040', linewidth=1.5, linestyle='--',
                           label=f"EV mean: {ev_mean:+.3f} €")
                ax.set_title("Distribution of hand outcomes", fontweight='bold', fontsize=11)
                ax.set_xlabel("Net profit per hand (€)", color=_TEXT)
                ax.set_ylabel("Frequency", color=_TEXT)
                ax.xaxis.set_major_formatter(mticker.FuncFormatter(_eur))
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x):,}"))
                leg = ax.legend(fontsize=8, facecolor=_BG, edgecolor=_GRID, labelcolor=_TEXT)
                plt.tight_layout(); st.pyplot(fig); plt.close(fig)
            else:
                st.info("Hand outcomes not tracked.")

        # ── Section 5 : Variance Analysis (multi-seed) ────────────────────
        if run_variance:
            st.subheader("🎲 Variance Analysis - 5 Simulations")
            SEEDS_VAR = [42, 123, 456, 789, 1337]
            COLORS_VAR = ['#4a9eff','#f0c040','#a78bfa','#34d399','#fb923c']
            variance_results = []
            prog_bar  = st.progress(0)
            prog_text = st.empty()
            for i, s in enumerate(SEEDS_VAR):
                prog_text.text(f"Running simulation {i+1}/5 (seed {s})…")
                vcfg = SimConfig(
                    hands            = int(hands),
                    decks            = decks,
                    penetration      = penetration,
                    betting          = BettingConfig.from_string(spread, unit_size=float(unit_size)),
                    rules            = TableRules(
                        dealer_hits_soft_17 = dealer_h17,
                        double_after_split  = das_sim,
                        surrender_allowed   = surrender_sim,
                        max_split_hands     = max_split,
                        blackjack_payout    = bj_payout_v,
                    ),
                    initial_bankroll = float(bankroll),
                    seed             = s,
                    use_deviations   = use_deviations_sim,
                    track_history    = True,
                    history_interval = max(1, int(hands) // 2000),
                )
                vr = simulate(vcfg)
                variance_results.append(vr)
                prog_bar.progress((i + 1) / 5)
            prog_text.empty(); prog_bar.empty()

            fig, ax = _dark_fig(10, 5)
            all_ys = []
            for i, (vr, s) in enumerate(zip(variance_results, SEEDS_VAR)):
                if vr.bankroll_history:
                    vxs = [h[0] for h in vr.bankroll_history]
                    vys = [h[1] for h in vr.bankroll_history]
                    ax.plot(vxs, vys, color=COLORS_VAR[i], linewidth=1,
                            label=f"Seed {s}  ({vr.final_bankroll:+,.0f} €)", alpha=0.85)
                    all_ys.append(vys)
            ax.axhline(bankroll, color='#6b7280', linestyle='--', linewidth=1,
                       label=f"Initial  {bankroll:,.0f} €")
            # Zone de confiance min/max
            if all_ys:
                min_len = min(len(y) for y in all_ys)
                arr = np.array([y[:min_len] for y in all_ys])
                xs_var = [vr.bankroll_history[j][0] for j in range(min_len)] \
                         if variance_results[0].bankroll_history else list(range(min_len))
                ax.fill_between(xs_var, arr.min(axis=0), arr.max(axis=0),
                                color='#ffffff', alpha=0.07, label="Min–Max range")
            ax.set_title(
                f"Bankroll variance across 5 simulations - {int(hands):,} hands each",
                fontweight='bold', fontsize=11)
            ax.set_xlabel("Hand #", color=_TEXT)
            ax.set_ylabel("Bankroll (€)", color=_TEXT)
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(_eur))
            ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x):,}"))
            leg = ax.legend(fontsize=8, facecolor=_BG, edgecolor=_GRID, labelcolor=_TEXT, ncol=2)
            plt.tight_layout(); st.pyplot(fig); plt.close(fig)

            # Mini-tableau de synthèse
            var_rows = []
            for vr, s in zip(variance_results, SEEDS_VAR):
                var_rows.append({
                    "Seed": s,
                    "Final bankroll": f"{vr.final_bankroll:,.0f} €",
                    "Peak":           f"{vr.max_bankroll:,.0f} €",
                    "Low":            f"{vr.min_bankroll:,.0f} €",
                    "Net P&L":        f"{vr.total_profit:+,.0f} €",
                })
            avg_final = np.mean([vr.final_bankroll for vr in variance_results])
            avg_peak  = np.mean([vr.max_bankroll   for vr in variance_results])
            avg_low   = np.mean([vr.min_bankroll   for vr in variance_results])
            avg_pnl   = np.mean([vr.total_profit   for vr in variance_results])
            var_rows.append({
                "Seed": "**Average**",
                "Final bankroll": f"**{avg_final:,.0f} €**",
                "Peak":           f"**{avg_peak:,.0f} €**",
                "Low":            f"**{avg_low:,.0f} €**",
                "Net P&L":        f"**{avg_pnl:+,.0f} €**",
            })
            st.dataframe(pd.DataFrame(var_rows), use_container_width=True, hide_index=True)

        # ── Section 6 : Hand Breakdown ─────────────────────────────────────
        with st.expander("🃏 Hand Breakdown", expanded=False):
            st.dataframe(pd.DataFrame({
                "Outcome":     ["Wins","Losses","Pushes","Blackjacks","Surrenders","Player busts"],
                "Count":       [r.wins, r.losses, r.pushes, r.blackjacks, r.surrenders, r.busts],
                "% of rounds": [f"{v/r.hands_played:.2%}" for v in
                                [r.wins, r.losses, r.pushes, r.blackjacks, r.surrenders, r.busts]],
            }), use_container_width=True, hide_index=True)

        # ── Section 7 : Config Recap ───────────────────────────────────────
        with st.expander("⚙ Simulation config recap", expanded=False):
            st.code(
                f"Hands:     {r.hands_played:,}\n"
                f"Decks:     {decks}  |  Penetration: {penetration:.0%}\n"
                f"Spread:    {spread}  |  Unit: {unit_size} €  |  BJ payout: {bj_payout_s}\n"
                f"Rules:     {'H17' if dealer_h17 else 'S17'}, "
                f"{'DAS' if das_sim else 'no DAS'}, "
                f"{'Surrender' if surrender_sim else 'no Surrender'}, "
                f"max {max_split} split hands\n"
                f"Strategy:  {'Basic + I18 Deviations' if use_deviations_sim else 'Basic Strategy'}\n"
                f"Seed:      {seed if seed is not None else 'random'}\n"
                f"Elapsed:   {elapsed:.2f}s",
                language=None,
            )


# ═══════════════════════════════════════════════════════════════
# ── PAGE 2 : EV Playground ───────────────────────────────────
# ═══════════════════════════════════════════════════════════════
else:

    # ── Pure helpers (scoped here) ────────────────────────────
    ALL_RANKS  = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
    LOW_RANKS  = {'2','3','4','5','6'}
    MID_RANKS  = {'7','8','9'}
    RANK_VAL   = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
                  '10':10,'J':10,'Q':10,'K':10,'A':11}
    ACTION_LABEL = {
        'H':'Hit','S':'Stand','D':'Double','Ds':'Double/Stand',
        'Y':'Split','Y/N':'Split (DAS)','SUR':'Surrender','INS':'Insurance',
    }
    PRESETS = {
        "Manuel": None,
        "16 vs 10  (I18 classique)": (['10','6'], '10'),
        "15 vs 10  (I18 TC≥4)":      (['10','5'], '10'),
        "11 vs As  (I18 TC≥1)":      (['6','5'],  'A'),
        "8,8 vs Dame":                (['8','8'],  'Q'),
        "9,9 vs 9":                   (['9','9'],  '9'),
        "12 vs 3  (I18 TC≥2)":       (['7','5'],  '3'),
        "13 vs 2  (I18 TC<-1)":      (['7','6'],  '2'),
        "Hard 10 vs 10":              (['6','4'],  '10'),
        "A,7 soft 18 vs 9":          (['A','7'],  '9'),
        "14 vs 10  (I18 TC≥3)":      (['7','7'],  '10'),
    }

    def _hilo(r): return 1 if r in LOW_RANKS else (0 if r in MID_RANKS else -1)

    def _hand_value(ranks):
        v = sum(RANK_VAL[r] for r in ranks); a = ranks.count('A')
        while v > 21 and a > 0: v -= 10; a -= 1
        return v

    def _is_soft(ranks):
        v = sum(RANK_VAL[r] for r in ranks); a = ranks.count('A')
        while v > 21 and a > 0: v -= 10; a -= 1
        return a > 0 and v <= 21

    def _is_pair(ranks):
        return len(ranks) == 2 and RANK_VAL[ranks[0]] == RANK_VAL[ranks[1]]

    def _mc(r): return Card(r, '♠')

    def _mh(ranks, split=False):
        h = Hand(is_split_hand=split)
        for r in ranks: h.add_card(_mc(r))
        return h

    def _build_shoe(player_ranks, upcard, target_tc, num_decks=6):
        counts = Counter({r: num_decks * 4 for r in ALL_RANKS})
        for r in player_ranks + [upcard]:
            if counts[r] > 0: counts[r] -= 1
        n_rem = sum(counts.values()); decks_rem = n_rem / 52.0
        target_rc  = -round(target_tc * decks_rem)
        current_rc = sum(_hilo(r) * counts[r] for r in ALL_RANKS)
        delta = target_rc - current_rc
        if delta > 0:
            for r in ['10','J','Q','K','A']:
                while delta > 0 and counts[r] > 0: counts[r] -= 1; delta -= 1
        elif delta < 0:
            for r in ['2','3','4','5','6']:
                while delta < 0 and counts[r] > 0: counts[r] -= 1; delta += 1
        shoe = [r for r in ALL_RANKS for _ in range(counts[r])]
        random.shuffle(shoe); return shoe

    def _run_dealer(hand, draw, hits_s17):
        h = list(hand)
        while True:
            v = _hand_value(h); s = _is_soft(h)
            if v > 21 or v > 17: break
            if v == 17 and not (s and hits_s17): break
            c = draw()
            if c is None: break
            h.append(c)
        return h

    def _outcome(player, dealer, bet_mult=1.0, is_split=False, bj_pay=1.5):
        pv = _hand_value(player); dv = _hand_value(dealer)
        p_bj = len(player)==2 and pv==21 and not is_split
        d_bj = len(dealer)==2 and dv==21
        if pv > 21:             return -bet_mult
        if p_bj and not d_bj:  return  bj_pay * bet_mult
        if d_bj and not p_bj:  return -bet_mult
        if p_bj and d_bj:      return  0.0
        if dv > 21 or pv > dv: return  bet_mult
        if pv < dv:            return -bet_mult
        return 0.0

    def _play_basic(hand, upcard, draw, das, is_split=False):
        h = list(hand); bet_mult = 1.0
        while True:
            v = _hand_value(h)
            if v > 21 or v == 21: break
            bs = get_basic_strategy(_mh(h, is_split), _mc(upcard))
            if bs in ('S','SUR'): break
            elif bs == 'H':
                c = draw()
                if c: h.append(c)
            elif bs in ('D','Ds'):
                can_dbl = (len(h)==2) and (not is_split or das)
                if can_dbl:
                    c = draw()
                    if c: h.append(c)
                    bet_mult = 2.0; break
                elif bs == 'D':
                    c = draw()
                    if c: h.append(c)
                else: break
            else: break
        return h, bet_mult

    def _simulate_ev(player_ranks, upcard, action, target_tc, rules, n_sims=100_000):
        hits_s17 = rules.get('hits_soft_17', False)
        das      = rules.get('das', True)
        bj_pay   = rules.get('bj_payout', 1.5)
        ndeck    = rules.get('num_decks', 6)
        results  = []
        for _ in range(n_sims):
            shoe = _build_shoe(player_ranks, upcard, target_tc, ndeck)
            idx  = 0
            def draw():
                nonlocal idx
                if idx >= len(shoe): return None
                c = shoe[idx]; idx += 1; return c
            hole = draw()
            if hole is None: continue
            d_init = [hole, upcard]; d_bj = (_hand_value(d_init)==21)
            if action == 'INS':
                # Insurance paie 2:1 sur la mise d'assurance (= moitié de la mise principale)
                # EV normalisé à la mise principale : +0.5 si dealer BJ, -0.5 si non
                results.append(0.5 if d_bj else -0.5); continue
            if action == 'SUR':
                results.append(-1.0 if d_bj else -0.5); continue
            if d_bj:
                pv = _hand_value(player_ranks)
                results.append(0.0 if (len(player_ranks)==2 and pv==21) else -1.0); continue
            if action == 'S':
                results.append(_outcome(player_ranks, _run_dealer(d_init, draw, hits_s17), bj_pay=bj_pay))
            elif action == 'H':
                h = list(player_ranks) + [draw()]
                h, _ = _play_basic(h, upcard, draw, das)
                results.append(_outcome(h, _run_dealer(d_init, draw, hits_s17), bj_pay=bj_pay))
            elif action == 'D':
                h = list(player_ranks) + [draw()]
                results.append(_outcome(h, _run_dealer(d_init, draw, hits_s17), 2.0, bj_pay=bj_pay))
            elif action in ('Y','Y/N'):
                h1 = [player_ranks[0], draw()]; h2 = [player_ranks[1], draw()]
                h1, bm1 = _play_basic(h1, upcard, draw, das, True)
                h2, bm2 = _play_basic(h2, upcard, draw, das, True)
                df = _run_dealer(d_init, draw, hits_s17)
                results.append(_outcome(h1,df,bm1,True,bj_pay) + _outcome(h2,df,bm2,True,bj_pay))
        if not results: return {'ev':0.,'std_err':0.,'n':0,'action':action}
        arr = np.array(results)
        return {'ev':float(np.mean(arr)), 'std_err':float(np.std(arr,ddof=1)/np.sqrt(len(arr))),
                'n':len(arr), 'action':action}

    def _available_actions(player_ranks, upcard, rules):
        acts = ['H','S']
        if len(player_ranks) == 2:
            acts.append('D')
            if rules.get('surrender_allowed', True): acts.append('SUR')
            if _is_pair(player_ranks): acts.append('Y')
        # Insurance disponible uniquement si la première carte du dealer est un As
        if upcard == 'A':
            acts.append('INS')
        return acts

    # ── CSS : boutons-cartes ──────────────────────────────────
    st.markdown("""<style>
[data-testid="stMain"] button[data-testid="baseButton-secondary"] {
    background: white !important;
    color: #111827 !important;
    border: 2px solid #d1d5db !important;
    border-radius: 12px !important;
    font-size: 1.45rem !important;
    font-weight: 900 !important;
    min-height: 74px !important;
    letter-spacing: .02em !important;
    box-shadow: 2px 3px 8px rgba(0,0,0,.15) !important;
    transition: border-color .12s, box-shadow .12s, transform .12s !important;
}
[data-testid="stMain"] button[data-testid="baseButton-secondary"]:hover {
    border-color: #60a5fa !important;
    background: #f0f9ff !important;
    box-shadow: 2px 5px 14px rgba(0,0,0,.22) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stMain"] button[data-testid="baseButton-primary"]:not([aria-label*="Lancer"]):not([aria-label*="nav"]) {
    border-radius: 12px !important;
    font-size: 1.45rem !important;
    font-weight: 900 !important;
    min-height: 74px !important;
}
</style>""", unsafe_allow_html=True)

    # ── UI ───────────────────────────────────────────────────
    st.title("🔬 EV Playground")
    st.caption(
        "Simule l'EV de chaque action pour une main précise vs dealer à TC donné. "
        "Monte Carlo avec sabot biaisé selon le True Count cible."
    )
    st.divider()

    # ── Helpers ───────────────────────────────────────────────
    _CSUITS = {
        'A':'♠','K':'♣','Q':'♥','J':'♦','10':'♠',
        '9':'♣','8':'♠','7':'♦','6':'♣','5':'♥',
        '4':'♦','3':'♣','2':'♠',
    }

    # ── Session state : cartes sélectionnées ─────────────────
    if "pg_cards" not in st.session_state:
        st.session_state.pg_cards     = ['8', '8']
        st.session_state.pg_upcard_r  = 'Q'
        st.session_state.pg_edit_slot = None

    # Paramètres en haut de page, 3 colonnes
    cfg_c1, cfg_c2, cfg_c3 = st.columns([1.2, 1, 1])

    with cfg_c1:
        st.subheader("Hand")

        # Nombre de cartes
        n_cards = int(st.number_input(
            "Number of cards", 2, 5,
            len(st.session_state.pg_cards), key="pg_nc",
        ))
        while len(st.session_state.pg_cards) < n_cards:
            st.session_state.pg_cards.append('2')
        if len(st.session_state.pg_cards) > n_cards:
            st.session_state.pg_cards = st.session_state.pg_cards[:n_cards]
            _s0 = st.session_state.pg_edit_slot
            if _s0 and _s0.startswith("p") and int(_s0[1:]) >= n_cards:
                st.session_state.pg_edit_slot = None

        # ── Cartes joueur - clic pour modifier ────────────
        st.markdown("**Your hand** *(click a card to change it)*")
        _hcols = st.columns(n_cards)
        for _i, _r in enumerate(st.session_state.pg_cards):
            _s = f"p{_i}"
            _active = st.session_state.pg_edit_slot == _s
            if _hcols[_i].button(
                f"{_r} {_CSUITS.get(_r,'♠')}",
                key=f"pg_card_{_i}",
                use_container_width=True,
                type="primary" if _active else "secondary",
            ):
                st.session_state.pg_edit_slot = None if _active else _s
                st.rerun()

        # ── Carte dealer ───────────────────────────────────
        st.markdown("**vs Dealer** *(click to change)*")
        _ded = st.session_state.pg_edit_slot == "dealer"
        if st.button(
            f"{st.session_state.pg_upcard_r} {_CSUITS.get(st.session_state.pg_upcard_r,'♠')}",
            key="pg_card_dealer",
            use_container_width=True,
            type="primary" if _ded else "secondary",
        ):
            st.session_state.pg_edit_slot = None if _ded else "dealer"
            st.rerun()

    with cfg_c2:
        st.subheader("Count & Rules")
        target_tc_pg = st.slider("True Count", -5.0, 8.0, 0.0, 0.5, key="pg_tc")
        rc1, rc2 = st.columns(2)
        pg_decks = rc1.selectbox("Decks", [1,2,6,8], index=2, key="pg_decks")
        pg_h17   = rc2.checkbox("Dealer H17", value=False, key="pg_h17")
        pg_sur   = rc1.checkbox("Surrender",  value=True,  key="pg_sur")
        pg_das   = rc2.checkbox("DAS",        value=True,  key="pg_das")
        pg_bj    = st.radio("BJ payout", [1.5, 1.2], horizontal=True, key="pg_bj",
                            format_func=lambda x: "3:2" if x==1.5 else "6:5")

    with cfg_c3:
        st.subheader("Simulation")
        pg_nsims = st.select_slider(
            "Simulations",
            options=[10_000, 50_000, 100_000, 200_000, 500_000],
            value=100_000, key="pg_nsims",
            format_func=lambda x: f"{x:,}",
        )
        pg_scan = st.checkbox("Scan TC (−4 → +8)", value=False, key="pg_scan",
                              help="Compute EV for every action across the full TC range")
        st.markdown("")
        run_pg = st.button("▶ Run", type="primary", use_container_width=True, key="pg_run")

    # ── Card picker (pleine largeur, sous les colonnes) ──────────
    _edit_slot = st.session_state.get("pg_edit_slot")
    if _edit_slot:
        _slot_lbl = (
            f"Card {int(_edit_slot[1:])+1}" if _edit_slot.startswith("p") else "Dealer"
        )
        _cur_rank = (
            st.session_state.pg_cards[int(_edit_slot[1:])]
            if _edit_slot.startswith("p")
            else st.session_state.pg_upcard_r
        )
        st.markdown(
            f'<p style="margin:6px 0 4px;font-weight:600;font-size:.95rem">'
            f'🃏 Pick card - <em>{_slot_lbl}</em></p>',
            unsafe_allow_html=True,
        )
        _pcols = st.columns(13)
        for _pi, _pr in enumerate(ALL_RANKS):
            _psuit  = _CSUITS.get(_pr, '♠')
            _is_sel = _pr == _cur_rank
            with _pcols[_pi]:
                if st.button(
                    f"{_pr} {_psuit}",
                    key=f"pick_{_edit_slot}_{_pr}",
                    use_container_width=True,
                    type="primary" if _is_sel else "secondary",
                ):
                    if _edit_slot.startswith("p"):
                        st.session_state.pg_cards[int(_edit_slot[1:])] = _pr
                    else:
                        st.session_state.pg_upcard_r = _pr
                    st.session_state.pg_edit_slot = None
                    st.rerun()

    st.divider()

    # Résoudre les variables depuis le session state
    player_ranks_pg: list[str] = st.session_state.pg_cards
    upcard_pg: str = st.session_state.pg_upcard_r

    pg_rules = {'num_decks':pg_decks,'hits_soft_17':pg_h17,
                'surrender_allowed':pg_sur,'das':pg_das,'bj_payout':pg_bj}

    # Résumé + recommandations stratégie
    pv_pg    = _hand_value(player_ranks_pg)
    psoft_pg = " (soft)" if _is_soft(player_ranks_pg) else ""
    ppair_pg = " · pair" if _is_pair(player_ranks_pg) else ""

    st.subheader(
        f"{' + '.join(player_ranks_pg)} = **{pv_pg}{psoft_pg}**{ppair_pg}"
        f"   vs   **{upcard_pg}**   ·   TC **{target_tc_pg:+.1f}**"
    )

    h_pg  = _mh(player_ranks_pg)
    u_pg  = _mc(upcard_pg)
    bs_pg = get_basic_strategy(h_pg, u_pg)
    dv_pg = get_deviation(h_pg, u_pg, target_tc_pg)
    rec_pg = dv_pg if dv_pg else bs_pg

    m1, m2, m3 = st.columns(3)
    m1.metric("Basic Strategy", ACTION_LABEL.get(bs_pg, bs_pg))
    m2.metric("I18 Deviation",
              f"★ {ACTION_LABEL.get(dv_pg,dv_pg)}" if dv_pg and dv_pg!=bs_pg else "- (none)")
    m3.metric("Recommendation", ACTION_LABEL.get(rec_pg, rec_pg),
              delta="I18 deviation" if dv_pg and dv_pg!=bs_pg else "basic strategy")

    if not run_pg:
        st.info("Configure the situation above, then click **▶ Run**.")
    else:
        actions_pg = _available_actions(player_ranks_pg, upcard_pg, pg_rules)
        pg_results: dict[str, dict] = {}
        prog_pg = st.progress(0, text="Running simulation…")
        for i, act in enumerate(actions_pg):
            pg_results[act] = _simulate_ev(
                player_ranks_pg, upcard_pg, act, target_tc_pg, pg_rules, pg_nsims
            )
            prog_pg.progress((i+1)/len(actions_pg))
        prog_pg.empty()

        sorted_acts = sorted(actions_pg, key=lambda a: pg_results[a]['ev'], reverse=True)
        best_act    = sorted_acts[0]
        best_ev_pg  = pg_results[best_act]['ev']

        # Metrics
        mcols = st.columns(len(sorted_acts))
        for col, act in zip(mcols, sorted_acts):
            r  = pg_results[act]; ev = r['ev']; se = r['std_err']
            tags = []
            if act == best_act:                      tags.append("✅ Optimal")
            if act == rec_pg:                        tags.append("📖 Rec.")
            if act == dv_pg and dv_pg != bs_pg:      tags.append("★ I18")
            elif act == bs_pg:                       tags.append("BS")
            pfx = "🟢" if act==best_act else "🔴" if ev==min(pg_results[a]['ev'] for a in actions_pg) else "🟡"
            col.metric(
                f"{pfx} {ACTION_LABEL.get(act,act)}", f"{ev:+.5f}",
                delta=" · ".join(tags) if tags else None,
                help=f"95% CI: [{ev-1.96*se:+.4f}, {ev+1.96*se:+.4f}]  n={r['n']:,}",
            )

        # Table
        rows_pg = []
        for act in sorted_acts:
            r = pg_results[act]; ev = r['ev']; se = r['std_err']; ci = 1.96*se
            rows_pg.append({
                "Action":       ACTION_LABEL.get(act, act),
                "EV":           f"{ev:+.5f}",
                "EV %":         f"{ev*100:+.3f} %",
                "Δ vs optimal": f"{ev-best_ev_pg:+.5f}" if act!=best_act else "-",
                "IC 95%":       f"[{ev-ci:+.4f}, {ev+ci:+.4f}]",
                "n":            f"{r['n']:,}",
                "Tag":          ("★ I18" if act==dv_pg and dv_pg!=bs_pg
                                 else ("BS" if act==bs_pg else "")),
            })
        st.dataframe(pd.DataFrame(rows_pg), use_container_width=True, hide_index=True)

        # Bar chart
        fig, ax = plt.subplots(figsize=(max(7, len(actions_pg)*1.8), 4))
        fig.patch.set_facecolor('#0e1117'); ax.set_facecolor('#1a1a2e')
        evs  = [pg_results[a]['ev']            for a in sorted_acts]
        errs = [1.96*pg_results[a]['std_err']  for a in sorted_acts]
        lbls = [ACTION_LABEL.get(a,a)          for a in sorted_acts]
        cols_bar = [
            '#2ecc71' if a==best_act else
            '#e74c3c' if pg_results[a]['ev']<-0.6 else '#3498db'
            for a in sorted_acts
        ]
        bp = ax.bar(lbls, evs, color=cols_bar, yerr=errs, capsize=5,
                    error_kw={'color':'white','alpha':0.5}, width=0.55, zorder=3)
        for rect, ev in zip(bp, evs):
            off = 0.01 if ev >= 0 else -0.025
            ax.text(rect.get_x()+rect.get_width()/2, ev+off, f"{ev:+.4f}",
                    ha='center', va='bottom' if ev>=0 else 'top',
                    color='white', fontsize=9, fontweight='bold')
        for i, act in enumerate(sorted_acts):
            if act==dv_pg and dv_pg!=bs_pg:
                ax.annotate("★ I18", (i, evs[i]), textcoords="offset points", xytext=(0,14),
                            ha='center', color='#f39c12', fontsize=9, fontweight='bold')
            elif act==bs_pg and not (dv_pg and dv_pg!=bs_pg):
                ax.annotate("BS", (i, evs[i]), textcoords="offset points", xytext=(0,14),
                            ha='center', color='#9b59b6', fontsize=9, fontweight='bold')
        ax.axhline(-0.5, color='#e74c3c', linestyle='--', alpha=0.4, linewidth=1)
        ax.axhline(0, color='white', linestyle='-', alpha=0.1, linewidth=1)
        ax.set_ylabel("EV (bet units)", color='white')
        ax.set_title(
            f"{' + '.join(player_ranks_pg)} vs {upcard_pg}  ·  TC {target_tc_pg:+.1f}  ·  n={pg_nsims:,}",
            color='white', pad=10,
        )
        ax.tick_params(colors='white', labelsize=10)
        for sp in ax.spines.values(): sp.set_color('#333355')
        ax.grid(axis='y', color='#333355', linestyle='--', alpha=0.5, zorder=0)
        plt.tight_layout(); st.pyplot(fig); plt.close()

        st.success(
            f"**Best simulated action:** {ACTION_LABEL.get(best_act,best_act)}  -  "
            f"EV = **{best_ev_pg:+.5f}** ({best_ev_pg*100:+.3f} %)"
        )

        # ── Scan TC ──────────────────────────────────────────
        if pg_scan:
            st.divider()
            st.subheader("🔭 TC Scan - EV vs True Count")
            st.caption(f"n = {max(10_000, pg_nsims//5):,} hands per point · range −4 → +8 (step 0.5)")

            tc_range = [t/2 for t in range(-8, 17)]
            scan_n   = max(10_000, pg_nsims//5)
            scan_evs = {a: [] for a in actions_pg}
            step, total = 0, len(tc_range)*len(actions_pg)
            sp = st.progress(0)
            for tc_v in tc_range:
                for a in actions_pg:
                    scan_evs[a].append(
                        _simulate_ev(player_ranks_pg, upcard_pg, a, tc_v, pg_rules, scan_n)['ev']
                    )
                    step += 1; sp.progress(step/total)
            sp.empty()

            palette = ['#2ecc71','#3498db','#e67e22','#e74c3c','#9b59b6','#1abc9c']
            fig2, ax2 = plt.subplots(figsize=(13, 5))
            fig2.patch.set_facecolor('#0e1117'); ax2.set_facecolor('#1a1a2e')
            for i, a in enumerate(actions_pg):
                ax2.plot(tc_range, scan_evs[a], label=ACTION_LABEL.get(a,a),
                         color=palette[i%len(palette)],
                         lw=2.5 if a in (best_act, rec_pg) else 1.5,
                         ls='--' if a=='SUR' else '-')
            ax2.axvline(target_tc_pg, color='yellow', linestyle='--', alpha=0.5,
                        linewidth=1.2, label=f"Current TC ({target_tc_pg:+.1f})")
            ax2.axhline(-0.5, color='white', linestyle=':', alpha=0.2, linewidth=1)
            ax2.axhline(0,    color='white', linestyle=':', alpha=0.1, linewidth=1)
            ax2.set_xlabel("True Count", color='white')
            ax2.set_ylabel("EV", color='white')
            ax2.set_title(
                f"EV by action - {' + '.join(player_ranks_pg)} vs {upcard_pg}",
                color='white',
            )
            ax2.tick_params(colors='white')
            for sp2 in ax2.spines.values(): sp2.set_color('#333355')
            ax2.grid(color='#333355', linestyle='--', alpha=0.35)
            ax2.legend(facecolor='#1a1a2e', labelcolor='white', fontsize=9)
            plt.tight_layout(); st.pyplot(fig2); plt.close()

            # Crossovers
            crossovers = []
            for i, a1 in enumerate(actions_pg):
                for a2 in actions_pg[i+1:]:
                    for j in range(len(tc_range)-1):
                        e1a,e1b = scan_evs[a1][j],scan_evs[a1][j+1]
                        e2a,e2b = scan_evs[a2][j],scan_evs[a2][j+1]
                        if (e1a-e2a)*(e1b-e2b) < 0:
                            d = (e1b-e1a)-(e2b-e2a)
                            tc_x = tc_range[j]+0.5*(e2a-e1a)/d if d else tc_range[j]
                            before = a1 if e1a>e2a else a2
                            after  = a2 if e1a>e2a else a1
                            crossovers.append({
                                "Actions":      f"{ACTION_LABEL.get(a1,a1)} vs {ACTION_LABEL.get(a2,a2)}",
                                "TC crossover": f"{tc_x:+.2f}",
                                "Before":       f"→ {ACTION_LABEL.get(before,before)}",
                                "After":        f"→ {ACTION_LABEL.get(after,after)}",
                            })

            st.subheader("📐 Crossover points (index plays)")
            if crossovers:
                st.dataframe(pd.DataFrame(crossovers), use_container_width=True, hide_index=True)
                st.caption("These TC values correspond to card-counting index plays.")
            else:
                st.info("No crossover detected in TC range [−4, +8].")
