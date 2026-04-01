# Architecture - Blackjack Trainer Pro

## Vue d'ensemble

L'application est composée de **deux programmes indépendants** qui partagent les mêmes
règles de jeu, mais ne s'appellent pas directement l'un l'autre :

```
┌─────────────────────────────────────────────────────────────┐
│                   Blackjack Trainer Pro                     │
│                                                             │
│   ┌────────────────────┐     ┌────────────────────────┐     │
│   │  Interactive Game  │     │       EV Lab           │     │
│   │  react/blackjack   │     │  app_simulation.py     │     │
│   │  .jsx              │     │  (Streamlit)           │     │
│   │                    │     │                        │     │
│   │  JS reimplements   │     │  Calls Python engine   │     │
│   │  strategy + Hi-Lo  │     │  directly              │     │
│   └────────────────────┘     └────────────────────────┘     │
│            │                           │                    │
│            └──────────┬────────────────┘                    │
│                       │  Same rules, separate code          │
│               ┌───────▼────────┐                            │
│               │  simulation/   │                            │
│               │  Python engine │                            │
│               └───────────────-┘                            │
└─────────────────────────────────────────────────────────────┘
```

**Important :** le jeu React réimplémente les tables de stratégie et le comptage
Hi-Lo directement en JavaScript. Il n'appelle pas le Python. La cohérence entre
les deux est assurée par les tests et par `CLAUDE.md`.

---

## Structure des fichiers

```
├── app_simulation.py          # Streamlit EV Lab (point d'entrée Streamlit)
├── ARCHITECTURE.md            # Ce fichier
├── CLAUDE.md                  # Instructions pour l'IA (règles métier critiques)
├── README.md                  # Guide utilisateur
│
├── simulation/                # Moteur Python partagé
│   ├── engine.py              # Sabot, main, actions de jeu
│   ├── strategy.py            # Tables basic strategy
│   ├── counting.py            # Comptage Hi-Lo
│   ├── deviations.py          # Illustrious 18 (I18)
│   ├── betting.py             # Rampe de mise selon TC
│   ├── simulator.py           # Boucle Monte Carlo
│   └── config.py              # Dataclasses de configuration
│
├── tests/                     # 334 tests unitaires
│   ├── test_engine.py
│   ├── test_strategy.py
│   ├── test_counting.py
│   ├── test_deviations.py
│   └── test_simulator.py
│
├── react/                     # Jeu interactif (React + Vite)
│   ├── blackjack.jsx          # Application complète (fichier unique)
│   ├── main.jsx               # Point d'entrée React
│   ├── index.html             # Shell HTML
│   ├── index.css              # CSS global (Tailwind directives)
│   ├── vite.config.js         # Config Vite (base: './' pour file://)
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── dist/                  # Build de production (ouvrir dist/index.html)
│
├── docs/
│   └── references/            # Images de référence stratégie
│       ├── basic-blackjack-strategy-chart.png
│       └── Illustrious_18_Deviations.png
│
└── notebooks/
    └── variance_analysis.ipynb
```

---

## Partie 1 - Moteur Python (`simulation/`)

### `engine.py` - Moteur de jeu pur

Zéro stratégie, zéro comptage. Uniquement la mécanique des cartes.

```
Card(rank, suit)
  └── rank ∈ {'2'..'10','jack','queen','king','ace'}

Shoe(num_decks, penetration)
  ├── shuffle()           → mélange et remet à zéro
  ├── deal() → Card       → tire la prochaine carte
  └── needs_shuffle       → True si pénétration atteinte

Hand(is_split_hand)
  ├── add_card(card)
  ├── value               → total (as = 11 ou 1)
  ├── is_blackjack        → True si 2 cartes = 21 (hors split)
  ├── is_bust             → True si value > 21
  └── doubled             → flag pour le simulateur

Fonctions libres :
  can_split(hand)         → 2 cartes de même valeur
  can_double(hand)        → exactement 2 cartes
  can_surrender(hand, upcard)
  split_hand(hand, shoe) → (Hand, Hand)
  dealer_must_hit(hand, h17) → S17 ou H17
  compute_hand_result(player, dealer) → 'win'|'lose'|'push'|'bust'|'blackjack'
```

### `strategy.py` - Basic strategy (6 decks, S17, DAS, Late Surrender)

Source : Wizard of Odds. Tables immuables, fonctions pures.

```
_H[total][upcard_idx]     → action hard  (total 8–17, upcard 2–A)
_SOFT[kicker][upcard_idx] → action soft  (A+2 à A+9)
_SPLIT[card_val][upcard_idx] → Y / Y/N / N

Actions retournées : 'H' | 'S' | 'D' | 'Ds' | 'SUR' | 'Y' | 'Y/N'
  D   = Double if possible, else Hit
  Ds  = Double if possible, else Stand
  Y/N = Split seulement si DAS autorisé

get_basic_strategy(hand, dealer_upcard) → str
```

### `counting.py` - Comptage Hi-Lo

```
HiLoCounter
  ├── update(card)        → met à jour le running count
  ├── reset()             → remet RC à 0 (nouveau sabot)
  ├── running_count       → RC courant
  └── true_count(shoe)    → RC / decks_restants, arrondi à 0.5

Valeurs Hi-Lo :
  +1 : 2–6
   0 : 7–9
  −1 : 10, J, Q, K, A

Règle critique : la hole card du dealer n'est comptée
qu'à sa révélation, pas à la donne.
```

### `deviations.py` - Illustrious 18 (Schlesinger)

18 entrées exactes. Remplacent la basic strategy quand le TC le justifie.

```python
DEVIATIONS = [
    # (hand_type, player_total, dealer_upcard, operator, threshold, action)
    ('insurance', None, 'ace', '>=', 3,  'take'),   # #1
    ('hard',      16,   '10',  '>=', 0,  'S'),       # #2
    ('hard',      15,   '10',  '>=', 4,  'S'),       # #3
    ('pair',      10,   '5',   '>=', 5,  'Y'),       # #4
    ('pair',      10,   '6',   '>=', 4,  'Y'),       # #5
    # ... 13 autres
]

get_deviation(hand, dealer_upcard, true_count) → str | None
should_take_insurance(dealer_upcard, true_count) → bool

Règle critique : une déviation I18 "Stand" ne remplace
JAMAIS SUR (les I18 sont calibrés pour jeux sans surrender).
```

### `betting.py` - Rampe de mise

```
BettingRamp
  └── compute_bet(tc, betting_config) → float

Logique : interpolation linéaire entre spread_min et spread_max
selon le TC. TC ≤ 1 → mise min. TC ≥ max → mise max.
```

### `config.py` - Dataclasses

```python
TableRules
  dealer_hits_soft_17: bool = False   # S17 par défaut
  double_after_split:  bool = True
  surrender_allowed:   bool = True
  max_split_hands:     int  = 4
  blackjack_payout:    float = 1.5   # 3:2

BettingConfig
  spread_min: int   = 1
  spread_max: int   = 12
  unit_size:  float = 25.0
  from_string('1-12', unit_size=25) → BettingConfig

SimConfig
  hands, decks, penetration
  betting: BettingConfig
  rules: TableRules
  initial_bankroll, seed, use_deviations
  track_history, history_interval     # pour le graphe bankroll
  track_hand_outcomes                 # pour l'histogramme

SimulationResult
  # Métriques financières
  ev_percent, ev_per_hand, ev_per_100_hands
  total_profit, total_wagered, average_bet
  final_bankroll, max_bankroll, min_bankroll
  # Comptage des mains
  wins, losses, pushes, blackjacks, surrenders, busts
  positive_tc_hands, positive_tc_ratio
  # Dispersion
  profit_std, profit_std_units         # algo Welford en ligne
  # Données pour graphes
  bankroll_history: [(round_idx, bankroll), ...]
  tc_bucket_ev: {-3..5: {profit, count}}  # toujours rempli
  hand_outcomes: [profit_par_main, ...]   # si track_hand_outcomes
```

### `simulator.py` - Boucle Monte Carlo

Orchestre tous les modules ci-dessus.

```
simulate(config: SimConfig) → SimulationResult

Ordre de comptage (convention américaine) :
  P1 visible → D1/upcard visible → P2 visible → D2/hole (non compté)
  → insurance check (si upcard = As et use_deviations)
  → player joue  [_play_hand, récursif pour les splits]
  → D2 compté à la révélation
  → dealer joue  [dealer_must_hit]
  → compute_hand_result pour chaque main

_pick_action(hand, upcard, tc, use_deviations)
  → déviation I18 si applicable, sinon basic strategy
  → protège SUR : une déviation "Stand" ne remplace pas SUR

_resolve_action(action, hand, upcard, rules, n_split_hands)
  → traduit l'action stratégique en action réalisable
  → D/Ds → double si possible, sinon H/S
  → SUR → surrender si autorisé, sinon H
  → Y/Y/N → split si règles le permettent, sinon hard fallback

_play_hand(...) → [(Hand, bet), ...]
  → récursif pour les splits
  → compte chaque carte tirée dans le HiLoCounter
```

---

## Partie 2 - EV Lab Streamlit (`app_simulation.py`)

### Navigation

```
Sidebar : boutons "📊 Monte Carlo Simulator" | "🔬 EV Playground"
→ st.session_state.page contrôle quelle page est affichée
```

### Page 1 - Monte Carlo Simulator

Paramètres exposés dans 3 colonnes :
- **Col 1** : nombre de mains, spread, unit size, bankroll, seed
- **Col 2** : règles de table (decks, pénétration, H17, DAS, surrender)
- **Col 3** : max splits, BJ payout, stratégie (Basic / Advanced), checkbox variance

Après le clic "▶ Run Simulation" :
1. Crée `SimConfig` avec `track_history=True` et `track_hand_outcomes=True`
2. `history_interval = max(1, hands // 2000)` → toujours ≤ 2000 points sur le graphe
3. Lance `simulate()` avec `st.spinner`
4. Affiche les résultats en sections :

```
Section 1 - Key Metrics     : 2 lignes de 5 métriques (EV + bankroll)
Section 2 - Bankroll        : courbe temporelle, zones colorées, peak/low
Section 3 - TC Analysis     : barres EV par bucket TC (expander)
Section 4 - Distribution    : histogramme profits par main (expander)
Section 5 - Variance        : 5 simulations seeds fixes (si checkbox cochée)
Section 6 - Hand Breakdown  : tableau wins/losses/pushes (expander)
Section 7 - Config Recap    : résumé texte de la simulation (expander)
```

**Variance Analysis (5 seeds)** :
- Seeds fixes : `[42, 123, 456, 789, 1337]`
- Barre de progression Streamlit en temps réel
- Multi-line chart avec zone de confiance min/max (alpha 0.07)
- Mini-tableau : seed, bankroll finale, peak, low, P&L + ligne moyenne

**Helpers graphes** (définis au niveau module) :
- `_dark_fig(w, h)` → figure + axes avec fond `#1a1a2e`
- `_eur(x)` → formateur `f"{x:,.0f} €"`
- Constantes `_BG`, `_GRID`, `_TEXT`

### Page 2 - EV Playground

Calcule l'EV de chaque action possible pour une main précise à un TC cible.

```
Interface :
  Presets de mains (16 vs 10, 11 vs As, etc.) + saisie manuelle
  Clic sur une carte → ouvre le rank picker
  TC cible, règles de table

Moteur de calcul :
  _build_shoe(target_tc, num_decks, rules) → list[Card]
    → sabot biaisé : ajuste la proportion low/high cards
      pour atteindre le TC cible
  _simulate_ev(action, hand_ranks, dealer_rank, shoe, rules, n)
    → simule n mains avec l'action imposée au premier coup
    → retourne EV moyen ± IC 95%

Actions évaluées : H, S, D, Ds, Y, SUR, INS (si As upcard)
Affichage : tableau trié par EV, meilleure action mise en évidence
```

---

## Partie 3 - Jeu React (`react/blackjack.jsx`)

Fichier unique (~2 400 lignes). Pas de composants séparés, pas de store externe.

### Architecture du fichier

```
1. Imports React + images
2. Constantes globales
   ├── DEFAULT_CONFIG       → règles de table par défaut
   ├── SUITS, RANKS, VALUES → définition des cartes
   ├── CHIPS                → valeurs et couleurs des jetons
   └── UPCARD_ORDER         → ordre d'indexation des tables
3. Logique de jeu pure (fonctions hors composant)
   ├── buildDeck(n), shuffle()
   ├── handValue(), isSoft(), isBlackjack(), isBust()
   ├── canDouble(), canSplit(), canSurr()
   ├── hiLo(), roundHalf(), calcTC()
   ├── Tables _H, _SOFT, _SPLIT → basic strategy
   ├── I18[]                → Illustrious 18 (même liste que deviations.py)
   ├── basicHint(), deviationHint(), getHint()
   └── buildChipsFromAmount()
4. Sous-composants React
   ├── SVGCard              → rendu d'une carte (face ou dos)
   ├── HandDisplay          → main + total + badge résultat
   ├── HintBox              → ancien composant (remplacé par rendu inline)
   ├── CoveredPanel         → panneau avec blur overlay révélable
   ├── Counter              → affichage RC + TC
   ├── ChipSVG              → jeton SVG cliquable
   ├── ShoeVisual           → sabot 3D avec jauge
   ├── DiscardTray          → pile de défausse
   └── ActionBtn            → bouton d'action (Hit, Stand, etc.)
5. Composant App (état + handlers + JSX)
```

### Phases du jeu

```
'betting'
    │
    ├─ si dealer upcard = As → 'insurance'
    │       │
    │       └──────────────────────┐
    │                              │
    └─────────────────────→ 'playing'
                                   │
                              'revealing'  (animation dealer)
                                   │
                                 'result'
                                   │
                              (New Bet) → 'betting'
```

### État du composant

```javascript
// Sabot
shoe, shoeIdx, rc              // cartes, index courant, running count

// Mains en cours
playerHands[]                  // tableau de mains (splits)
activeIdx                      // index de la main active
dealerCards[]
isSplitGame                    // true si au moins un split a eu lieu
surrendered[]                  // indices des mains surrenderées
preHandResults[]               // BJ resolus avant le jeu (joueur/dealer BJ)

// Bankroll
bankroll, bets[]               // bankroll et mises par main

// Spots de mise (dynamiques, 1 à 6)
handBetChips[][]               // chips par spot
lastHandBetChips[][]           // pour la fonction "Repeat"
spotIds[]                      // IDs stables pour les clés React (animations)
nextSpotId, selectedBetHand
hoveredSpot, removingSpotId

// Phase & animation
phase, revealCount, pendingResult

// Résultats
resultMsg, delta, handResults[]
insHandIdx, insDecisions[]

// Session stats
sessionHands, sessionWins, sessionDelta
sessionMistakes, sessionDecisions

// Config & overlays
gameConfig                     // toutes les règles de table (DEFAULT_CONFIG)
showSettings, editConfig       // modal paramètres
showBSOverlay, showI18Overlay  // overlays strategy/I18
bsHov, i18Hov                  // hover état des boutons

// UI
showHint, showHiLo
showShuffle, showRoundDelta
editingBankroll, bankrollInput
chipUsage, discardCount, dealRoundKey, dealDelays
```

### Dérivés calculés au render

```javascript
decksLeft = (shoe.length - shoeIdx) / 52
tc        = useMemo(() => calcTC(rc, decksLeft))
activeHand = playerHands[activeIdx] ?? []
upcard     = dealerCards[1] ?? null   // index 1 = upcard visible

handBetAmounts = handBetChips.map(sum)
numSpots       = spotIds.length
activeSlots    = spots avec mise > 0
canDeal        = au moins 1 slot actif ET bankroll suffisante

// Avant le useMemo hint (éviter TDZ)
playing = phase === 'playing'
canSur  = playing && canSurr(activeHand, isSplitGame) && gameConfig.lateSurrender

hint = useMemo(...)   // getHint + fallbacks SUR→H et D→H/S
  // Fallback SUR  : si hint=SUR mais !canSur → action='H'
  // Fallback D/Ds : si hint=D/Ds mais main > 2 cartes → H ou S

canDbl = playing && canDoubleHand(activeHand) && (DAS ou pas split) && bankroll ok
canSpl = playing && canSplit(activeHand) && < maxSplitHands && bankroll ok
```

### draw() - gestion du sabot

```javascript
function draw(shoe, idx, rc) {
  if (idx >= floor(shoe.length * gameConfig.penetration)) {
    shoe = shuffle(buildDeck(gameConfig.numDecks))
    idx = 0; rc = 0
  }
  return { card: shoe[idx], shoe, idx: idx+1, rcBefore: rc }
}
```
Le running count `rcBefore` est retourné pour que l'appelant puisse
mettre à jour `rc` avec `hiLo(card)` au bon moment (hole card comptée
à la révélation, pas à la donne).

### Spots dynamiques (betting zone)

```
handBetChips : tableau de N tableaux de chips (1 ≤ N ≤ 6)
spotIds      : IDs stables parallèles à handBetChips
               → clés React stables pour les animations CSS

addSpot(side)    : insère un spot gauche ou droite
removeSpot(si)   : retire un spot vide (animation spotOut → timeout 200ms)
clearAllBets()   : remet toutes les mises à zéro
doNewBets()      : après résultat, reset à 1 spot

CSS keyframes : spotIn, spotOut, fadeInFast, plusFadeOut, card-deal,
                card-flip, card-breathe, bj-glow, badgePop
```

### Configuration de table (`gameConfig`)

```javascript
DEFAULT_CONFIG = {
  bjPayout:          1.5,     // 3:2 ou 6:5 (1.2)
  dealerHitsSoft17:  false,   // H17 ou S17
  lateSurrender:     true,
  doubleRestriction: 'any',   // 'any' | '9-11' | '10-11'
  doubleAfterSplit:  true,
  maxSplitHands:     4,       // 2, 3 ou 4
  resplitAces:       false,
  numDecks:          6,
  penetration:       0.75,
}
```
Modifiable via le modal ⚙. `applyAndReset(cfg)` applique et recrée
le sabot entier, remet la session à zéro.

---

## Règles métier critiques (ne jamais casser)

| Règle | Où |
|---|---|
| True count = RC / decks restants, arrondi à 0.5 | `counting.py`, `blackjack.jsx` |
| Hole card comptée à la révélation | `simulator.py`, `blackjack.jsx` |
| I18 "Stand" ne remplace jamais SUR | `simulator.py::_pick_action`, `blackjack.jsx::hint` |
| Liste I18 = exactement 18 entrées | `deviations.py`, `blackjack.jsx::I18[]` |
| Tables basic strategy = source WoO 6D S17 DAS LS | `strategy.py`, `blackjack.jsx` |

---

## Lancer l'application

```bash
# Jeu interactif (React - ouvrir directement dans le navigateur)
react/dist/index.html

# Rebuild si modification de blackjack.jsx
cd react && npm run build

# EV Lab (Streamlit)
streamlit run app_simulation.py

# Tests
python -m pytest tests/ -v           # 334 tests

# Vérifications intégrité
python simulation/strategy.py --verify
python simulation/deviations.py --verify
```
