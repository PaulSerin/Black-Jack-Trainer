# Blackjack Trainer Pro

Personal blackjack training and simulation tool built around a mathematically rigorous Python engine and a React UI. Two independent applications share the same game engine.

---

## What's inside

### 1. Interactive Game — `react/blackjack.jsx`
A fully playable blackjack game in the browser with real-time strategy coaching.

**Features:**
- 6-deck shoe, S17, 3:2, late surrender, DAS — standard Vegas rules
- **Best Play hint** displayed next to the Hi-Lo counter: shows the optimal action for the current hand at the current true count
- **Illustrious 18 deviations** — when the true count justifies it, the hint overrides basic strategy and shows the I18 play (marked ★ I18 Deviation)
- **Insurance** — when the dealer shows an Ace, a dedicated insurance phase is offered before play. The hint recommends Take if TC ≥ +3, No otherwise
- **Hi-Lo counting panel** — live running count and true count (rounded to ½)
- Multi-hand mode (1–3 simultaneous hands), split up to 4 hands, double after split
- Bankroll tracking with adjustable bet size

### 2. EV Lab — `app_simulation.py` (Streamlit)
Two tools in one Streamlit app, navigated from the sidebar.

#### Monte Carlo Simulator
Runs millions of hands and reports long-run EV, variance, and bankroll trajectory.

| Parameter | Options |
|-----------|---------|
| Hands | 1 000 → 10 000 000 |
| Bet spread | 1-1 (flat) → 1-12 |
| Unit size | any € amount |
| Decks / Penetration | 1/2/4/6/8 decks, 50–95% |
| Table rules | H17/S17, DAS, late surrender, max splits, BJ payout |
| **Strategy** | **Basic Strategy** or **Advanced (Basic + I18 Deviations)** |

Advanced mode applies all 18 Illustrious 18 index plays including insurance at TC ≥ +3 and the 10,10 pair splits.

Outputs: EV %, EV/hand, EV/100 hands, total profit, bankroll range, win/loss/push breakdown, positive-TC ratio, standard deviation per hand.

#### EV Playground
Compute and compare the EV of every possible action for a specific hand situation.

- Click any card in your hand or the dealer upcard to change it via the rank picker
- Set a target True Count and table rules
- Run Monte Carlo with a biased shoe matching the TC
- Instantly see which action is optimal and by how much, with 95% confidence intervals
- Insurance action appears automatically when dealer upcard is Ace

---

## How to launch

### Prerequisites
```bash
# Python 3.11+
pip install streamlit numpy pandas matplotlib pytest
```

### Interactive Game (React)
The built version is already in `react/dist/`. Open it directly in a browser:
```
react/dist/index.html
```

To rebuild after modifying `blackjack.jsx`:
```bash
cd react
npm install
npm run build
```

### EV Lab (Streamlit)
```bash
streamlit run app_simulation.py
```
Opens at `http://localhost:8501` — navigate with the sidebar buttons.

### CLI simulation (no UI)
```bash
# Basic strategy, 500k hands, flat bet
python -m simulation.simulator --hands 500000 --spread 1-1 --unit-size 25

# Advanced strategy, 1M hands, 1-12 spread
python -m simulation.simulator --hands 1000000 --spread 1-12 --unit-size 25

# Custom rules
python -m simulation.simulator --hands 500000 --spread 1-8 --h17 --pen 0.80
```

---

## Project structure

```
├── app_simulation.py          # Streamlit EV Lab (2 pages)
├── react/
│   ├── blackjack.jsx          # Full game UI (single file, React + Tailwind)
│   ├── dist/                  # Built app — open index.html directly
│   └── main.jsx               # Entry point
├── simulation/
│   ├── engine.py              # Pure game engine: shoe, hand, deal, split, surrender
│   ├── counting.py            # Hi-Lo: running count, true count (rounded to ½)
│   ├── strategy.py            # Complete basic strategy tables: hard / soft / split
│   ├── deviations.py          # Illustrious 18 — canonical list from Schlesinger
│   ├── betting.py             # Bet ramp: spread → unit bet given true count
│   ├── simulator.py           # Monte Carlo engine
│   └── config.py              # SimConfig, TableRules, BettingConfig dataclasses
├── tests/
│   ├── test_engine.py
│   ├── test_strategy.py
│   ├── test_counting.py
│   ├── test_deviations.py
│   └── test_simulator.py
├── notebooks/
│   └── variance_analysis.ipynb
└── docs/
    └── references/            # Strategy chart, I18 deviation table images
```

---

## Running the tests

```bash
python -m pytest tests/ -v
```

334 tests, all passing. Covers engine correctness, every cell of the basic strategy tables, Hi-Lo counting, all 18 I18 deviations, and simulator output.

```bash
# Verify strategy and deviations integrity independently
python simulation/strategy.py --verify
python simulation/deviations.py --verify
```

---

## Strategy implemented

### Basic Strategy
6 decks, S17, DAS, late surrender — source: Wizard of Odds.
- Hard totals: 5–21 vs all upcards
- Soft totals: A2–A9 vs all upcards
- Pairs: 2,2 through A,A vs all upcards (Y/N for DAS-dependent splits)

### Illustrious 18 (Schlesinger, *Blackjack Attack*)
Canonical list of 18 index plays applied when the True Count justifies them:

| # | Situation | TC | Action |
|---|-----------|-----|--------|
| 1 | Insurance | ≥ +3 | Take |
| 2 | 16 vs 10 | ≥ 0 | Stand |
| 3 | 15 vs 10 | ≥ +4 | Stand |
| 4 | 10,10 vs 5 | ≥ +5 | Split |
| 5 | 10,10 vs 6 | ≥ +4 | Split |
| 6 | 10 vs 10 | ≥ +4 | Double |
| 7 | 12 vs 3 | ≥ +2 | Stand |
| 8 | 12 vs 2 | ≥ +3 | Stand |
| 9 | 11 vs A | ≥ +1 | Double |
| 10 | 9 vs 2 | ≥ +1 | Double |
| 11 | 10 vs A | ≥ +4 | Double |
| 12 | 9 vs 7 | ≥ +3 | Double |
| 13 | 16 vs 9 | ≥ +5 | Stand |
| 14 | 13 vs 2 | < −1 | Hit |
| 15 | 12 vs 4 | < 0 | Hit |
| 16 | 12 vs 5 | < −2 | Hit |
| 17 | 12 vs 6 | < −1 | Hit |
| 18 | 13 vs 3 | < −2 | Hit |

### Hi-Lo System
- **+1**: 2–6 / **0**: 7–9 / **−1**: 10–A
- True Count = Running Count ÷ Decks remaining (rounded to nearest ½)
- Shoe shuffled after 75% penetration
