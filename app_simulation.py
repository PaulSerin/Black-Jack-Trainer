"""
app_simulation.py — Blackjack EV Lab + EV Playground
Streamlit UI avec deux onglets :
  1. Monte Carlo Simulator  — simulation longue durée avec stratégie complète
  2. EV Playground          — EV par action pour une main précise vs TC donné

Lancement : streamlit run app_simulation.py
"""

from __future__ import annotations

import os, sys, random, time
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation.simulator import simulate
from simulation.config import BettingConfig, SimConfig, TableRules
from simulation.engine import Card, Hand
from simulation.strategy import get_basic_strategy
from simulation.deviations import get_deviation

# ═══════════════════════════════════════════════════════════════
# Page config
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Blackjack EV Lab",
    page_icon="🃏",
    layout="wide",
)

st.title("🃏 Blackjack EV Lab")

tab_sim, tab_play = st.tabs(["📊 Monte Carlo Simulator", "🔬 EV Playground"])


# ═══════════════════════════════════════════════════════════════
# ── TAB 1 : Monte Carlo Simulator (original) ─────────────────
# ═══════════════════════════════════════════════════════════════
with tab_sim:
    st.caption("Simulation longue durée — basic strategy complète, bet spread Hi-Lo")

    # ── Sidebar parameters (only shown when this tab is active) ─
    with st.sidebar:
        st.header("📊 Monte Carlo")

        hands = st.number_input(
            "Hands (rounds)",
            min_value=1_000, max_value=10_000_000, value=500_000, step=100_000,
        )
        spread_options = ["1-1","1-2","1-4","1-6","1-8","1-10","1-12"]
        spread    = st.selectbox("Bet spread", spread_options, index=0)
        unit_size = st.number_input("Unit size (€)", min_value=1., max_value=10_000., value=10., step=5.)
        bankroll  = st.number_input("Initial bankroll (€)", min_value=100., max_value=1e8, value=1e7, step=10_000.)

        use_seed = st.checkbox("Fix random seed", value=False)
        seed = None
        if use_seed:
            seed = st.number_input("Seed", min_value=0, max_value=999_999, value=42, step=1)

        st.divider()
        st.header("⚙️ Table Rules")

        decks       = st.selectbox("Decks", [1,2,4,6,8], index=3)
        penetration = st.slider("Penetration", 0.50, 0.95, 0.75, 0.05, format="%.0f%%")
        dealer_h17  = st.toggle("Dealer hits soft 17 (H17)", value=False)
        das_sim     = st.toggle("Double after split (DAS)", value=True)
        surrender_sim = st.toggle("Late surrender", value=True)
        max_split   = st.selectbox("Max split hands", [2,3,4], index=2)
        bj_payout_s = st.selectbox("Blackjack payout", ["3:2 (1.5)","6:5 (1.2)"], index=0)
        bj_payout_v = 1.5 if bj_payout_s.startswith("3") else 1.2

        st.divider()
        run_btn_sim = st.button("▶ Run Simulation", type="primary", use_container_width=True)

    if not run_btn_sim:
        st.info("Configure les paramètres dans la barre latérale, puis clique **▶ Run Simulation**.")
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
                initial_bankroll = float(bankroll),
                seed             = int(seed) if seed is not None else None,
            )
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            st.stop()

        with st.spinner(f"Simulating {hands:,} hands…"):
            t0 = time.perf_counter()
            r  = simulate(cfg)
            elapsed = time.perf_counter() - t0

        st.success(f"Done in {elapsed:.1f}s — {r.hands_played:,} rounds played.")

        # KPI
        st.subheader("Expected Value")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("EV %",           f"{r.ev_percent:+.4f}%")
        c2.metric("EV / hand",      f"{r.ev_per_hand:+.4f} €")
        c3.metric("EV / 100 hands", f"{r.ev_per_100_hands:+.2f} €")
        c4.metric("Total profit",   f"{r.total_profit:+,.0f} €")
        c5.metric("Total wagered",  f"{r.total_wagered:,.0f} €")

        st.subheader("Bankroll")
        b1,b2,b3,b4 = st.columns(4)
        b1.metric("Final bankroll", f"{r.final_bankroll:,.0f} €", delta=f"{r.final_bankroll-bankroll:+,.0f} €")
        b2.metric("Peak bankroll",  f"{r.max_bankroll:,.0f} €")
        b3.metric("Low bankroll",   f"{r.min_bankroll:,.0f} €")
        b4.metric("Average bet",    f"{r.average_bet:.2f} €")

        # Hand breakdown
        st.subheader("Hand Breakdown")
        st.dataframe(pd.DataFrame({
            "Outcome":     ["Wins","Losses","Pushes","Blackjacks","Surrenders","Player busts"],
            "Count":       [r.wins, r.losses, r.pushes, r.blackjacks, r.surrenders, r.busts],
            "% of rounds": [f"{v/r.hands_played:.2%}" for v in
                            [r.wins, r.losses, r.pushes, r.blackjacks, r.surrenders, r.busts]],
        }), use_container_width=True, hide_index=True)

        # Counting & dispersion
        st.subheader("Counting & Dispersion")
        s1,s2,s3 = st.columns(3)
        s1.metric("Positive-TC rounds",        f"{r.positive_tc_hands:,}", delta=f"{r.positive_tc_ratio:.1%}")
        s2.metric("Profit std dev / hand",      f"{r.profit_std:.4f} €")
        s3.metric("Profit std dev / hand (u)",  f"{r.profit_std_units:.4f} u")

        # Charts
        st.subheader("Charts")
        col_l, col_r = st.columns(2)

        with col_l:
            fig, ax = plt.subplots(figsize=(5, 3.5))
            ax.bar(["Wins","Losses","Pushes"], [r.wins, r.losses, r.pushes])
            ax.set_title("Win / Loss / Push breakdown")
            ax.set_ylabel("Rounds")
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:,.0f}"))
            ax.grid(axis="y", linestyle=":", alpha=0.5)
            plt.tight_layout(); st.pyplot(fig); plt.close(fig)

        with col_r:
            fig, ax = plt.subplots(figsize=(5, 3.5))
            metrics    = ["EV %","Win %","Loss %","Push %","+TC %"]
            values_pct = [
                r.ev_percent,
                r.wins/r.hands_played*100, r.losses/r.hands_played*100,
                r.pushes/r.hands_played*100, r.positive_tc_ratio*100,
            ]
            ax.bar(metrics, values_pct)
            ax.axhline(0, linewidth=0.8)
            ax.set_title("Key metrics (%)")
            ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
            ax.grid(axis="y", linestyle=":", alpha=0.5)
            plt.tight_layout(); st.pyplot(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 2.5))
        ax.barh(["Bankroll range"], [r.max_bankroll - r.min_bankroll], left=[r.min_bankroll], height=0.4)
        ax.axvline(bankroll,         linestyle="--", linewidth=1, label=f"Initial {bankroll:,.0f} €")
        ax.axvline(r.final_bankroll, linestyle=":",  linewidth=1, label=f"Final {r.final_bankroll:,.0f} €")
        ax.set_title("Bankroll range (min → max)")
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:,.0f} €"))
        ax.legend(loc="lower right")
        plt.tight_layout(); st.pyplot(fig); plt.close(fig)

        with st.expander("Simulation config recap"):
            st.code(
                f"Hands:     {r.hands_played:,}\n"
                f"Decks:     {decks}  |  Penetration: {penetration:.0%}\n"
                f"Spread:    {spread}  |  Unit: {unit_size} €  |  BJ payout: {bj_payout_s}\n"
                f"Rules:     {'H17' if dealer_h17 else 'S17'}, "
                f"{'DAS' if das_sim else 'no DAS'}, "
                f"{'Surrender' if surrender_sim else 'no Surrender'}, "
                f"max {max_split} split hands\n"
                f"Seed:      {seed if seed is not None else 'random'}\n"
                f"Elapsed:   {elapsed:.2f}s",
                language=None,
            )


# ═══════════════════════════════════════════════════════════════
# ── TAB 2 : EV Playground ────────────────────────────────────
# ═══════════════════════════════════════════════════════════════

# ── Pure helpers ─────────────────────────────────────────────
ALL_RANKS  = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
LOW_RANKS  = {'2','3','4','5','6'}
MID_RANKS  = {'7','8','9'}
HIGH_RANKS = {'10','J','Q','K','A'}
RANK_VAL   = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
              '10':10,'J':10,'Q':10,'K':10,'A':11}
ACTION_LABEL = {
    'H':'Hit','S':'Stand','D':'Double','Ds':'Double/Stand',
    'Y':'Split','Y/N':'Split (DAS)','SUR':'Surrender',
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

def _hilo(rank: str) -> int:
    return 1 if rank in LOW_RANKS else (0 if rank in MID_RANKS else -1)

def _hand_value(ranks: list[str]) -> int:
    v = sum(RANK_VAL[r] for r in ranks); a = ranks.count('A')
    while v > 21 and a > 0: v -= 10; a -= 1
    return v

def _is_soft(ranks: list[str]) -> bool:
    v = sum(RANK_VAL[r] for r in ranks); a = ranks.count('A')
    while v > 21 and a > 0: v -= 10; a -= 1
    return a > 0 and v <= 21

def _is_pair(ranks: list[str]) -> bool:
    return len(ranks) == 2 and RANK_VAL[ranks[0]] == RANK_VAL[ranks[1]]

def _make_card(r: str) -> Card:
    return Card(r, '♠')

def _make_hand(ranks: list[str], split: bool = False) -> Hand:
    h = Hand(is_split_hand=split)
    for r in ranks: h.add_card(_make_card(r))
    return h

def _build_shoe(player_ranks, upcard_rank, target_tc, num_decks=6):
    counts: Counter = Counter({r: num_decks * 4 for r in ALL_RANKS})
    for r in player_ranks + [upcard_rank]:
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
    if pv > 21:            return -bet_mult
    if p_bj and not d_bj: return  bj_pay * bet_mult
    if d_bj and not p_bj: return -bet_mult
    if p_bj and d_bj:     return  0.0
    if dv > 21 or pv > dv: return  bet_mult
    if pv < dv:            return -bet_mult
    return 0.0

def _play_basic(hand, upcard, draw, das, is_split=False):
    h = list(hand); bet_mult = 1.0
    while True:
        v = _hand_value(h)
        if v > 21 or v == 21: break
        bs = get_basic_strategy(_make_hand(h, is_split), _make_card(upcard))
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

def _simulate_ev(player_ranks, upcard_rank, action, target_tc, rules, n_sims=100_000):
    hits_s17 = rules.get('hits_soft_17', False)
    das      = rules.get('das', True)
    bj_pay   = rules.get('bj_payout', 1.5)
    ndeck    = rules.get('num_decks', 6)
    results  = []
    for _ in range(n_sims):
        shoe = _build_shoe(player_ranks, upcard_rank, target_tc, ndeck)
        idx  = 0
        def draw():
            nonlocal idx
            if idx >= len(shoe): return None
            c = shoe[idx]; idx += 1; return c
        hole = draw()
        if hole is None: continue
        d_init = [hole, upcard_rank]; d_bj = (_hand_value(d_init)==21)
        if action == 'SUR':
            results.append(-1.0 if d_bj else -0.5); continue
        if d_bj:
            pv = _hand_value(player_ranks)
            results.append(0.0 if (len(player_ranks)==2 and pv==21) else -1.0); continue
        if action == 'S':
            results.append(_outcome(player_ranks, _run_dealer(d_init, draw, hits_s17), bj_pay=bj_pay))
        elif action == 'H':
            h = list(player_ranks) + [draw()]
            h, _ = _play_basic(h, upcard_rank, draw, das)
            results.append(_outcome(h, _run_dealer(d_init, draw, hits_s17), bj_pay=bj_pay))
        elif action == 'D':
            h = list(player_ranks) + [draw()]
            results.append(_outcome(h, _run_dealer(d_init, draw, hits_s17), bet_mult=2.0, bj_pay=bj_pay))
        elif action in ('Y','Y/N'):
            h1 = [player_ranks[0], draw()]; h2 = [player_ranks[1], draw()]
            h1, bm1 = _play_basic(h1, upcard_rank, draw, das, is_split=True)
            h2, bm2 = _play_basic(h2, upcard_rank, draw, das, is_split=True)
            df = _run_dealer(d_init, draw, hits_s17)
            results.append(_outcome(h1,df,bm1,True,bj_pay) + _outcome(h2,df,bm2,True,bj_pay))
    if not results: return {'ev':0.,'std_err':0.,'n':0,'action':action}
    arr = np.array(results)
    return {'ev':float(np.mean(arr)), 'std_err':float(np.std(arr,ddof=1)/np.sqrt(len(arr))),
            'n':len(arr), 'action':action}

def _available_actions(player_ranks, rules):
    acts = ['H','S']
    if len(player_ranks) == 2:
        acts.append('D')
        if rules.get('surrender_allowed', True): acts.append('SUR')
        if _is_pair(player_ranks): acts.append('Y')
    return acts

# ── Tab 2 UI ─────────────────────────────────────────────────
with tab_play:
    st.caption(
        "Simule l'EV de chaque action possible pour une main précise vs dealer à TC donné. "
        "Monte Carlo avec sabot biaisé selon le True Count cible."
    )

    col_cfg, col_main = st.columns([1, 2])

    with col_cfg:
        st.subheader("🎴 Situation")
        preset_name = st.selectbox("Preset", list(PRESETS.keys()), key="pg_preset")
        preset_val  = PRESETS[preset_name]
        default_p   = preset_val[0] if preset_val else ['8','8']
        default_u   = preset_val[1] if preset_val else 'Q'

        st.markdown("**Main du joueur**")
        n_cards = st.number_input("Cartes", 2, 5, len(default_p), key="pg_nc")
        pg_cols = st.columns(min(int(n_cards), 5))
        player_ranks_pg: list[str] = []
        for i in range(int(n_cards)):
            dr = default_p[i] if i < len(default_p) else '2'
            r  = pg_cols[i % len(pg_cols)].selectbox(
                f"C{i+1}", ALL_RANKS, index=ALL_RANKS.index(dr),
                key=f"pg_pc{i}", label_visibility="collapsed",
            )
            player_ranks_pg.append(r)

        upcard_pg = st.selectbox(
            "Upcard dealer", ALL_RANKS, index=ALL_RANKS.index(default_u), key="pg_up"
        )
        target_tc_pg = st.slider("True Count", -5.0, 8.0, 0.0, 0.5, key="pg_tc")

        st.markdown("**Règles**")
        rc1, rc2 = st.columns(2)
        pg_decks   = rc1.selectbox("Decks", [1,2,6,8], index=2, key="pg_decks")
        pg_h17     = rc2.checkbox("Dealer H17", value=False, key="pg_h17")
        pg_sur     = rc1.checkbox("Surrender",  value=True,  key="pg_sur")
        pg_das     = rc2.checkbox("DAS",        value=True,  key="pg_das")
        pg_bj      = st.radio("BJ payout", [1.5,1.2], horizontal=True, key="pg_bj",
                              format_func=lambda x: "3:2" if x==1.5 else "6:5")
        pg_nsims   = st.select_slider("Simulations", [10_000,50_000,100_000,200_000,500_000],
                                      value=100_000, key="pg_nsims",
                                      format_func=lambda x: f"{x:,}")
        pg_scan    = st.checkbox("Scan TC (−4 → +8)", value=False, key="pg_scan")
        run_pg     = st.button("▶ Lancer", type="primary", use_container_width=True, key="pg_run")

    pg_rules = {'num_decks':pg_decks,'hits_soft_17':pg_h17,
                'surrender_allowed':pg_sur,'das':pg_das,'bj_payout':pg_bj}

    with col_main:
        pv_pg    = _hand_value(player_ranks_pg)
        psoft_pg = " (soft)" if _is_soft(player_ranks_pg) else ""
        ppair_pg = " · paire" if _is_pair(player_ranks_pg) else ""
        st.subheader(f"{' + '.join(player_ranks_pg)} = **{pv_pg}{psoft_pg}**{ppair_pg}   vs   **{upcard_pg}**   ·   TC **{target_tc_pg:+.1f}**")

        h_pg  = _make_hand(player_ranks_pg)
        u_pg  = _make_card(upcard_pg)
        bs_pg = get_basic_strategy(h_pg, u_pg)
        dv_pg = get_deviation(h_pg, u_pg, target_tc_pg)
        rec_pg = dv_pg if dv_pg else bs_pg

        m1, m2, m3 = st.columns(3)
        m1.metric("Basic Strategy", ACTION_LABEL.get(bs_pg, bs_pg))
        m2.metric("I18 Déviation",
                  f"★ {ACTION_LABEL.get(dv_pg,dv_pg)}" if dv_pg and dv_pg!=bs_pg else "— (aucune)")
        m3.metric("Recommandation", ACTION_LABEL.get(rec_pg, rec_pg),
                  delta="déviation I18" if dv_pg and dv_pg!=bs_pg else "basic strategy")

        if not run_pg:
            st.info("Configure la situation à gauche, puis clique **▶ Lancer**.")
        else:
            actions_pg = _available_actions(player_ranks_pg, pg_rules)
            pg_results: dict[str, dict] = {}
            prog_pg = st.progress(0, text="Simulation…")
            for i, act in enumerate(actions_pg):
                pg_results[act] = _simulate_ev(player_ranks_pg, upcard_pg, act,
                                               target_tc_pg, pg_rules, pg_nsims)
                prog_pg.progress((i+1)/len(actions_pg))
            prog_pg.empty()

            sorted_acts = sorted(actions_pg, key=lambda a: pg_results[a]['ev'], reverse=True)
            best_act    = sorted_acts[0]
            best_ev_pg  = pg_results[best_act]['ev']

            # Metrics row
            mcols = st.columns(len(sorted_acts))
            for col, act in zip(mcols, sorted_acts):
                r   = pg_results[act]
                ev  = r['ev']; se = r['std_err']
                tags = []
                if act == best_act:  tags.append("✅ Optimal")
                if act == rec_pg:    tags.append("📖 Rec.")
                if act == dv_pg and dv_pg != bs_pg: tags.append("★ I18")
                elif act == bs_pg:   tags.append("BS")
                pfx = "🟢" if act==best_act else "🔴" if ev==min(pg_results[a]['ev'] for a in actions_pg) else "🟡"
                col.metric(f"{pfx} {ACTION_LABEL.get(act,act)}", f"{ev:+.5f}",
                           delta=" · ".join(tags) if tags else None,
                           help=f"IC 95%: [{ev-1.96*se:+.4f}, {ev+1.96*se:+.4f}]  n={r['n']:,}")

            # Table
            rows_pg = []
            for act in sorted_acts:
                r = pg_results[act]; ev = r['ev']; se = r['std_err']; ci = 1.96*se
                rows_pg.append({
                    "Action":       ACTION_LABEL.get(act, act),
                    "EV":           f"{ev:+.5f}",
                    "EV %":         f"{ev*100:+.3f} %",
                    "Δ vs optimal": f"{ev-best_ev_pg:+.5f}" if act!=best_act else "—",
                    "IC 95%":       f"[{ev-ci:+.4f}, {ev+ci:+.4f}]",
                    "n":            f"{r['n']:,}",
                    "Tag":          ("★ I18" if act==dv_pg and dv_pg!=bs_pg
                                     else ("BS" if act==bs_pg else "")),
                })
            st.dataframe(pd.DataFrame(rows_pg), use_container_width=True, hide_index=True)

            # Bar chart
            fig, ax = plt.subplots(figsize=(max(6, len(actions_pg)*1.6), 4))
            fig.patch.set_facecolor('#0e1117'); ax.set_facecolor('#1a1a2e')
            evs  = [pg_results[a]['ev']             for a in sorted_acts]
            errs = [1.96*pg_results[a]['std_err']   for a in sorted_acts]
            lbls = [ACTION_LABEL.get(a,a)           for a in sorted_acts]
            cols_bar = ['#2ecc71' if a==best_act else '#e74c3c' if pg_results[a]['ev']<-0.6 else '#3498db'
                        for a in sorted_acts]
            bp = ax.bar(lbls, evs, color=cols_bar, yerr=errs, capsize=5,
                        error_kw={'color':'white','alpha':0.5}, width=0.55, zorder=3)
            for rect, ev in zip(bp, evs):
                off = 0.01 if ev >= 0 else -0.025
                ax.text(rect.get_x()+rect.get_width()/2, ev+off, f"{ev:+.4f}",
                        ha='center', va='bottom' if ev>=0 else 'top',
                        color='white', fontsize=8, fontweight='bold')
            for i, act in enumerate(sorted_acts):
                if act==dv_pg and dv_pg!=bs_pg:
                    ax.annotate("★ I18", (i, evs[i]), textcoords="offset points", xytext=(0,14),
                                ha='center', color='#f39c12', fontsize=8, fontweight='bold')
                elif act==bs_pg and not (dv_pg and dv_pg!=bs_pg):
                    ax.annotate("BS", (i, evs[i]), textcoords="offset points", xytext=(0,14),
                                ha='center', color='#9b59b6', fontsize=8, fontweight='bold')
            ax.axhline(-0.5, color='#e74c3c', linestyle='--', alpha=0.4, linewidth=1)
            ax.axhline(0, color='white', linestyle='-', alpha=0.1, linewidth=1)
            ax.set_ylabel("EV (unités)", color='white')
            ax.set_title(f"{' + '.join(player_ranks_pg)} vs {upcard_pg}  ·  TC {target_tc_pg:+.1f}  ·  n={pg_nsims:,}",
                         color='white', pad=10)
            ax.tick_params(colors='white', labelsize=9)
            for sp in ax.spines.values(): sp.set_color('#333355')
            ax.grid(axis='y', color='#333355', linestyle='--', alpha=0.5, zorder=0)
            plt.tight_layout(); st.pyplot(fig); plt.close()

            # Conclusion
            st.success(f"**Optimal simulé :** {ACTION_LABEL.get(best_act,best_act)}  —  "
                       f"EV = **{best_ev_pg:+.5f}** ({best_ev_pg*100:+.3f} %)")

            # TC Scan
            if pg_scan:
                st.divider()
                st.subheader("🔭 Scan TC — EV selon le True Count")
                tc_range  = [t/2 for t in range(-8, 17)]
                scan_n    = max(10_000, pg_nsims//5)
                scan_evs  = {a: [] for a in actions_pg}
                step, total = 0, len(tc_range)*len(actions_pg)
                sp = st.progress(0)
                for tc_v in tc_range:
                    for a in actions_pg:
                        scan_evs[a].append(_simulate_ev(player_ranks_pg, upcard_pg, a,
                                                        tc_v, pg_rules, scan_n)['ev'])
                        step += 1; sp.progress(step/total)
                sp.empty()

                palette = ['#2ecc71','#3498db','#e67e22','#e74c3c','#9b59b6','#1abc9c']
                fig2, ax2 = plt.subplots(figsize=(12, 4.5))
                fig2.patch.set_facecolor('#0e1117'); ax2.set_facecolor('#1a1a2e')
                for i, a in enumerate(actions_pg):
                    ax2.plot(tc_range, scan_evs[a], label=ACTION_LABEL.get(a,a),
                             color=palette[i%len(palette)],
                             lw=2.5 if a in (best_act, rec_pg) else 1.5,
                             ls='--' if a=='SUR' else '-')
                ax2.axvline(target_tc_pg, color='yellow', linestyle='--', alpha=0.5, linewidth=1.2,
                            label=f"TC actuel ({target_tc_pg:+.1f})")
                ax2.axhline(-0.5, color='white', linestyle=':', alpha=0.2, linewidth=1)
                ax2.axhline(0,    color='white', linestyle=':', alpha=0.1, linewidth=1)
                ax2.set_xlabel("True Count", color='white')
                ax2.set_ylabel("EV", color='white')
                ax2.set_title(f"{' + '.join(player_ranks_pg)} vs {upcard_pg}", color='white')
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
                                    "Actions":       f"{ACTION_LABEL.get(a1,a1)} vs {ACTION_LABEL.get(a2,a2)}",
                                    "TC croisement": f"{tc_x:+.2f}",
                                    "Avant":         f"→ {ACTION_LABEL.get(before,before)}",
                                    "Après":         f"→ {ACTION_LABEL.get(after,after)}",
                                })
                st.subheader("📐 Points de croisement (index plays)")
                if crossovers:
                    st.dataframe(pd.DataFrame(crossovers), use_container_width=True, hide_index=True)
                    st.caption("Ces TC correspondent aux 'index plays' du comptage de cartes.")
                else:
                    st.info("Aucun croisement détecté dans TC [−4, +8].")
