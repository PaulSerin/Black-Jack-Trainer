# Blackjack - Règles & Glossaire

## Table des matières
1. [Objectif du jeu](#objectif)
2. [Déroulement d'une main](#deroulement)
3. [Actions du joueur](#actions)
4. [Règles du dealer](#dealer)
5. [Payouts](#payouts)
6. [Glossaire complet](#glossaire)

---

## 1. Objectif du jeu <a name="objectif"></a>

Battre le dealer en ayant une main dont la valeur est **plus proche de 21** sans la dépasser.
- Si le joueur dépasse 21 → **bust** → perd immédiatement
- Si le dealer dépasse 21 → **bust** → le joueur gagne
- Égalité → **push** → la mise est rendue

### Valeur des cartes
| Cartes | Valeur |
|--------|--------|
| 2 – 10 | Valeur nominale |
| J, Q, K | 10 |
| As (Ace) | 1 **ou** 11 (au choix, optimal automatiquement) |

---

## 2. Déroulement d'une main <a name="deroulement"></a>

1. Le joueur place sa mise (**bet**)
2. Le dealer distribue **2 cartes à chacun** : joueur face visible, dealer 1 visible (**upcard**) + 1 cachée (**hole card**)
3. Si l'upcard est un As → phase **insurance** proposée
4. Si le dealer a un **blackjack** naturel → révélation immédiate, main terminée
5. Le joueur joue ses actions (hit, stand, double, split, surrender)
6. Le dealer révèle sa hole card et joue selon ses règles fixes
7. Comparaison des mains, paiements

---

## 3. Actions du joueur <a name="actions"></a>

### Hit (H)
Tirer une carte supplémentaire. Peut être répété autant de fois que souhaité tant que la main ne bust pas.

### Stand (S)
Ne pas tirer de carte. Passer la main au dealer.

### Double Down (D)
Doubler sa mise initiale en échange d'**une seule carte supplémentaire**, puis stand obligatoire.
- Disponible uniquement sur les 2 premières cartes (en règle générale)
- **Ds** (Double or Stand) : indique qu'on double si possible, sinon on stand

### Split (Y)
Lorsqu'on a une paire (deux cartes de même valeur), séparer en **deux mains indépendantes**, chacune avec une mise égale à la mise initiale. On joue ensuite chaque main séparément.
- **Y/N** : Split uniquement si DAS autorisé, sinon Ne pas split

### Surrender (SUR)
Abandonner la main et récupérer **la moitié** de sa mise. Disponible avant toute autre action (early surrender) ou après la donne initiale (late surrender).
- **Late Surrender (LS)** : forme la plus courante, après que le dealer a vérifié son blackjack

### Insurance
Lorsque l'upcard du dealer est un As, le joueur peut miser jusqu'à la **moitié de sa mise principale** sur le fait que le dealer a un blackjack.
- Paye **2:1** si le dealer a effectivement un blackjack
- EV négatif en basic strategy - rentable uniquement si **TC ≥ +3** (I18)

---

## 4. Règles du dealer <a name="dealer"></a>

Le dealer n'a **aucun choix** : il suit des règles fixes.

### S17 - Stand on Soft 17 (règle favorable au joueur)
Le dealer **s'arrête** sur tout 17, y compris les 17 soft (As + 6).
→ Standard dans la plupart des casinos européens et dans cette app.

### H17 - Hit on Soft 17 (règle défavorable au joueur)
Le dealer **tire** sur les 17 soft uniquement. Augmente le house edge d'environ **+0.20%**.

### Règle générale
- Dealer tire sur 16 ou moins
- Dealer s'arrête sur 18, 19, 20, 21
- Dealer bust → tous les joueurs encore en jeu gagnent

---

## 5. Payouts <a name="payouts"></a>

| Situation | Paiement |
|-----------|----------|
| Victoire classique | 1:1 (misez 10 → gagnez 10) |
| Blackjack naturel - 3:2 | 1.5:1 (misez 10 → gagnez 15) |
| Blackjack naturel - 6:5 | 1.2:1 (misez 10 → gagnez 12) |
| Insurance gagnée | 2:1 |
| Push (égalité) | Remboursement de la mise |
| Surrender | Récupère 50% de la mise |

> La règle **3:2** est fortement préférable à **6:5** : la différence représente environ **+1.4%** de house edge supplémentaire en 6:5.

---

## 6. Glossaire complet <a name="glossaire"></a>

---

### A

**Ace (As)**
Carte valant 1 ou 11 selon ce qui est optimal pour la main. Un As comptant 11 forme une **main soft**.

**Advantage (Avantage joueur)**
Pourcentage d'espérance de gain du joueur sur le casino. En basic strategy sur un sabot 6 decks S17, l'avantage casino est d'environ **−0.44%** (house edge). Le comptage de cartes peut inverser cet avantage.

---

### B

**Bankroll**
Capital total dont dispose le joueur. La gestion de la bankroll (bet sizing) est essentielle pour survivre à la variance à court terme.

**Basic Strategy (BS)**
Ensemble des décisions optimales (hit/stand/double/split/surrender) pour chaque combinaison main du joueur × upcard du dealer, calculées par simulation Monte Carlo et mathématiques exactes. Minimise le house edge à son minimum théorique. Source de référence : [Wizard of Odds](https://wizardofodds.com/games/blackjack/strategy/6-decks/).

**Bet (Mise)**
Montant misé sur une main avant la donne.

**Bet Ramp**
Échelle de mises selon le true count. Exemple : TC ≤ 1 → 1 unité, TC 2 → 2 unités, TC 3 → 4 unités, TC 4 → 8 unités, TC ≥ 5 → 12 unités.

**Bet Spread**
Ratio entre la **mise maximale** et la **mise minimale** utilisées par le compteur. Un spread 1–12 signifie que la mise max est 12× la mise min. Plus le spread est élevé, plus le gain espéré est important - mais plus la détection par le casino est risquée.

**Blackjack (naturel)**
Main composée d'un As + une carte de valeur 10 (10, J, Q, K) sur les deux premières cartes. Bat toute main ordinaire à 21. Paye 3:2 (ou 6:5 selon les règles).

**Burn card**
Première carte du sabot, retirée face cachée avant le début du jeu. Ne compte pas dans le running count.

**Bust**
Dépasser 21. La main perd immédiatement.

---

### C

**Camouflage**
Technique des compteurs pour masquer leur activité au casino : varier les mises de façon irrégulière, faire semblant d'hésiter, jouer des écarts de basic strategy "délibérément", etc.

**Card Counting (Comptage de cartes)**
Technique légale consistant à suivre mentalement la composition du sabot restant pour détecter les moments favorables (riches en hautes cartes) et adapter sa mise en conséquence.

**Cover play**
Action stratégiquement incorrecte jouée volontairement pour ne pas paraître comme un compteur.

**Cut card**
Carte plastique placée dans le sabot pour indiquer la profondeur de pénétration. Quand elle sort, le sabot est mélangé après la main en cours.

---

### D

**DAS - Double After Split**
Règle autorisant le joueur à doubler la mise sur une main obtenue après un split. Favorable au joueur (+0.14% environ). Affecte la stratégie de split : certains splits ne sont rentables qu'avec DAS.

**Dead hand**
Main dont l'issue est déjà connue avant que le dealer joue (ex. bust du joueur, blackjack).

**Deck (Deck)**
Paquet de 52 cartes standard. Le blackjack se joue généralement avec 1, 2, 4, 6 ou 8 decks.

**Dealer**
Le croupier. Représente la maison (casino). Joue selon des règles fixes sans décision.

**Deviations (Déviations)**
Écarts par rapport à la basic strategy justifiés par le true count. Voir **Illustrious 18**.

**Double Down** → voir [Actions](#actions)

---

### E

**Edge (Avantage)**
Voir *Advantage*.

**EV - Expected Value (Espérance de gain)**
Gain moyen espéré sur le long terme pour une action donnée, exprimé en fraction de la mise. EV = +0.05 signifie qu'on gagne en moyenne 5% de la mise. L'objectif est de **maximiser l'EV** à chaque décision.

**Even money**
Lorsque le joueur a un blackjack et que le dealer montre un As, le casino propose de payer 1:1 immédiatement plutôt que de risquer un push contre le blackjack du dealer. Équivalent mathématique à prendre l'insurance sur un BJ - défavorable en basic strategy (EV identique).

---

### F

**Flat bet**
Miser toujours la même somme à chaque main, sans adapter selon le count. Résulte en un EV légèrement négatif (house edge) sur le long terme.

**Frenetic / Favorable shoe**
Sabot dont la composition restante est favorable au joueur (riche en hautes cartes, TC élevé).

---

### H

**Hand**
La main du joueur ou du dealer. Ensemble des cartes reçues sur un round.

**Hard hand (Main hard / dure)**
Main ne contenant **pas d'As**, ou un As forcément compté à 1 (car compter 11 ferait bust). Exemple : 10 + 7 = hard 17.

**Hi-Lo**
Système de comptage de cartes le plus répandu, proposé par Harvey Dubner (1963) et popularisé par Stanford Wong. Chaque carte reçoit un tag :
- **+1** : 2, 3, 4, 5, 6 (basses cartes - défavorables au joueur)
- **0** : 7, 8, 9 (neutres)
- **−1** : 10, J, Q, K, As (hautes cartes - favorables au joueur)

**Hit** → voir [Actions](#actions)

**Hole card**
La carte cachée du dealer, distribuée face cachée. Révélée uniquement quand le joueur a terminé de jouer.

**House edge**
Avantage mathématique du casino, exprimé en pourcentage de la mise. En blackjack 6 decks S17 avec basic strategy parfaite ≈ **0.44%**. Le comptage de cartes vise à annuler ou inverser cet avantage.

---

### I

**I18 - Illustrious 18**
Les 18 déviations à la basic strategy les plus importantes en termes de gain espéré, identifiées par Don Schlesinger dans *Blackjack Attack*. Apprendre ces 18 déviations capture l'essentiel du gain possible par les déviations. Exemples : Insurance TC≥3, 16 vs 10 TC≥0 stand, 15 vs 10 TC≥4 stand.

**Index (Indice)**
Valeur de TC à partir de laquelle une déviation devient rentable. Exemple : "16 vs 10, index 0" signifie qu'on stand si TC ≥ 0 au lieu de hit (basic strategy).

**Insurance** → voir [Actions](#actions)

---

### M

**Main soft** → voir *Soft hand*

**Monte Carlo simulation**
Méthode de simulation statistique consistant à jouer des millions de mains virtuelles pour estimer l'EV, la variance, et les performances d'une stratégie. Plus fiable que le calcul analytique pour les situations complexes (splits, déviations).

---

### N

**Natural** → voir *Blackjack*

**NRSA - No Resplit Aces**
Règle interdisant de re-splitter les As. Standard dans la plupart des casinos.

---

### P

**Pair**
Deux cartes de même valeur (ex. 8-8, A-A, 10-K). Peut être splitée.

**Penetration (Pénétration)**
Pourcentage du sabot distribué avant de mélanger. Une pénétration de 75% signifie que 75% des cartes sont jouées avant le shuffle. **Plus la pénétration est élevée, plus le comptage est efficace** (le TC est plus fiable).

**Push**
Égalité entre le joueur et le dealer. La mise est rendue sans gain ni perte.

---

### R

**RC - Running Count (Comptage courant)**
Somme cumulative des tags Hi-Lo depuis le dernier shuffle. Reflète la composition absolue des cartes sorties mais **ne tient pas compte du nombre de decks restants**.

**Résplit**
Splitter une paire déjà obtenue par un premier split. Ex : split 8-8, puis recevoir un 8 sur l'une des mains → resplit possible (si autorisé).

**RFB (Règle Favorable au Backcount)**
Voir *Wong Halves*, *Back counting*.

---

### S

**S17** → voir [Règles du dealer](#dealer)

**Sabot (Shoe)**
Boîtier contenant plusieurs decks mélangés ensemble, depuis lequel le dealer tire les cartes. Standard : **6 decks**. Le sabot augmente la durée de jeu et rend le comptage plus difficile (TC moins volatile) mais reste exploitable.

**Schlesinger, Don**
Auteur de *Blackjack Attack*, référence canonique pour les Illustrious 18 et l'analyse quantitative du blackjack.

**Session**
Ensemble de mains jouées lors d'une seule période de jeu. Les statistiques de session (win rate, P&L, mistakes) permettent de suivre ses performances.

**Shoe** → voir *Sabot*

**Shuffle**
Mélange du sabot. Réinitialise le running count à 0. En conditions réelles, intervient après la pénétration cible (75% dans cette app).

**Soft hand (Main soft / souple)**
Main contenant un As compté à **11** sans risque de bust. Exemple : As + 6 = soft 17. La flexibilité de l'As rend ces mains moins risquées - d'où des règles de double-down plus agressives.

**Split** → voir [Actions](#actions)

**Spread** → voir *Bet Spread*

**Stand** → voir [Actions](#actions)

**Surrender** → voir [Actions](#actions)

---

### T

**TC - True Count (Comptage vrai)**
RC normalisé par le nombre de **decks restants** dans le sabot. Formule :

```
TC = RC / decks restants
```

Le TC est arrondi au 0.5 le plus proche dans cette app (convention professionnelle). C'est la mesure standard pour évaluer l'avantage joueur et déclencher les déviations.

**True count conversion**
Transformation du RC en TC. Essentielle car un RC de +6 avec 2 decks restants (TC +3) est très différent d'un RC de +6 avec 6 decks restants (TC +1).

---

### U

**Unit (Unité de mise)**
La mise minimale du joueur, utilisée comme référence pour le bet spread. Si l'unité est 25€ et le spread 1–12, la mise max est 300€.

**Upcard**
La carte visible du dealer (face up), connue du joueur avant sa décision. C'est la variable clé de la basic strategy.

---

### V

**Variance**
Mesure de la dispersion des résultats autour de la moyenne. À court terme, la variance au blackjack est élevée - même avec un avantage positif, on peut perdre sur plusieurs centaines de mains. Une grande bankroll est nécessaire pour survivre aux fluctuations.

---

### W

**Wizard of Odds**
Site de référence ([wizardofodds.com](https://wizardofodds.com)) tenu par Michael Shackleford, mathématicien spécialisé dans les jeux de casino. Source des tables de basic strategy utilisées dans cette app.

**Wong, Stanford**
Auteur de *Professional Blackjack*. À l'origine du *Wonging* (back counting) et d'analyses approfondies du comptage Hi-Lo.

**Wonging / Back counting**
Technique consistant à observer un sabot sans jouer (**back counter**) et n'entrer en jeu que lorsque le TC est favorable. Très efficace mais souvent interdit ou surveillé dans les casinos.

---

## Résumé des abréviations

| Abréviation | Signification |
|-------------|---------------|
| BS | Basic Strategy |
| BJ | Blackjack (naturel) |
| DAS | Double After Split |
| EV | Expected Value (espérance) |
| H | Hit |
| H17 | Dealer hits soft 17 |
| Hi-Lo | Système de comptage (tags +1/0/−1) |
| I18 | Illustrious 18 (déviations) |
| LS | Late Surrender |
| RC | Running Count |
| RFB | Règle Favorable au Backcount |
| S | Stand |
| S17 | Dealer stands on soft 17 |
| SUR | Surrender |
| TC | True Count |
| Y | Split (yes) |
| Y/N | Split seulement si DAS |

---

*Sources : Don Schlesinger - Blackjack Attack · Stanford Wong - Professional Blackjack · Michael Shackleford - Wizard of Odds*
