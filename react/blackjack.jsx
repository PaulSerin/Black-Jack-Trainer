// ============================================================
// blackjack.jsx — Blackjack Trainer Pro (Phase 1)
// Interface React complète en un seul fichier.
// ============================================================

import { useState, useMemo } from 'react'

// ── 1. Constantes ─────────────────────────────────────────

const NUM_DECKS    = 6
const PENETRATION  = 0.75
const INIT_BANK    = 1000
const MIN_BET      = 10
const MAX_BET      = 500
const BET_STEP     = 10

const SUITS = ['clubs', 'diamonds', 'hearts', 'spades']
const RANKS = ['2','3','4','5','6','7','8','9','10','jack','queen','king','ace']

const RANK_VALUES = {
  '2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
  '10':10,'jack':10,'queen':10,'king':10,'ace':11,
}

// Upcards dans l'ordre des tables de strategy (index 0–9)
const UPCARD_ORDER = ['2','3','4','5','6','7','8','9','10','ace']

// ── 2. Logique de jeu pure ────────────────────────────────

function buildDeck() {
  const cards = []
  for (let d = 0; d < NUM_DECKS; d++)
    for (const suit of SUITS)
      for (const rank of RANKS)
        cards.push({ rank, suit, id: `${d}-${rank}-${suit}` })
  return cards
}

function shuffleDeck(deck) {
  const d = [...deck]
  for (let i = d.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [d[i], d[j]] = [d[j], d[i]]
  }
  return d
}

function cardVal(card) { return RANK_VALUES[card.rank] }

function handValue(cards) {
  let total = cards.reduce((s, c) => s + cardVal(c), 0)
  let aces  = cards.filter(c => c.rank === 'ace').length
  while (total > 21 && aces-- > 0) total -= 10
  return total
}

function isSoft(cards) {
  let total = cards.reduce((s, c) => s + cardVal(c), 0)
  let aces  = cards.filter(c => c.rank === 'ace').length
  while (total > 21 && aces > 0) { total -= 10; aces-- }
  return aces > 0 && total <= 21
}

function isBlackjack(cards, isSplitHand = false) {
  return !isSplitHand && cards.length === 2 && handValue(cards) === 21
}

function isBust(cards) { return handValue(cards) > 21 }

function canDouble(cards)            { return cards.length === 2 }
function canSplit(cards)             { return cards.length === 2 && cardVal(cards[0]) === cardVal(cards[1]) }
function canSurrender(cards, split)  { return cards.length === 2 && !split }

// Hi-Lo
function hiLoVal(card) {
  if (['2','3','4','5','6'].includes(card.rank)) return  1
  if (['7','8','9'].includes(card.rank))         return  0
  return -1
}

function roundHalf(x) { return Math.floor(x * 2 + 0.5) / 2 }
function trueCount(rc, decksLeft) {
  return decksLeft > 0 ? roundHalf(rc / decksLeft) : 0
}

// ── 3. Basic strategy (transcription de strategy.py) ──────

const _H = {
  8:  ['H','H','H','H','H','H','H','H','H','H'],
  9:  ['H','D','D','D','D','H','H','H','H','H'],
  10: ['D','D','D','D','D','D','D','D','H','H'],
  11: ['D','D','D','D','D','D','D','D','D','H'],
  12: ['H','H','S','S','S','H','H','H','H','H'],
  13: ['S','S','S','S','S','H','H','H','H','H'],
  14: ['S','S','S','S','S','H','H','H','H','H'],
  15: ['S','S','S','S','S','H','H','H','SUR','SUR'],
  16: ['S','S','S','S','S','H','H','SUR','SUR','SUR'],
  17: ['S','S','S','S','S','S','S','S','S','S'],
}
const _SOFT = {
  2:  ['H','H','H','D','D','H','H','H','H','H'],
  3:  ['H','H','H','D','D','H','H','H','H','H'],
  4:  ['H','H','D','D','D','H','H','H','H','H'],
  5:  ['H','H','D','D','D','H','H','H','H','H'],
  6:  ['H','D','D','D','D','H','H','H','H','H'],
  7:  ['Ds','Ds','Ds','Ds','Ds','S','S','H','H','H'],
  8:  ['S','S','S','S','Ds','S','S','S','S','S'],
  9:  ['S','S','S','S','S','S','S','S','S','S'],
}
const _SPLIT = {
  11: ['Y','Y','Y','Y','Y','Y','Y','Y','Y','Y'],
  10: ['N','N','N','N','N','N','N','N','N','N'],
  9:  ['Y','Y','Y','Y','Y','S','Y','Y','S','S'],
  8:  ['Y','Y','Y','Y','Y','Y','Y','Y','Y','Y'],
  7:  ['Y','Y','Y','Y','Y','Y','N','N','N','N'],
  6:  ['Y/N','Y','Y','Y','Y','N','N','N','N','N'],
  5:  ['N','N','N','N','N','N','N','N','N','N'],
  4:  ['N','N','N','Y/N','Y/N','N','N','N','N','N'],
  3:  ['Y/N','Y/N','Y','Y','Y','Y','N','N','N','N'],
  2:  ['Y/N','Y/N','Y','Y','Y','Y','N','N','N','N'],
}

function normalizeRank(rank) {
  return ['jack','queen','king'].includes(rank) ? '10' : rank
}

function basicStrategyHint(playerCards, dealerUpcard) {
  const upNorm = normalizeRank(dealerUpcard.rank)
  const ui = UPCARD_ORDER.indexOf(upNorm)
  if (ui === -1) return 'H'

  const total  = handValue(playerCards)
  const soft   = isSoft(playerCards)
  const isPair = canSplit(playerCards)

  // 1. Pairs
  if (isPair) {
    const pv  = cardVal(playerCards[0])
    const row = _SPLIT[pv]
    if (row) {
      const a = row[ui]
      if (a !== 'N') return a
    }
    // N → traiter comme hard
  }

  // 2. Soft
  if (soft) {
    const ap = total - 11
    if (ap >= 2 && ap <= 9) { const row = _SOFT[ap]; if (row) return row[ui] }
  }

  // 3. Hard
  if (total <= 7)  return 'H'
  if (total >= 18) return 'S'
  const row = _H[total]
  return row ? row[ui] : 'S'
}

// ── 4. Helpers UI ─────────────────────────────────────────

const ACTION_COLOR = {
  S: 'bg-green-500 text-white',
  H: 'bg-yellow-400 text-gray-900',
  D: 'bg-blue-500 text-white',
  Ds:'bg-blue-400 text-white',
  Y: 'bg-orange-500 text-white',
  'Y/N':'bg-orange-400 text-white',
  SUR:'bg-red-500 text-white',
}
const ACTION_LABEL = {
  S:'Stand', H:'Hit', D:'Double', Ds:'Double / Stand',
  Y:'Split', 'Y/N':'Split (if DAS)', SUR:'Surrender',
}

// Rotation déterministe par id de carte (±3°)
function cardRotation(id) {
  const h = [...id].reduce((a, c) => ((a << 5) - a + c.charCodeAt(0)) | 0, 0)
  return ((Math.abs(h) % 7) - 3)
}

// ── 5. Sous-composants ────────────────────────────────────

const CARD_IMG_BASE = 'https://raw.githubusercontent.com/hanhaechi/playing-cards/master/'

// Mapping vers le format du repo : {suit}_{rank}.png
const RANK_TO_IMG = {
  'ace':'A', '2':'2', '3':'3', '4':'4', '5':'5', '6':'6',
  '7':'7', '8':'8', '9':'9', '10':'10',
  'jack':'J', 'queen':'Q', 'king':'K',
}

function cardImgUrl(card) {
  return `${CARD_IMG_BASE}${card.suit}_${RANK_TO_IMG[card.rank]}.png`
}

function CardImg({ card, faceDown }) {
  const rot = useMemo(() => cardRotation(card?.id ?? 'back'), [card?.id])

  const style = { transform: `rotate(${rot}deg)` }
  const cls   = 'w-14 h-20 md:w-16 md:h-24 rounded-lg shadow-md object-cover select-none flex-shrink-0'

  if (faceDown || !card) {
    return (
      <img
        src={`${CARD_IMG_BASE}back_dark.png`}
        alt="Carte cachée"
        style={style}
        className={cls}
      />
    )
  }

  return (
    <img
      src={cardImgUrl(card)}
      alt={`${card.rank} of ${card.suit}`}
      style={style}
      className={cls}
    />
  )
}

function HandDisplay({ cards, label, hideFirst = false, active = false }) {
  const total = hideFirst ? handValue(cards.slice(1)) : handValue(cards)
  const soft  = !hideFirst && isSoft(cards) && total < 21

  return (
    <div className={`flex flex-col items-center gap-2 p-2 rounded-xl transition-all
      ${active ? 'ring-2 ring-yellow-400 bg-green-700/40' : ''}`}>
      <span className="text-white/70 text-xs font-semibold tracking-widest uppercase">
        {label}
      </span>
      <div className="flex gap-1 flex-wrap justify-center min-h-20">
        {cards.map((card, i) => (
          <CardImg key={card.id} card={card} faceDown={hideFirst && i === 0} />
        ))}
      </div>
      {cards.length > 0 && (
        <span className="text-white font-bold text-lg">
          {hideFirst ? '?' : `${total}${soft ? ' (soft)' : ''}`}
        </span>
      )}
    </div>
  )
}

function HintBox({ hint }) {
  if (!hint) return null
  const cls   = ACTION_COLOR[hint] ?? 'bg-gray-500 text-white'
  const label = ACTION_LABEL[hint] ?? hint
  return (
    <div className={`px-5 py-2 rounded-xl font-bold text-base shadow-lg ${cls} animate-pulse`}>
      💡 Suggestion : {label}
    </div>
  )
}

function CounterDisplay({ rc, tc }) {
  const rcColor = rc > 0 ? 'text-green-400' : rc < 0 ? 'text-red-400' : 'text-white'
  const tcColor = tc > 0 ? 'text-green-400' : tc < 0 ? 'text-red-400' : 'text-white'
  return (
    <div className="bg-black/40 rounded-xl px-4 py-3 flex flex-col gap-1 min-w-32">
      <span className="text-white/50 text-xs font-semibold tracking-widest uppercase">Hi-Lo</span>
      <div className="flex justify-between items-center gap-4">
        <span className="text-white/70 text-xs">RC</span>
        <span className={`font-bold text-lg ${rcColor}`}>{rc > 0 ? '+' : ''}{rc}</span>
      </div>
      <div className="flex justify-between items-center gap-4">
        <span className="text-white/70 text-xs">TC</span>
        <span className={`font-bold text-lg ${tcColor}`}>{tc > 0 ? '+' : ''}{tc.toFixed(1)}</span>
      </div>
    </div>
  )
}

function BetPanel({ bankroll, bet, onChange, disabled }) {
  const canDecrease = !disabled && bet > MIN_BET
  const canIncrease = !disabled && bet < Math.min(MAX_BET, bankroll)
  return (
    <div className="bg-black/40 rounded-xl px-4 py-3 flex flex-col gap-2 min-w-44">
      <span className="text-white/50 text-xs font-semibold tracking-widest uppercase">Bankroll</span>
      <span className="text-yellow-400 font-bold text-2xl">{bankroll.toFixed(0)}€</span>
      <div className="flex items-center gap-2">
        <span className="text-white/70 text-xs mr-1">Mise</span>
        <button onClick={() => onChange(Math.max(MIN_BET, bet - BET_STEP))}
          disabled={!canDecrease}
          className="w-7 h-7 bg-white/20 hover:bg-white/30 disabled:opacity-30 rounded-md text-white font-bold text-sm">
          −
        </button>
        <span className="text-white font-bold min-w-12 text-center">{bet}€</span>
        <button onClick={() => onChange(Math.min(MAX_BET, Math.min(bankroll, bet + BET_STEP)))}
          disabled={!canIncrease}
          className="w-7 h-7 bg-white/20 hover:bg-white/30 disabled:opacity-30 rounded-md text-white font-bold text-sm">
          +
        </button>
      </div>
    </div>
  )
}

// ── 6. Composant App ──────────────────────────────────────

export default function App() {
  // ─ Sabot ─
  const [shoe,      setShoe]      = useState(() => shuffleDeck(buildDeck()))
  const [shoeIdx,   setShoeIdx]   = useState(0)

  // ─ Comptage ─
  const [rc,  setRc]  = useState(0)

  // ─ Jeu ─
  const [playerHands,   setPlayerHands]   = useState([])
  const [activeIdx,     setActiveIdx]     = useState(0)
  const [dealerCards,   setDealerCards]   = useState([])
  const [phase,         setPhase]         = useState('betting') // betting|playing|result
  const [dealerHidden,  setDealerHidden]  = useState(true)
  const [isSplit,       setIsSplit]       = useState(false)

  // ─ Bankroll ─
  const [bankroll,  setBankroll]  = useState(INIT_BANK)
  const [bet,       setBet]       = useState(MIN_BET)
  const [bets,      setBets]      = useState([MIN_BET])  // par main

  // ─ UI ─
  const [hint,      setHint]      = useState(null)
  const [showHint,  setShowHint]  = useState(false)
  const [resultMsg, setResultMsg] = useState('')
  const [delta,     setDelta]     = useState(0)

  // ─ Dérivés ─
  const decksLeft = (shoe.length - shoeIdx) / 52
  const tc        = useMemo(() => trueCount(rc, decksLeft), [rc, decksLeft])
  const activeHand = playerHands[activeIdx] ?? []

  // ─────────────────────────────────────────────────────────
  // Utilitaire : distribuer une carte (gère la pénétration)
  // Retourne { card, newShoe, newIdx, newRc, reshuffled }
  // ─────────────────────────────────────────────────────────
  function dealOne(currentShoe, currentIdx, currentRc) {
    let s = currentShoe, i = currentIdx, r = currentRc
    let reshuffled = false
    if (i >= Math.floor(s.length * PENETRATION)) {
      s = shuffleDeck(buildDeck())
      i = 0
      r = 0
      reshuffled = true
    }
    return { card: s[i], newShoe: s, newIdx: i + 1, newRc: r, reshuffled }
  }

  // ─────────────────────────────────────────────────────────
  // Jouer la main du dealer + résoudre toutes les mains
  // (tout synchrone, un seul batch de state updates)
  // ─────────────────────────────────────────────────────────
  function resolveDealer(hands, dCards, currentRc, currentShoe, currentIdx, handBets, wasSplit) {
    let s   = currentShoe
    let idx = currentIdx
    let r   = currentRc
    let dHand = [...dCards]

    // Révéler la carte cachée
    r += hiLoVal(dHand[0])

    // Dealer tire selon S17
    while (true) {
      const v    = handValue(dHand)
      const soft = isSoft(dHand)
      if (v >= 17 && !(v === 17 && soft && false)) break  // stands on soft 17
      const result = dealOne(s, idx, r)
      if (result.reshuffled) r = 0
      s   = result.newShoe
      idx = result.newIdx
      r  += hiLoVal(result.card)
      dHand.push(result.card)
    }

    const dTotal = handValue(dHand)
    const dBust  = dTotal > 21
    let   totalDelta = 0
    const msgs = []

    hands.forEach((hand, i) => {
      const b      = handBets[i] ?? handBets[0]
      const pTotal = handValue(hand)
      const pBust  = isBust(hand)
      const pBJ    = isBlackjack(hand, wasSplit)
      const dBJ    = isBlackjack(dCards)  // utilise les cartes originales (2 cartes)

      if (pBust) {
        msgs.push(hands.length > 1 ? `M${i+1}: Bust` : 'Bust')
      } else if (pBJ && !dBJ) {
        const gain = b + Math.floor(b * 1.5)
        setBankroll(prev => prev + gain)
        totalDelta += gain - b
        msgs.push(`Blackjack! +${Math.floor(b * 1.5)}€`)
      } else if (dBJ && !pBJ) {
        msgs.push(hands.length > 1 ? `M${i+1}: Dealer BJ` : 'Dealer Blackjack')
      } else if (pBJ && dBJ) {
        setBankroll(prev => prev + b)
        msgs.push('Push — Both BJ')
      } else if (dBust || pTotal > dTotal) {
        setBankroll(prev => prev + b * 2)
        totalDelta += b
        msgs.push(hands.length > 1 ? `M${i+1}: Win +${b}€` : `Win +${b}€`)
      } else if (pTotal < dTotal) {
        msgs.push(hands.length > 1 ? `M${i+1}: Lose` : 'Lose')
        totalDelta -= b
      } else {
        setBankroll(prev => prev + b)
        msgs.push(hands.length > 1 ? `M${i+1}: Push` : 'Push')
      }
    })

    setDealerCards(dHand)
    setDealerHidden(false)
    setShoe(s)
    setShoeIdx(idx)
    setRc(r)
    setDelta(totalDelta)
    setResultMsg(msgs.join('  ·  '))
    setPhase('result')
  }

  // ─────────────────────────────────────────────────────────
  // Passer à la main suivante ou au dealer
  // ─────────────────────────────────────────────────────────
  function advance(hands, currentActiveIdx, dCards, currentRc, currentShoe, currentIdx, handBets, wasSplit) {
    const next = currentActiveIdx + 1
    if (next < hands.length) {
      setActiveIdx(next)
    } else {
      resolveDealer(hands, dCards, currentRc, currentShoe, currentIdx, handBets, wasSplit)
    }
  }

  // ─────────────────────────────────────────────────────────
  // Distribuer une nouvelle donne
  // ─────────────────────────────────────────────────────────
  function startHand() {
    let s = shoe, i = shoeIdx, r = rc

    // Mélange si pénétration atteinte
    if (i >= Math.floor(s.length * PENETRATION)) {
      s = shuffleDeck(buildDeck())
      i = 0
      r = 0
    }

    // 4 cartes : p1, d_hole, p2, d_up
    const p1 = s[i++], dHole = s[i++], p2 = s[i++], dUp = s[i++]

    // Compter cartes visibles (joueur + upcard dealer)
    r += hiLoVal(p1) + hiLoVal(p2) + hiLoVal(dUp)

    const pHand  = [p1, p2]
    const dHand  = [dHole, dUp]
    const initBet = bet

    setBankroll(prev => prev - initBet)
    setShoe(s)
    setShoeIdx(i)
    setRc(r)
    setPlayerHands([pHand])
    setDealerCards(dHand)
    setActiveIdx(0)
    setDealerHidden(true)
    setBets([initBet])
    setHint(null)
    setShowHint(false)
    setResultMsg('')
    setDelta(0)
    setIsSplit(false)

    // Blackjack immédiat ?
    const pBJ = isBlackjack(pHand)
    const dBJ = isBlackjack(dHand)
    if (pBJ || dBJ) {
      const rFinal = r + hiLoVal(dHole)
      setRc(rFinal)
      setDealerHidden(false)
      // Résoudre directement
      const dBJCheck = dBJ
      const pBJCheck = pBJ
      let totalDelta = 0, msg = ''
      if (pBJCheck && dBJCheck) {
        setBankroll(prev => prev + initBet)
        msg = 'Push — Both Blackjack!'
      } else if (pBJCheck) {
        const gain = initBet + Math.floor(initBet * 1.5)
        setBankroll(prev => prev + gain)
        totalDelta = Math.floor(initBet * 1.5)
        msg = `Blackjack! +${Math.floor(initBet * 1.5)}€`
      } else {
        msg = 'Dealer Blackjack.'
        totalDelta = -initBet
      }
      setDelta(totalDelta)
      setResultMsg(msg)
      setPhase('result')
    } else {
      setPhase('playing')
    }
  }

  // ─────────────────────────────────────────────────────────
  // Actions joueur
  // ─────────────────────────────────────────────────────────
  function doHit() {
    const result = dealOne(shoe, shoeIdx, rc)
    const newRc  = result.reshuffled ? hiLoVal(result.card) : rc + hiLoVal(result.card)
    const newHand = [...activeHand, result.card]
    const newHands = playerHands.map((h, i) => i === activeIdx ? newHand : h)

    setShoe(result.newShoe)
    setShoeIdx(result.newIdx)
    setRc(newRc)
    setPlayerHands(newHands)
    setHint(null)
    setShowHint(false)

    if (isBust(newHand)) {
      advance(newHands, activeIdx, dealerCards, newRc, result.newShoe, result.newIdx, bets, isSplit)
    }
  }

  function doStand() {
    setHint(null)
    setShowHint(false)
    advance(playerHands, activeIdx, dealerCards, rc, shoe, shoeIdx, bets, isSplit)
  }

  function doDouble() {
    if (!canDouble(activeHand)) return
    const result = dealOne(shoe, shoeIdx, rc)
    const newRc   = result.reshuffled ? hiLoVal(result.card) : rc + hiLoVal(result.card)
    const newHand = [...activeHand, result.card]
    const newHands = playerHands.map((h, i) => i === activeIdx ? newHand : h)
    const newBets  = bets.map((b, i) => i === activeIdx ? b * 2 : b)

    setBankroll(prev => prev - bets[activeIdx])  // mise supplémentaire
    setShoe(result.newShoe)
    setShoeIdx(result.newIdx)
    setRc(newRc)
    setPlayerHands(newHands)
    setBets(newBets)
    setHint(null)
    setShowHint(false)

    // Après un double : stand obligatoire
    advance(newHands, activeIdx, dealerCards, newRc, result.newShoe, result.newIdx, newBets, isSplit)
  }

  function doSplit() {
    if (!canSplit(activeHand) || playerHands.length >= 4) return

    const r1 = dealOne(shoe, shoeIdx, rc)
    const newRc1 = r1.reshuffled ? hiLoVal(r1.card) : rc + hiLoVal(r1.card)
    const r2 = dealOne(r1.newShoe, r1.newIdx, newRc1)
    const newRc2 = r2.reshuffled ? hiLoVal(r2.card) : newRc1 + hiLoVal(r2.card)

    const hand1 = [activeHand[0], r1.card]
    const hand2 = [activeHand[1], r2.card]
    const newHands = [
      ...playerHands.slice(0, activeIdx),
      hand1, hand2,
      ...playerHands.slice(activeIdx + 1),
    ]
    const newBets = [
      ...bets.slice(0, activeIdx),
      bets[activeIdx], bets[activeIdx],
      ...bets.slice(activeIdx + 1),
    ]

    setBankroll(prev => prev - bets[activeIdx])
    setShoe(r2.newShoe)
    setShoeIdx(r2.newIdx)
    setRc(newRc2)
    setPlayerHands(newHands)
    setBets(newBets)
    setHint(null)
    setShowHint(false)
    setIsSplit(true)
    // activeIdx reste sur la première main du split
  }

  function doSurrender() {
    const half = bets[activeIdx] / 2
    setBankroll(prev => prev + half)  // rembourser la moitié
    setDelta(-half)
    setResultMsg(`Surrender. Perdu ${half}€`)
    setPhase('result')
    setHint(null)
    setShowHint(false)
  }

  function handleShowHint() {
    if (dealerCards.length < 2) return
    const upcard = dealerCards[1]  // deuxième carte = upcard
    setHint(basicStrategyHint(activeHand, upcard))
    setShowHint(true)
  }

  // ─────────────────────────────────────────────────────────
  // Actions disponibles
  // ─────────────────────────────────────────────────────────
  const playing       = phase === 'playing'
  const canDbl        = playing && canDouble(activeHand) && bankroll >= bets[activeIdx]
  const canSpl        = playing && canSplit(activeHand) && bankroll >= bets[activeIdx] && playerHands.length < 4
  const canSur        = playing && canSurrender(activeHand, isSplit)

  // ─────────────────────────────────────────────────────────
  // Rendu
  // ─────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-green-900 flex flex-col p-3 gap-3 select-none">

      {/* ── Header ── */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-white font-bold text-2xl tracking-wider">🂡 Blackjack Trainer</h1>
          <p className="text-white/40 text-xs mt-0.5">6 decks · S17 · Hi-Lo</p>
        </div>
        <div className="flex gap-3 flex-wrap">
          <CounterDisplay rc={rc} tc={tc} />
          <BetPanel
            bankroll={bankroll}
            bet={bet}
            onChange={setBet}
            disabled={playing || phase === 'result'}
          />
        </div>
      </div>

      {/* ── Table ── */}
      <div className="flex-1 flex flex-col gap-3 max-w-2xl mx-auto w-full">

        {/* Zone dealer */}
        <div className="bg-green-800/50 rounded-2xl p-4 flex flex-col items-center min-h-36">
          {dealerCards.length > 0
            ? <HandDisplay
                cards={dealerCards}
                label="Dealer"
                hideFirst={dealerHidden && playing}
              />
            : <span className="text-white/30 text-sm mt-8">En attente…</span>
          }
        </div>

        {/* Message résultat */}
        {phase === 'result' && resultMsg && (
          <div className={`text-center font-bold text-lg py-3 px-6 rounded-xl shadow-lg
            ${delta > 0 ? 'bg-green-500 text-white'
            : delta < 0 ? 'bg-red-500 text-white'
            : 'bg-gray-500 text-white'}`}>
            {resultMsg}
          </div>
        )}

        {/* Zone joueur */}
        <div className="bg-green-800/50 rounded-2xl p-4 flex flex-col items-center min-h-36">
          {playerHands.length > 0 ? (
            <div className="flex gap-4 flex-wrap justify-center">
              {playerHands.map((hand, i) => (
                <HandDisplay
                  key={i}
                  cards={hand}
                  label={playerHands.length > 1 ? `Main ${i + 1}` : 'Vous'}
                  active={playing && i === activeIdx}
                />
              ))}
            </div>
          ) : (
            <span className="text-white/30 text-sm mt-8">Placez votre mise et distribuez</span>
          )}
        </div>
      </div>

      {/* ── Actions ── */}
      <div className="flex flex-col items-center gap-3 max-w-2xl mx-auto w-full">

        {/* Hint */}
        {showHint && hint && <HintBox hint={hint} />}

        {/* Boutons de jeu */}
        {playing && (
          <div className="flex flex-wrap gap-2 justify-center">
            <button onClick={doHit}
              className="px-5 py-2.5 bg-yellow-500 hover:bg-yellow-400 active:bg-yellow-600 text-gray-900 font-bold rounded-xl shadow transition-colors">
              Hit
            </button>
            <button onClick={doStand}
              className="px-5 py-2.5 bg-green-500 hover:bg-green-400 active:bg-green-600 text-white font-bold rounded-xl shadow transition-colors">
              Stand
            </button>
            {canDbl && (
              <button onClick={doDouble}
                className="px-5 py-2.5 bg-blue-500 hover:bg-blue-400 active:bg-blue-600 text-white font-bold rounded-xl shadow transition-colors">
                Double
              </button>
            )}
            {canSpl && (
              <button onClick={doSplit}
                className="px-5 py-2.5 bg-orange-500 hover:bg-orange-400 active:bg-orange-600 text-white font-bold rounded-xl shadow transition-colors">
                Split
              </button>
            )}
            {canSur && (
              <button onClick={doSurrender}
                className="px-5 py-2.5 bg-red-500 hover:bg-red-400 active:bg-red-600 text-white font-bold rounded-xl shadow transition-colors">
                Surrender
              </button>
            )}
            <button onClick={handleShowHint}
              className="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 active:bg-purple-700 text-white font-bold rounded-xl shadow transition-colors">
              💡 Hint
            </button>
          </div>
        )}

        {phase === 'betting' && (
          <button onClick={startHand}
            disabled={bankroll < bet}
            className="px-14 py-4 bg-yellow-500 hover:bg-yellow-400 disabled:opacity-40 text-gray-900 font-bold text-xl rounded-xl shadow-lg transition-colors">
            Distribuer
          </button>
        )}

        {phase === 'result' && (
          <button onClick={() => setPhase('betting')}
            className="px-14 py-4 bg-yellow-500 hover:bg-yellow-400 text-gray-900 font-bold text-xl rounded-xl shadow-lg transition-colors">
            Main suivante →
          </button>
        )}

        {/* Info deck */}
        <p className="text-white/30 text-xs">
          Sabot : {shoe.length - shoeIdx} cartes restantes
          {shoeIdx >= Math.floor(shoe.length * PENETRATION * 0.95) &&
            ' · 🔀 Mélange prochain'}
        </p>
      </div>
    </div>
  )
}
