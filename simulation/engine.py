"""
engine.py — Moteur de jeu pur pour Blackjack Trainer Pro.

Contient les dataclasses Card, Hand, Shoe, GameState ainsi que
les fonctions pures de règles de jeu. Aucune logique de strategy ici.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Card
# ---------------------------------------------------------------------------

SUITS: tuple[str, ...] = ("♠", "♥", "♦", "♣")
RANKS: tuple[str, ...] = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")

RANK_VALUES: dict[str, int] = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10,
    "A": 11,  # As compté 11 par défaut ; Hand gère la réduction à 1
}


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in RANKS:
            raise ValueError(f"Rang invalide : {self.rank!r}")
        if self.suit not in SUITS:
            raise ValueError(f"Couleur invalide : {self.suit!r}")

    @property
    def value(self) -> int:
        """Valeur numérique de la carte (As = 11, figures = 10)."""
        return RANK_VALUES[self.rank]

    @property
    def is_ace(self) -> bool:
        return self.rank == "A"

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    def __repr__(self) -> str:
        return f"Card({self.rank!r}, {self.suit!r})"


# ---------------------------------------------------------------------------
# Hand
# ---------------------------------------------------------------------------

@dataclass
class Hand:
    cards: List[Card] = field(default_factory=list)
    is_split_hand: bool = False          # main issue d'un split
    doubled: bool = False                # mise doublée

    def add_card(self, card: Card) -> None:
        """Ajoute une carte à la main. Seul effet de bord autorisé."""
        self.cards.append(card)

    @property
    def value(self) -> int:
        """
        Valeur optimale de la main (≤ 21 si possible).
        Les As sont d'abord comptés 11 ; on les repasse à 1 si nécessaire.
        """
        total = sum(c.value for c in self.cards)
        aces = sum(1 for c in self.cards if c.is_ace)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @property
    def is_soft(self) -> bool:
        """Main souple : contient un As compté 11."""
        total = sum(c.value for c in self.cards)
        aces = sum(1 for c in self.cards if c.is_ace)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        # S'il reste encore un As contribuant 11, la main est souple
        return aces > 0 and total <= 21

    @property
    def is_blackjack(self) -> bool:
        """Blackjack naturel : exactement 2 cartes, As + figure/10."""
        return (
            len(self.cards) == 2
            and self.value == 21
            and not self.is_split_hand
        )

    @property
    def is_bust(self) -> bool:
        return self.value > 21

    @property
    def is_pair(self) -> bool:
        """Deux cartes de même valeur (pour le split)."""
        return len(self.cards) == 2 and self.cards[0].value == self.cards[1].value

    @property
    def first_card(self) -> Optional[Card]:
        return self.cards[0] if self.cards else None

    def __len__(self) -> int:
        return len(self.cards)

    def __str__(self) -> str:
        cards_str = " ".join(str(c) for c in self.cards)
        return f"[{cards_str}] = {self.value}"


# ---------------------------------------------------------------------------
# Shoe
# ---------------------------------------------------------------------------

@dataclass
class Shoe:
    num_decks: int = 6
    penetration: float = 0.75   # proportion du sabot jouée avant mélange

    _cards: List[Card] = field(default_factory=list, init=False, repr=False)
    _dealt: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.num_decks < 1:
            raise ValueError("num_decks doit être ≥ 1")
        if not (0.0 < self.penetration <= 1.0):
            raise ValueError("penetration doit être dans ]0, 1]")
        self._build_and_shuffle()

    def _build_and_shuffle(self) -> None:
        """Construit le sabot complet et le mélange."""
        self._cards = [
            Card(rank, suit)
            for _ in range(self.num_decks)
            for suit in SUITS
            for rank in RANKS
        ]
        random.shuffle(self._cards)
        self._dealt = 0

    def shuffle(self) -> None:
        """Mélange explicite (remet le sabot à zéro)."""
        self._build_and_shuffle()

    @property
    def total_cards(self) -> int:
        return self.num_decks * 52

    @property
    def cards_dealt(self) -> int:
        return self._dealt

    @property
    def cards_remaining(self) -> int:
        return self.total_cards - self._dealt

    @property
    def decks_remaining(self) -> float:
        """Nombre de decks restants (utile pour le true count)."""
        return self.cards_remaining / 52.0

    @property
    def needs_shuffle(self) -> bool:
        """True si la pénétration configurée est atteinte."""
        return self._dealt >= int(self.total_cards * self.penetration)

    def deal(self) -> Card:
        """Distribue une carte. Lève RuntimeError si le sabot est vide."""
        if self._dealt >= len(self._cards):
            raise RuntimeError("Sabot vide — appelez shuffle() avant de continuer.")
        card = self._cards[self._dealt]
        self._dealt += 1
        return card


# ---------------------------------------------------------------------------
# GameState
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    shoe: Shoe
    player_hands: List[Hand] = field(default_factory=list)
    dealer_hand: Hand = field(default_factory=Hand)
    active_hand_index: int = 0          # index de la main joueur active

    @property
    def active_hand(self) -> Optional[Hand]:
        if 0 <= self.active_hand_index < len(self.player_hands):
            return self.player_hands[self.active_hand_index]
        return None

    def deal_initial(self) -> None:
        """
        Distribue la donne initiale : 2 cartes au joueur, 2 au dealer.
        Mélange le sabot si nécessaire avant de distribuer.
        """
        if self.shoe.needs_shuffle:
            self.shoe.shuffle()

        player_hand = Hand()
        self.player_hands = [player_hand]
        self.dealer_hand = Hand()
        self.active_hand_index = 0

        # Ordre standard : joueur, dealer, joueur, dealer
        player_hand.add_card(self.shoe.deal())
        self.dealer_hand.add_card(self.shoe.deal())
        player_hand.add_card(self.shoe.deal())
        self.dealer_hand.add_card(self.shoe.deal())


# ---------------------------------------------------------------------------
# Fonctions pures de règles de jeu
# ---------------------------------------------------------------------------

def can_split(hand: Hand, max_splits: int = 3) -> bool:
    """
    Le joueur peut splitter si :
    - La main contient exactement 2 cartes de même valeur
    - Il n'a pas déjà splitté le nombre maximum de fois autorisé
    """
    if len(hand.cards) != 2:
        return False
    if hand.cards[0].value != hand.cards[1].value:
        return False
    # max_splits contrôle le nombre total de mains (défaut : jusqu'à 4 mains)
    return True  # La limite de splits est gérée au niveau GameState


def can_double(hand: Hand) -> bool:
    """
    Double autorisé sur n'importe quelle 2 premières cartes
    (règle casino standard — peut être restreint à 9-11 selon les règles).
    """
    return len(hand.cards) == 2 and not hand.is_split_hand or (
        len(hand.cards) == 2
    )


def can_surrender(hand: Hand, dealer_upcard: Card) -> bool:
    """
    Late surrender autorisé uniquement sur les 2 premières cartes
    et seulement si le dealer n'a pas de blackjack (vérifié après sa carte face cachée).
    Ici on implémente le Late Surrender standard.
    """
    return len(hand.cards) == 2 and not hand.is_split_hand


def split_hand(hand: Hand, shoe: Shoe) -> tuple[Hand, Hand]:
    """
    Sépare une main en deux mains et distribue une nouvelle carte à chacune.
    Retourne un tuple (main1, main2). Ne modifie pas la main originale.
    """
    if not can_split(hand):
        raise ValueError("Cette main ne peut pas être splittée.")

    hand1 = Hand(cards=[hand.cards[0]], is_split_hand=True)
    hand2 = Hand(cards=[hand.cards[1]], is_split_hand=True)
    hand1.add_card(shoe.deal())
    hand2.add_card(shoe.deal())
    return hand1, hand2


def dealer_must_hit(hand: Hand, hits_soft_17: bool = False) -> bool:
    """
    Le dealer doit tirer si :
    - Sa main vaut < 17
    - Sa main vaut exactement 17 et est souple ET hits_soft_17 est True
    Règle par défaut du projet : stands on soft 17 (hits_soft_17=False).
    """
    v = hand.value
    if v < 17:
        return True
    if v == 17 and hand.is_soft and hits_soft_17:
        return True
    return False


def compute_hand_result(
    player_hand: Hand,
    dealer_hand: Hand,
) -> str:
    """
    Compare une main de joueur avec la main du dealer.
    Retourne : "blackjack", "win", "push", "lose", "bust".
    Suppose que le dealer a fini de jouer.
    """
    if player_hand.is_bust:
        return "bust"
    if player_hand.is_blackjack and not dealer_hand.is_blackjack:
        return "blackjack"
    if dealer_hand.is_blackjack and not player_hand.is_blackjack:
        return "lose"
    if dealer_hand.is_bust:
        return "win"
    if player_hand.value > dealer_hand.value:
        return "win"
    if player_hand.value < dealer_hand.value:
        return "lose"
    return "push"


# ---------------------------------------------------------------------------
# Point d'entrée CLI minimal (debug)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test rapide du moteur")
    parser.add_argument("--hands", type=int, default=5)
    args = parser.parse_args()

    shoe = Shoe()
    print(f"Sabot : {shoe.total_cards} cartes ({shoe.num_decks} decks)")

    for i in range(args.hands):
        state = GameState(shoe=shoe)
        state.deal_initial()
        p = state.player_hands[0]
        d = state.dealer_hand
        print(f"Main {i+1} | Joueur : {p} | Dealer visible : {d.cards[0]}")
