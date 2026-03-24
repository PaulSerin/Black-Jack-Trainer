# Blackjack Trainer Pro — CLAUDE.md

## Vision du projet
Application solo d'entraînement et de simulation au blackjack.
Deux modes principaux sur un moteur de jeu partagé :
- **Mode Interactif** : jouer contre un dealer avec hints en temps réel
- **Mode Simulation** : Monte Carlo avec paramètres configurables

Public : usage personnel, apprentissage de la basic strategy,
des deviations (Illustrious 18, Fab 4) et du comptage Hi-Lo.
Priorité absolue : exactitude mathématique > esthétique.

---

## Stack & architecture

- **Interface** : React/JSX, fichier unique, Tailwind CSS uniquement
- **Moteur** : Python 3.11+, dataclasses, typing
- **Visualisation** : matplotlib (simulations uniquement)
- **Pas de** : framework backend, base de données, dépendances npm tierces

---

## Structure des fichiers
```
blackjack/
├── CLAUDE.md
├── react/
│   └── blackjack.jsx          # App complète en un fichier
├── simulation/
│   ├── engine.py              # Moteur de jeu pur (partagé)
│   ├── counting.py            # Hi-Lo, running count, true count
│   ├── strategy.py            # Basic strategy complète hard/soft/split
│   ├── deviations.py          # Illustrious 18, Fab 4, index plays
│   ├── betting.py             # Bet spread, bankroll management
│   └── simulator.py           # Monte Carlo, stats longterme
└── tests/
    ├── test_engine.py
    ├── test_strategy.py
    ├── test_counting.py
    └── test_deviations.py
```

---

## Fonctionnalités cibles (roadmap)

### Phase 1 — Moteur de base
- [ ] engine.py : sabot 6 decks, deal, hit, stand, double, split
- [ ] strategy.py : tables basic strategy hard/soft/split complètes
- [ ] counting.py : Hi-Lo running count + true count
- [ ] Tests unitaires strategy et counting

### Phase 2 — Interface React
- [ ] Mode jeu interactif contre dealer
- [ ] Affichage hint basic strategy en temps réel
- [ ] Compteur Hi-Lo visible (running + true count)
- [ ] Gestion bankroll : mise personnalisée, solde

### Phase 3 — Deviations
- [ ] deviations.py : Illustrious 18 + Fab 4
- [ ] Hints avec deviations si TC le justifie (priment sur basic strategy)
- [ ] Indication visuelle quand une deviation s'applique

### Phase 4 — Simulation
- [ ] simulator.py : Monte Carlo configurable
- [ ] Paramètres : bet spread, pénétration, nombre de mains, bankroll
- [ ] Sorties : EV, risk of ruin, graphes matplotlib

### Paramètres de jeu configurables
- Nombre de decks (défaut : 6)
- Dealer hits/stands soft 17 (défaut : stands)
- Pénétration (défaut : 75%)
- Blackjack payout (défaut : 3:2)
- Bet spread (défaut : 1-12)

---

## Règles de code Python

- Typage strict : dataclasses + typing partout
- Fonctions pures autant que possible, pas d'effets de bord cachés
- Une responsabilité par fichier (engine ≠ strategy ≠ counting)
- Tests unitaires pour toute logique strategy/counting/deviations
- Pas de `Any` sauf justification explicite

## Règles de code React

- Composants fonctionnels uniquement, pas de classes
- Hooks natifs uniquement (useState, useEffect, useCallback, useMemo)
- Zéro lib externe sauf Tailwind
- Logique de jeu séparée du rendu (fonctions pures hors composants)
- State minimal : ne stocker que ce qui doit déclencher un re-render

---

## Règles métier critiques — NE JAMAIS CASSER

### Calculs fondamentaux
- **True count** = running count / decks restants (arrondi à 0.5, pas de floor)
- **Pénétration** : mélange après 75% du sabot écoulé
- **Blackjack** : paie 3:2
- **Dealer** : stands on soft 17
- **Sabot** : 6 decks

### Basic strategy
- Table complète hard (5-21) / soft (A2-A9) / split (2-A)
- Source de référence : https://wizardofodds.com/games/blackjack/strategy/6-decks/
- Ne jamais modifier sans source vérifiée

### Deviations (quand implémentées)
- Les deviations Illustrious 18 priment sur basic strategy si TC le justifie
- Chaque deviation a un index (TC seuil) — ne pas hardcoder sans vérification
- Fab 4 surrenders à intégrer en Phase 3
- Source : "Blackjack Attack" de Don Schlesinger

### Hi-Lo counting
- +1 : 2-6 / 0 : 7-9 / -1 : 10-A
- Running count remis à 0 à chaque nouveau sabot
- True count = running / decks restants estimés (pas decks joués)

---

## Interdictions

- Ne jamais réécrire engine.py sans que tous les tests passent avant et après
- Ne pas mélanger logique métier et composants React
- Ne pas ajouter de dépendances npm sans demander
- Ne pas modifier les tables de strategy sans source vérifiée
- Ne pas implémenter les deviations avant que basic strategy soit 100% testée

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

Claude ne considère jamais une tâche terminée si les tests ne passent pas.

---

## Commandes utiles
```bash
# Tests complets
python -m pytest tests/ -v

# Vérification strategy
python simulation/strategy.py --verify

# Lancer une simulation rapide
python simulation/simulator.py --hands 100000 --spread 1-12

# Vérifier le true count sur une séquence
python simulation/counting.py --debug
```

---

## Ce que Claude doit faire avant chaque tâche

1. Lire ce fichier
2. Identifier le fichier concerné et sa phase
3. Vérifier que les tests existants passent
4. Implémenter
5. Relancer les tests
6. Signaler tout écart avec les règles métier ci-dessus