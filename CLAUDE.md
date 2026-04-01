# Blackjack Trainer Pro - CLAUDE.md

## Vision du projet
Application solo d'entraînement et de simulation au blackjack.
Deux applications indépendantes sur un moteur de jeu Python partagé :
- **Interactive Game** : React, jouer contre un dealer avec hints en temps réel
- **EV Lab** : Streamlit, Monte Carlo + EV Playground par action

Public : usage personnel. Apprentissage basic strategy, deviations I18, comptage Hi-Lo.
**Priorité absolue : exactitude mathématique > esthétique.**

---

## État actuel - tout est implémenté

### Moteur Python (`simulation/`)
- `engine.py` - sabot 6 decks, deal, hit, stand, double, split, surrender, blackjack
- `strategy.py` - tables basic strategy complètes hard/soft/split (source : Wizard of Odds)
- `counting.py` - Hi-Lo running count + true count (arrondi à 0.5)
- `deviations.py` - Illustrious 18 canonique (Schlesinger), 18 entrées exactement
- `betting.py` - bet ramp, spread → mise selon TC
- `simulator.py` - Monte Carlo avec basic strategy ou Basic + I18 deviations
- `config.py` - dataclasses SimConfig, TableRules, BettingConfig, SimulationResult

### Interface React (`react/blackjack.jsx`)
- Jeu complet : hit, stand, double, split (×4), surrender, multi-main (1–3)
- Phase insurance quand dealer montre un As
- Hint panel dans le header (à gauche du Hi-Lo counter) : Best Play ou ★ I18 Deviation
- Hi-Lo counter live (running count + true count)
- Bankroll + mise ajustable

### EV Lab Streamlit (`app_simulation.py`)
- **Monte Carlo Simulator** : Basic Strategy OU Advanced (Basic + I18), graphes matplotlib
- **EV Playground** : EV par action pour une main précise au TC donné, sabot biaisé Monte Carlo

### Tests (`tests/`)
- 334 tests, tous passent - `python -m pytest tests/ -v`

---

## Stack & architecture

- **Game UI** : React 18 / JSX, fichier unique `blackjack.jsx`, Tailwind CSS
- **EV Lab** : Streamlit + matplotlib + pandas + numpy
- **Moteur** : Python 3.11+, dataclasses, typing strict
- **Pas de** : framework backend, base de données, npm tiers

---

## Structure des fichiers
```
├── app_simulation.py          # Streamlit EV Lab
├── react/
│   ├── blackjack.jsx          # App jeu complète (un seul fichier)
│   └── dist/                  # Build statique - ouvrir dist/index.html
├── simulation/
│   ├── engine.py
│   ├── counting.py
│   ├── strategy.py
│   ├── deviations.py
│   ├── betting.py
│   ├── simulator.py
│   └── config.py
├── tests/
│   ├── test_engine.py
│   ├── test_strategy.py
│   ├── test_counting.py
│   ├── test_deviations.py
│   └── test_simulator.py
└── docs/references/           # Captures strategy chart + I18 table
```

---

## Règles métier critiques - NE JAMAIS CASSER

### Calculs fondamentaux
- **True count** = running count / decks restants, arrondi à 0.5 (pas floor, pas int)
- **Pénétration** : mélange après 75% du sabot écoulé
- **Blackjack** : paie 3:2 (configurable)
- **Dealer** : stands on soft 17 (S17 par défaut)
- **Sabot** : 6 decks par défaut

### Basic strategy
- Source vérifiée : https://wizardofodds.com/games/blackjack/strategy/6-decks/
- Tables hard (5–21) / soft (A2–A9) / split (2–A) - **ne jamais modifier sans source**
- Y/N = split uniquement si DAS autorisé

### Illustrious 18 - liste canonique
Source : Don Schlesinger, *Blackjack Attack*. La liste doit contenir **exactement 18 entrées** :
- 1 insurance (hand_type="insurance")
- 2 pair splits : 10,10 vs 5 (TC≥+5), 10,10 vs 6 (TC≥+4)
- 15 hard deviations

**Entrées non canoniques** (à ne jamais rajouter) : "14 vs 10 TC≥3" et "15 vs 9 TC≥2" - elles avaient été incluses par erreur et ont été retirées.

### Règle SUR → Stand (BUG DÉJÀ CORRIGÉ)
Les déviations I18 "Stand" (ex. 16 vs 10 à TC≥0) ont été calibrées pour des jeux **sans surrender**. Dans un jeu avec surrender, SUR (EV ≈ −0.500) est meilleur que Stand (EV ≈ −0.543) jusqu'à TC ≈ +5.
**La règle : on ne remplace JAMAIS SUR par Stand via une déviation I18.**
Implémenté dans `simulator.py::_pick_action()` et dans `deviationHint()` dans React.

### Hi-Lo counting
- +1 : 2–6 / 0 : 7–9 / −1 : 10–A
- Running count remis à 0 à chaque nouveau sabot
- True count = running / decks restants (pas decks joués)
- Hole card du dealer comptée à la révélation (pas à la donne)

### Insurance
- Décision séparée de la main (phase 'insurance' dans React, avant de jouer)
- I18 : prendre si TC ≥ +3 (dealer montre As)
- Paye 2:1 sur la mise d'assurance (= moitié de la mise principale)
- Dans le simulateur : uniquement en mode `use_deviations=True`

---

## Architecture React - points clés

### Phases du jeu
```
'betting' → 'insurance' (si upcard=As) → 'playing' → 'revealing' → 'result'
                                        ↗ (si pas d'As)
```
- `'insurance'` : hole card cachée (`hideFirst=true`), boutons Take/No Thanks
- `'revealing'` : animation dealer + pendingResult appliqué via useEffect
- `preHandResults[]` : mains résolues avant le jeu (BJ joueur/dealer)

### State minimal - règles
- Ne stocker dans le state que ce qui déclenche un re-render
- `insuranceTaken`/`insuranceBet` : utilisés uniquement comme relay dans les handlers, pas lus dans le rendu - c'est intentionnel

### Hint panel
- Positionné dans le **header, à gauche du Hi-Lo counter**
- Affiché uniquement pendant `phase === 'playing'` ou `phase === 'insurance'`
- Insurance : montre "TC+X ≥ +3 → Take Insurance" ou "TC-X < +3 → No Insurance"
- Jeu : montre Best Play (basic) ou ★ I18 Deviation

### I18 dans React (`blackjack.jsx`)
Le tableau `I18[]` dans React doit rester synchronisé avec `deviations.py`.
Chaque entrée a un flag `pair: true/false`. La fonction `deviationHint()` :
- Skip les mains soft
- Filtre `d.pair !== isPair` pour éviter d'appliquer les hard deviations sur les paires
- Protège SUR → jamais remplacé par Stand

---

## Architecture Python - points clés

### Responsabilités des fichiers
- `engine.py` : moteur pur, **zéro stratégie**, zéro counting
- `strategy.py` : tables only, fonctions pures
- `deviations.py` : I18 only, `get_deviation()` + `should_take_insurance()`
- `simulator.py` : boucle Monte Carlo, appelle tout le reste
- `config.py` : dataclasses de configuration, **zéro logique de jeu**

### Ordre de comptage dans le simulateur
```
P1 visible → D1/upcard visible → P2 visible → D2/hole (pas compté)
→ insurance check (si As upcard)
→ player joue
→ D2 compté à la révélation
→ dealer joue
```

### EV Playground - `_simulate_ev()`
Le sabot est biaisé (`_build_shoe()`) pour approcher le TC cible en ajustant
la composition des cartes restantes. Chaque action est simulée indépendamment
sur le même TC et les mêmes règles.

Pour `action == 'INS'` : EV normalisé à la mise principale = +0.5 si dealer BJ, −0.5 sinon.

---

## Règles de code Python

- Typage strict : dataclasses + typing partout, pas de `Any`
- Fonctions pures autant que possible, pas d'effets de bord cachés
- Une responsabilité par fichier
- Tests unitaires pour toute logique strategy / counting / deviations
- Ne jamais réécrire `engine.py` sans que tous les tests passent avant et après

## Règles de code React

- Composants fonctionnels uniquement, pas de classes
- Hooks natifs uniquement (useState, useEffect, useCallback, useMemo)
- Zéro lib externe sauf Tailwind
- Logique de jeu séparée du rendu (fonctions pures hors composants)
- State minimal : ne stocker que ce qui doit déclencher un re-render
- L'UI est entièrement en **anglais** (labels, messages, hints)
- Les commentaires de code restent en **français**

---

## Interdictions

- Ne jamais modifier les tables de strategy sans source vérifiée (WoO)
- Ne jamais modifier la liste I18 sans vérifier la source (Schlesinger)
- Ne jamais rajouter "14 vs 10 TC≥3" ou "15 vs 9 TC≥2" dans I18 - non canoniques
- Ne jamais laisser une déviation I18 "Stand" remplacer SUR
- Ne pas mélanger logique métier et composants React
- Ne pas ajouter de dépendances npm sans demander
- Ne pas réécrire engine.py sans que les tests passent avant et après

---

## Workflow de validation

Après tout changement Python :
```bash
python -m pytest tests/ -v
```

Après tout changement strategy ou deviations :
```bash
python simulation/strategy.py --verify
python simulation/deviations.py --verify
```

**Claude ne considère jamais une tâche terminée si les tests ne passent pas.**

---

## Commandes utiles
```bash
# Tests complets
python -m pytest tests/ -v

# EV Lab (Streamlit)
streamlit run app_simulation.py

# Simulation CLI rapide
python -m simulation.simulator --hands 100000 --spread 1-12 --unit-size 25

# Simulation avancée avec I18
python -m simulation.simulator --hands 500000 --spread 1-12 --unit-size 25
# (use_deviations s'active via SimConfig, pas encore exposé en CLI)

# Vérifications
python simulation/strategy.py --verify
python simulation/deviations.py --verify
python simulation/counting.py --debug
```

---

## Ce que Claude doit faire avant chaque tâche

1. Lire ce fichier en entier
2. Identifier le(s) fichier(s) concerné(s)
3. Lire les fichiers concernés (ne pas supposer leur contenu)
4. Vérifier que les tests passent : `python -m pytest tests/ -v`
5. Implémenter
6. Relancer les tests
7. Signaler tout écart avec les règles métier ci-dessus
8. Commit avec un message détaillé si demandé

## Pièges à éviter (appris en session)

- **I18 et surrender** : toujours vérifier que la déviation ne remplace pas SUR par Stand
- **Penetration slider Streamlit** : utiliser un slider int (50–95) + division `/100`, pas float (cause affichage "1%")
- **st.toggle()** : remplacer par `st.checkbox()` si les boutons ronds ne sont pas voulus
- **Phase insurance React** : `hideFirst` doit inclure `phase === 'insurance'` sinon la hole card est visible
- **Synchronisation React ↔ Python** : le tableau I18 dans `blackjack.jsx` doit rester identique à `deviations.py` - vérifier les deux à chaque modification I18
