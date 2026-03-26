// blackjack.jsx — Blackjack Trainer Pro
import { useState, useMemo, useEffect } from 'react'

// ── Constants ────────────────────────────────────────────────
const NUM_DECKS   = 6
const PENETRATION = 0.75
const INIT_BANK   = 1000
const MIN_BET     = 10
const MAX_BET     = 500
const BET_STEP    = 10

const SUITS = ['clubs','diamonds','hearts','spades']
const RANKS = ['2','3','4','5','6','7','8','9','10','jack','queen','king','ace']
const RANK_VALUES = {
  '2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
  '10':10,'jack':10,'queen':10,'king':10,'ace':11,
}
const UPCARD_ORDER = ['2','3','4','5','6','7','8','9','10','ace']
const IMG_BASE = 'https://raw.githubusercontent.com/hanhaechi/playing-cards/master/'
const BACK_URL = `${IMG_BASE}back_dark.png`
const RANK_IMG = {
  'ace':'A','2':'2','3':'3','4':'4','5':'5','6':'6',
  '7':'7','8':'8','9':'9','10':'10','jack':'J','queen':'Q','king':'K',
}

// ── Pure game logic ───────────────────────────────────────────
function buildDeck() {
  const cards = []
  for (let d = 0; d < NUM_DECKS; d++)
    for (const s of SUITS)
      for (const r of RANKS)
        cards.push({ rank: r, suit: s, id: `${d}-${r}-${s}` })
  return cards
}

function shuffle(deck) {
  const d = [...deck]
  for (let i = d.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[d[i], d[j]] = [d[j], d[i]]
  }
  return d
}

const cardVal = c => RANK_VALUES[c.rank]

function handValue(cards) {
  let v = cards.reduce((s, c) => s + cardVal(c), 0)
  let a = cards.filter(c => c.rank === 'ace').length
  while (v > 21 && a-- > 0) v -= 10
  return v
}

function isSoft(cards) {
  let v = cards.reduce((s, c) => s + cardVal(c), 0)
  let a = cards.filter(c => c.rank === 'ace').length
  while (v > 21 && a > 0) { v -= 10; a-- }
  return a > 0 && v <= 21
}

const isBlackjack = (cards, split = false) =>
  !split && cards.length === 2 && handValue(cards) === 21
const isBust    = cards => handValue(cards) > 21
const canDouble = cards => cards.length === 2
const canSplit  = cards => cards.length === 2 && cardVal(cards[0]) === cardVal(cards[1])
const canSurr   = (cards, split) => !split && cards.length === 2

// ── Hi-Lo ────────────────────────────────────────────────────
const hiLo = c =>
  ['2','3','4','5','6'].includes(c.rank) ? 1
  : ['7','8','9'].includes(c.rank) ? 0 : -1
const roundHalf = x => Math.floor(x * 2 + 0.5) / 2
const calcTC    = (rc, dl) => dl > 0 ? roundHalf(rc / dl) : 0

// ── Basic strategy ────────────────────────────────────────────
const _H = {
  8: ['H','H','H','H','H','H','H','H','H','H'],
  9: ['H','D','D','D','D','H','H','H','H','H'],
  10:['D','D','D','D','D','D','D','D','H','H'],
  11:['D','D','D','D','D','D','D','D','D','H'],
  12:['H','H','S','S','S','H','H','H','H','H'],
  13:['S','S','S','S','S','H','H','H','H','H'],
  14:['S','S','S','S','S','H','H','H','H','H'],
  15:['S','S','S','S','S','H','H','H','SUR','SUR'],
  16:['S','S','S','S','S','H','H','SUR','SUR','SUR'],
  17:['S','S','S','S','S','S','S','S','S','S'],
}
const _SOFT = {
  2:['H','H','H','D','D','H','H','H','H','H'],
  3:['H','H','H','D','D','H','H','H','H','H'],
  4:['H','H','D','D','D','H','H','H','H','H'],
  5:['H','H','D','D','D','H','H','H','H','H'],
  6:['H','D','D','D','D','H','H','H','H','H'],
  7:['Ds','Ds','Ds','Ds','Ds','S','S','H','H','H'],
  8:['S','S','S','S','Ds','S','S','S','S','S'],
  9:['S','S','S','S','S','S','S','S','S','S'],
}
const _SPLIT = {
  11:['Y','Y','Y','Y','Y','Y','Y','Y','Y','Y'],
  10:['N','N','N','N','N','N','N','N','N','N'],
  9: ['Y','Y','Y','Y','Y','S','Y','Y','S','S'],
  8: ['Y','Y','Y','Y','Y','Y','Y','Y','Y','Y'],
  7: ['Y','Y','Y','Y','Y','Y','N','N','N','N'],
  6: ['Y/N','Y','Y','Y','Y','N','N','N','N','N'],
  5: ['N','N','N','N','N','N','N','N','N','N'],
  4: ['N','N','N','Y/N','Y/N','N','N','N','N','N'],
  3: ['Y/N','Y/N','Y','Y','Y','Y','N','N','N','N'],
  2: ['Y/N','Y/N','Y','Y','Y','Y','N','N','N','N'],
}

const normRank = r => ['jack','queen','king'].includes(r) ? '10' : r

function basicHint(pCards, dCard) {
  const ui = UPCARD_ORDER.indexOf(normRank(dCard.rank))
  if (ui === -1) return 'H'
  const total = handValue(pCards), soft = isSoft(pCards)
  if (canSplit(pCards)) {
    const row = _SPLIT[cardVal(pCards[0])]
    if (row && row[ui] !== 'N') return row[ui]
  }
  if (soft) {
    const ap = total - 11
    if (ap >= 2 && ap <= 9 && _SOFT[ap]) return _SOFT[ap][ui]
  }
  if (total <= 7) return 'H'
  if (total >= 18) return 'S'
  return _H[total]?.[ui] ?? 'S'
}

// ── Illustrious 18 deviations ─────────────────────────────────
const I18 = [
  { val:16, up:'10',  op:'>=', thr: 0, action:'S', pair:false },
  { val:15, up:'10',  op:'>=', thr: 4, action:'S', pair:false },
  { val:10, up:'10',  op:'>=', thr: 4, action:'D', pair:false },
  { val:12, up:'3',   op:'>=', thr: 2, action:'S', pair:false },
  { val:12, up:'2',   op:'>=', thr: 3, action:'S', pair:false },
  { val:11, up:'ace', op:'>=', thr: 1, action:'D', pair:false },
  { val: 9, up:'2',   op:'>=', thr: 1, action:'D', pair:false },
  { val:10, up:'ace', op:'>=', thr: 4, action:'D', pair:false },
  { val: 9, up:'7',   op:'>=', thr: 3, action:'D', pair:false },
  { val:16, up:'9',   op:'>=', thr: 5, action:'S', pair:false },
  { val:10, up:'5',   op:'>=', thr: 5, action:'Y', pair:true  },
  { val:10, up:'6',   op:'>=', thr: 4, action:'Y', pair:true  },
  { val:13, up:'2',   op:'<',  thr:-1, action:'H', pair:false },
  { val:12, up:'4',   op:'<',  thr: 0, action:'H', pair:false },
  { val:12, up:'5',   op:'<',  thr:-2, action:'H', pair:false },
  { val:12, up:'6',   op:'<',  thr:-1, action:'H', pair:false },
  { val:13, up:'3',   op:'<',  thr:-2, action:'H', pair:false },
]

function deviationHint(pCards, dCard, tc) {
  if (isSoft(pCards)) return null
  const basic = basicHint(pCards, dCard)
  const up = normRank(dCard.rank), total = handValue(pCards)
  const isPair = canSplit(pCards)
  for (const d of I18) {
    if (d.up !== up || total !== d.val) continue
    if (d.pair !== isPair) continue
    // Les indices I18 "Stand vs Hit" ne s'appliquent pas quand basic = SUR :
    // ils ont été calibrés pour jeux sans surrender (basic=Hit), pas pour remplacer SUR.
    if (basic === 'SUR' && d.action === 'S') continue
    if (d.op === '>=' ? tc >= d.thr : tc < d.thr) return d.action
  }
  return null
}

function getHint(pCards, dCard, tc) {
  if (!pCards?.length || !dCard) return null
  const basic = basicHint(pCards, dCard)
  const dev   = deviationHint(pCards, dCard, tc)
  return { action: dev ?? basic, isDeviation: dev !== null && dev !== basic, basic }
}

// ── Action metadata ───────────────────────────────────────────
const ACTION = {
  S:    { label:'Stand',           bg:'bg-emerald-500', fg:'text-white' },
  H:    { label:'Hit',             bg:'bg-amber-400',   fg:'text-gray-900' },
  D:    { label:'Double Down',     bg:'bg-blue-500',    fg:'text-white' },
  Ds:   { label:'Double or Stand', bg:'bg-blue-400',    fg:'text-white' },
  Y:    { label:'Split',           bg:'bg-orange-500',  fg:'text-white' },
  'Y/N':{ label:'Split (if DAS)',  bg:'bg-orange-400',  fg:'text-white' },
  SUR:  { label:'Surrender',       bg:'bg-red-500',     fg:'text-white' },
}

// ── Card component ────────────────────────────────────────────
function CardImg({ card, faceDown, animCls = '', animDelay = 0 }) {
  const src = faceDown || !card
    ? BACK_URL
    : `${IMG_BASE}${card.suit}_${RANK_IMG[card.rank]}.png`
  return (
    <div
      className={`flex-shrink-0 rounded-lg overflow-hidden shadow-xl ${animCls}`}
      style={animCls ? { animationDelay: `${animDelay}s`, animationFillMode:'both' } : undefined}
    >
      <img src={src} alt={faceDown ? '?' : card ? `${card.rank} ${card.suit}` : '?'}
        className="w-14 h-20 md:w-16 md:h-24 object-cover block" />
    </div>
  )
}

// ── Hand display ──────────────────────────────────────────────
function HandDisplay({ cards, label, hideFirst = false, active = false,
                       result = null, bet = 0, revealCount = Infinity, isRevealing = false }) {
  const shown  = cards.slice(0, Math.min(cards.length, revealCount))
  const total  = hideFirst ? handValue(shown.slice(1)) : handValue(shown)
  const soft   = !hideFirst && isSoft(shown) && total < 21
  const bust   = !hideFirst && shown.length > 0 && isBust(shown)
  const bj     = !hideFirst && shown.length > 0 && isBlackjack(shown)

  const ring = result === 'win' || result === 'bj'
    ? 'ring-2 ring-emerald-400 bg-emerald-900/20'
    : result === 'lose'
    ? 'ring-2 ring-red-400/70 bg-red-900/15'
    : result === 'push'
    ? 'ring-2 ring-yellow-400/50'
    : active
    ? 'ring-2 ring-white/40 bg-white/5'
    : ''

  return (
    <div className={`flex flex-col items-center gap-1.5 px-3 py-2 rounded-xl transition-all duration-300 ${ring}`}>
      <div className="flex items-center gap-1.5">
        <span className="text-white/50 text-xs uppercase tracking-wider font-semibold">{label}</span>
        {bet > 0 && <span className="text-yellow-400/60 text-xs font-bold">{bet}€</span>}
      </div>
      <div className="flex gap-1 flex-wrap justify-center" style={{ minHeight:'5rem' }}>
        {shown.map((card, i) => {
          const fd  = hideFirst && i === 0
          const cls = isRevealing
            ? (i === 0 ? 'card-flip' : i >= 2 ? 'card-deal' : '')
            : ''
          return (
            <CardImg key={fd ? `back-${card.id}` : card.id}
              card={card} faceDown={fd} animCls={cls} animDelay={0} />
          )
        })}
      </div>
      {shown.length > 0 && (
        <div className="font-bold text-lg leading-none flex items-center gap-1.5 text-white">
          {hideFirst
            ? <span className="text-white/25">?</span>
            : <>
                <span>{total}</span>
                {soft && <span className="text-white/35 text-sm font-normal">soft</span>}
                {bust && <span className="text-red-400 text-sm ml-1">Bust</span>}
                {bj   && <span className="text-yellow-300 text-sm ml-1">BJ!</span>}
              </>
          }
        </div>
      )}
    </div>
  )
}

// ── Hint box ──────────────────────────────────────────────────
function HintBox({ hint }) {
  if (!hint) return null
  const m = ACTION[hint.action] ?? { label: hint.action, bg:'bg-gray-600', fg:'text-white' }
  return (
    <div className={`flex flex-col gap-0.5 px-4 py-2.5 rounded-xl font-bold shadow-lg ${m.bg} ${m.fg} min-w-36`}>
      <div className="text-xs font-normal opacity-70">
        {hint.isDeviation ? '★ I18 Deviation' : 'Basic Strategy'}
      </div>
      <div className="text-base">{m.label}</div>
      {hint.isDeviation && (
        <div className="text-xs font-normal opacity-55">
          (basic: {ACTION[hint.basic]?.label ?? hint.basic})
        </div>
      )}
    </div>
  )
}

// ── Covered panel (vignette révélable au clic) ───────────────
function CoveredPanel({ children, hidden, onToggle, label, icon = '🔒', className = '' }) {
  return (
    <div className={`relative cursor-pointer select-none ${className}`} onClick={onToggle}>
      {children}
      <div
        className="absolute inset-0 rounded-xl flex flex-col items-center justify-center gap-1.5 transition-all duration-300"
        style={{
          backdropFilter: hidden ? 'blur(8px)' : 'blur(0px)',
          backgroundColor: hidden ? 'rgba(0,0,0,0.72)' : 'rgba(0,0,0,0)',
          opacity: hidden ? 1 : 0,
          pointerEvents: hidden ? 'auto' : 'none',
          border: hidden ? '1px solid rgba(255,255,255,0.08)' : '1px solid transparent',
        }}
      >
        <span className="text-lg">{icon}</span>
        <span className="text-white/50 text-xs font-bold uppercase tracking-widest">{label}</span>
        <span className="text-white/25 text-xs">click to reveal</span>
      </div>
      {/* "cacher" indicator when shown */}
      {!hidden && (
        <div className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity"
          title="Hide">
          <span className="text-white/40 text-xs">✕</span>
        </div>
      )}
    </div>
  )
}

// ── Hi-Lo counter ─────────────────────────────────────────────
function Counter({ rc, tc }) {
  const tcCls = tc >= 3 ? 'text-emerald-400'
    : tc >= 1 ? 'text-lime-400'
    : tc <= -3 ? 'text-red-400'
    : tc < 0 ? 'text-orange-400' : 'text-white'
  return (
    <div className="bg-black/40 border border-white/10 rounded-xl px-4 py-3 flex flex-col gap-1 min-w-36">
      <span className="text-white/40 text-xs font-bold tracking-widest uppercase">Hi-Lo</span>
      <div className="flex justify-between items-baseline">
        <span className="text-white/40 text-xs">Running</span>
        <span className={`font-black text-xl ${rc > 0 ? 'text-lime-400' : rc < 0 ? 'text-red-400' : 'text-white'}`}>
          {rc > 0 ? '+' : ''}{rc}
        </span>
      </div>
      <div className="flex justify-between items-baseline">
        <span className="text-white/40 text-xs">True</span>
        <span className={`font-black text-xl ${tcCls}`}>
          {tc > 0 ? '+' : ''}{tc.toFixed(1)}
        </span>
      </div>
      {Math.abs(tc) >= 1 && (
        <div className={`text-xs text-center ${tcCls} opacity-70`}>
          {tc >= 1 ? '▲ Favorable' : '▼ Unfavorable'}
        </div>
      )}
    </div>
  )
}

// ── Action button ─────────────────────────────────────────────
const BTN_STYLES = {
  Hit:       'bg-amber-500 hover:bg-amber-400 text-gray-900',
  Stand:     'bg-emerald-600 hover:bg-emerald-500 text-white',
  Double:    'bg-blue-600 hover:bg-blue-500 text-white',
  Split:     'bg-orange-600 hover:bg-orange-500 text-white',
  Surrender: 'bg-red-700 hover:bg-red-600 text-white',
}

function ActionBtn({ label, onClick, enabled }) {
  return (
    <button
      onClick={enabled ? onClick : undefined}
      disabled={!enabled}
      className={`px-4 py-2.5 font-bold rounded-xl shadow transition-all text-sm
        ${BTN_STYLES[label]}
        ${!enabled ? 'opacity-30 cursor-not-allowed' : 'active:scale-95'}`}
    >
      {label}
    </button>
  )
}

// ── App ───────────────────────────────────────────────────────
export default function App() {
  // ─ Shoe ─
  const [shoe,    setShoe]    = useState(() => shuffle(buildDeck()))
  const [shoeIdx, setShoeIdx] = useState(0)
  const [rc,      setRc]      = useState(0)

  // ─ Hands ─
  const [playerHands,    setPlayerHands]    = useState([])
  const [activeIdx,      setActiveIdx]      = useState(0)
  const [dealerCards,    setDealerCards]    = useState([])
  const [isSplitGame,    setIsSplitGame]    = useState(false)
  const [surrendered,    setSurrendered]    = useState([])
  // preHandResults: hands resolved before playing phase (BJ while dealer no BJ)
  // null = unresolved, 'bj' | 'push' | 'lose' = already settled
  const [preHandResults, setPreHandResults] = useState([])

  // ─ Bankroll ─
  const [bankroll, setBankroll] = useState(INIT_BANK)
  const [bet,      setBet]      = useState(MIN_BET)
  const [bets,     setBets]     = useState([MIN_BET])
  const [numHands, setNumHands] = useState(1)

  // ─ Phase & animation ─
  const [phase,         setPhase]         = useState('betting')
  const [revealCount,   setRevealCount]   = useState(0)
  const [pendingResult, setPendingResult] = useState(null)

  // ─ Result display ─
  const [resultMsg,   setResultMsg]   = useState('')
  const [delta,       setDelta]       = useState(0)
  const [handResults, setHandResults] = useState([])

  // ─ Insurance ─
  const [insuranceTaken, setInsuranceTaken] = useState(false)
  const [insuranceBet,   setInsuranceBet]   = useState(0)

  // ─ UI toggles ─
  const [showHint,    setShowHint]    = useState(true)
  const [showCounter, setShowCounter] = useState(true)

  // ─ Derived ─
  const decksLeft  = (shoe.length - shoeIdx) / 52
  const tc         = useMemo(() => calcTC(rc, decksLeft), [rc, decksLeft])
  const activeHand = playerHands[activeIdx] ?? []
  const upcard     = dealerCards[1] ?? null

  const hint = useMemo(() => {
    if (phase !== 'playing' || !upcard || !activeHand.length) return null
    // Don't show hint for pre-resolved hands
    if (preHandResults[activeIdx] != null) return null
    return getHint(activeHand, upcard, tc)
  }, [phase, activeHand, upcard, tc, activeIdx, preHandResults])

  // Recommandation assurance : affichée pendant la phase 'insurance'
  const insuranceHint = phase === 'insurance' ? (tc >= 3 ? 'take' : 'decline') : null

  // ─ Dealer reveal animation ────────────────────────────────
  useEffect(() => {
    if (phase !== 'revealing') return
    const t = setTimeout(() => {
      if (revealCount >= dealerCards.length) {
        if (pendingResult) {
          setBankroll(prev => prev + pendingResult.bankrollReturn)
          setResultMsg(pendingResult.msg)
          setDelta(pendingResult.displayDelta)
          setHandResults(pendingResult.results)
        }
        setPhase('result')
      } else {
        setRevealCount(n => n + 1)
      }
    }, 450)
    return () => clearTimeout(t)
  }, [phase, revealCount, dealerCards.length, pendingResult])

  // ─ Shoe helpers ───────────────────────────────────────────
  function draw(s, i, r) {
    if (i >= Math.floor(s.length * PENETRATION)) {
      s = shuffle(buildDeck()); i = 0; r = 0
    }
    return { card: s[i], shoe: s, idx: i + 1, rcBefore: r }
  }

  // ─ Compute full dealer hand ───────────────────────────────
  function computeDealer(dCards, curRc, curShoe, curIdx) {
    let s = curShoe, i = curIdx, r = curRc
    const hand = [...dCards]
    r += hiLo(hand[0])
    while (handValue(hand) < 17) {
      const d = draw(s, i, r)
      s = d.shoe; i = d.idx; r = d.rcBefore + hiLo(d.card)
      hand.push(d.card)
    }
    return { hand, newShoe: s, newIdx: i, newRc: r }
  }

  // ─ Start dealer reveal ────────────────────────────────────
  function startReveal(hands, dCards, curRc, curShoe, curIdx, handBets, wasSplit, surr, preRes) {
    // Only draw if at least one non-pre-resolved, non-bust, non-surrendered hand exists
    const needsDraw = hands.some((h, i) =>
      preRes[i] == null && !surr.includes(i) && !isBust(h)
    )
    const { hand: dHand, newShoe, newIdx, newRc } = needsDraw
      ? computeDealer(dCards, curRc, curShoe, curIdx)
      : { hand: dCards, newShoe: curShoe, newIdx: curIdx, newRc: curRc + hiLo(dCards[0]) }

    const dTotal = handValue(dHand)
    const dBJ    = isBlackjack(dCards)

    let bankrollReturn = 0, displayDelta = 0
    const msgs = [], results = []

    hands.forEach((hand, hi) => {
      const b = handBets[hi] ?? handBets[0]

      // Pre-resolved BJ hands (bankroll already applied in startHand)
      if (preRes[hi] != null) {
        const gain = Math.floor(b * 1.5)
        results.push(preRes[hi])
        if (preRes[hi] === 'bj') {
          displayDelta += gain
          msgs.push(hands.length > 1 ? `M${hi+1}: BJ +${gain}€` : `Blackjack! +${gain}€`)
        } else if (preRes[hi] === 'push') {
          msgs.push(hands.length > 1 ? `M${hi+1}: Push BJ` : 'Push — Both BJ')
        } else {
          displayDelta -= b
          msgs.push(hands.length > 1 ? `M${hi+1}: Dealer BJ` : 'Dealer Blackjack')
        }
        return
      }

      // Surrendered
      if (surr.includes(hi)) {
        results.push('lose'); displayDelta -= b / 2
        msgs.push(hands.length > 1 ? `M${hi+1}: Surrender` : 'Surrender')
        return
      }

      const pTotal = handValue(hand)
      const pBJ    = isBlackjack(hand, wasSplit)

      if (isBust(hand)) {
        results.push('lose'); displayDelta -= b
        msgs.push(hands.length > 1 ? `M${hi+1}: Bust` : 'Bust')
      } else if (pBJ && !dBJ) {
        const gain = Math.floor(b * 1.5)
        bankrollReturn += b + gain; displayDelta += gain
        results.push('bj')
        msgs.push(hands.length > 1 ? `M${hi+1}: BJ +${gain}€` : `Blackjack! +${gain}€`)
      } else if (dBJ && !pBJ) {
        results.push('lose'); displayDelta -= b
        msgs.push(hands.length > 1 ? `M${hi+1}: Dealer BJ` : 'Dealer Blackjack')
      } else if (pBJ && dBJ) {
        bankrollReturn += b; results.push('push')
        msgs.push('Push — Both BJ')
      } else if (dTotal > 21 || pTotal > dTotal) {
        bankrollReturn += b * 2; displayDelta += b
        results.push('win')
        msgs.push(hands.length > 1 ? `M${hi+1}: +${b}€` : `Win +${b}€`)
      } else if (pTotal < dTotal) {
        results.push('lose'); displayDelta -= b
        msgs.push(hands.length > 1 ? `M${hi+1}: Lose` : 'Lose')
      } else {
        bankrollReturn += b; results.push('push')
        msgs.push(hands.length > 1 ? `M${hi+1}: Push` : 'Push')
      }
    })

    setDealerCards(dHand)
    setShoe(newShoe); setShoeIdx(newIdx); setRc(newRc)
    setPendingResult({ bankrollReturn, displayDelta, msg: msgs.join('  ·  '), results })
    setRevealCount(2)
    setPhase('revealing')
  }

  // ─ Advance to next hand or reveal ─────────────────────────
  function advance(hands, curIdx, dCards, curRc, curShoe, curShoIdx, handBets, wasSplit, surr, preRes) {
    let next = curIdx + 1
    // Skip pre-resolved hands (BJ)
    while (next < hands.length && preRes[next] != null) next++
    if (next < hands.length) {
      setActiveIdx(next)
    } else {
      startReveal(hands, dCards, curRc, curShoe, curShoIdx, handBets, wasSplit, surr, preRes)
    }
  }

  // ─ Start hand ────────────────────────────────────────────
  function startHand() {
    const total = bet * numHands
    if (bankroll < total) return

    let s = shoe, i = shoeIdx, r = rc
    if (i >= Math.floor(s.length * PENETRATION)) {
      s = shuffle(buildDeck()); i = 0; r = 0
    }

    // Traditional deal order
    const handCards = Array.from({ length: numHands }, () => [])
    for (let h = 0; h < numHands; h++) handCards[h].push(s[i++])
    const hole = s[i++]
    for (let h = 0; h < numHands; h++) handCards[h].push(s[i++])
    const up = s[i++]
    const dHand = [hole, up]

    for (let h = 0; h < numHands; h++)
      r += hiLo(handCards[h][0]) + hiLo(handCards[h][1])
    r += hiLo(up)

    const handBets = Array(numHands).fill(bet)
    setBankroll(prev => prev - total)
    setShoe(s); setShoeIdx(i); setRc(r)
    setPlayerHands(handCards); setDealerCards(dHand)
    setActiveIdx(0); setBets(handBets)
    setSurrendered([]); setIsSplitGame(false)
    setResultMsg(''); setDelta(0); setHandResults([])
    setPendingResult(null)

    const pBJs = handCards.map(h => isBlackjack(h))
    const dBJ  = isBlackjack(dHand)

    if (up.rank === 'ace') {
      // Dealer montre un As : proposer l'assurance avant de regarder le trou
      setPreHandResults(Array(numHands).fill(null))
      setInsuranceTaken(false)
      setInsuranceBet(0)
      setPhase('insurance')

    } else if (dBJ) {
      // Dealer BJ (upcard != As) — all hands end immediately via revealing
      setRc(r + hiLo(hole))
      const preRes = Array(numHands).fill(null)
      let bankrollReturn = 0, displayDelta = 0
      const msgs = [], results = []
      handCards.forEach((_h, hi) => {
        const b = bet
        if (pBJs[hi]) {
          bankrollReturn += b; results.push('push'); preRes[hi] = 'push'
          msgs.push(numHands > 1 ? `M${hi+1}: Push BJ` : 'Push — Both Blackjack!')
        } else {
          displayDelta -= b; results.push('lose'); preRes[hi] = 'lose'
          msgs.push(numHands > 1 ? `M${hi+1}: Dealer BJ` : 'Dealer Blackjack')
        }
      })
      setPreHandResults(preRes)
      setPendingResult({ bankrollReturn, displayDelta, msg: msgs.join('  ·  '), results })
      setRevealCount(2)
      setPhase('revealing')

    } else if (pBJs.every(Boolean)) {
      // All player hands BJ, dealer no BJ — all win via revealing
      const preRes = Array(numHands).fill('bj')
      let bankrollReturn = 0, displayDelta = 0
      const msgs = []
      handCards.forEach((_h, hi) => {
        const gain = Math.floor(bet * 1.5)
        bankrollReturn += bet + gain; displayDelta += gain
        msgs.push(numHands > 1 ? `M${hi+1}: BJ +${gain}€` : `Blackjack! +${gain}€`)
      })
      setPreHandResults(preRes)
      setPendingResult({ bankrollReturn, displayDelta, msg: msgs.join('  ·  '), results: preRes })
      setRevealCount(2)
      setPhase('revealing')

    } else if (pBJs.some(Boolean)) {
      // Mixed: some hands BJ, some not — apply BJ wins now, play the rest
      const preRes = pBJs.map(bj => bj ? 'bj' : null)
      let bjReturn = 0
      pBJs.forEach((bj, hi) => {
        if (bj) bjReturn += bet + Math.floor(bet * 1.5)
      })
      setBankroll(prev => prev + bjReturn)
      setPreHandResults(preRes)
      setHandResults(preRes)  // show BJ result on those hands immediately
      // Start at first non-BJ hand
      const firstPlayable = pBJs.findIndex(bj => !bj)
      setActiveIdx(firstPlayable)
      setPhase('playing')

    } else {
      // Normal — no BJ anywhere
      setPreHandResults(Array(numHands).fill(null))
      setPhase('playing')
    }
  }

  // ─ Insurance resolution ───────────────────────────────────
  function resolveAfterInsurance(taken, insBet) {
    const dBJ  = isBlackjack(dealerCards)
    const pBJs = playerHands.map(h => isBlackjack(h))

    if (dBJ) {
      // Trou révélé → compter la hole card
      setRc(prev => prev + hiLo(dealerCards[0]))
      // Insurance paie 2:1 si prise
      let bankrollReturn = taken ? insBet * 2 : 0
      let displayDelta   = taken ? insBet : 0
      const msgs = [], results = []
      if (taken) msgs.push(`Insurance +${insBet}€`)
      playerHands.forEach((_h, hi) => {
        const b = bets[hi]
        if (pBJs[hi]) {
          bankrollReturn += b; results.push('push')
          msgs.push(playerHands.length > 1 ? `M${hi+1}: Push BJ` : 'Push — Both BJ')
        } else {
          displayDelta -= b; results.push('lose')
          msgs.push(playerHands.length > 1 ? `M${hi+1}: Dealer BJ` : 'Dealer Blackjack')
        }
      })
      const preRes = playerHands.map((_, hi) => pBJs[hi] ? 'push' : 'lose')
      setPreHandResults(preRes)
      setPendingResult({ bankrollReturn, displayDelta, msg: msgs.join('  ·  '), results })
      setRevealCount(2)
      setPhase('revealing')

    } else {
      // Pas de BJ dealer — assurance perdue si prise (déjà déduite du bankroll)
      const insMsgs = taken ? [`Insurance lost -${insBet}€`] : []

      if (pBJs.every(Boolean)) {
        const preRes = Array(playerHands.length).fill('bj')
        let bankrollReturn = 0, displayDelta = taken ? -insBet : 0
        const msgs = [...insMsgs]
        playerHands.forEach((_h, hi) => {
          const gain = Math.floor(bets[hi] * 1.5)
          bankrollReturn += bets[hi] + gain; displayDelta += gain
          msgs.push(playerHands.length > 1 ? `M${hi+1}: BJ +${gain}€` : `Blackjack! +${gain}€`)
        })
        setPreHandResults(preRes)
        setPendingResult({ bankrollReturn, displayDelta, msg: msgs.join('  ·  '), results: preRes })
        setRevealCount(2)
        setPhase('revealing')

      } else if (pBJs.some(Boolean)) {
        const preRes = pBJs.map(bj => bj ? 'bj' : null)
        let bjReturn = 0
        pBJs.forEach((bj, hi) => { if (bj) bjReturn += bets[hi] + Math.floor(bets[hi] * 1.5) })
        setBankroll(prev => prev + bjReturn)
        setPreHandResults(preRes)
        setHandResults(preRes)
        const firstPlayable = pBJs.findIndex(bj => !bj)
        setActiveIdx(firstPlayable)
        setPhase('playing')

      } else {
        setPreHandResults(Array(playerHands.length).fill(null))
        setPhase('playing')
      }
    }
  }

  function doTakeInsurance() {
    const insBet = bets[0] / 2
    setBankroll(prev => prev - insBet)
    setInsuranceTaken(true)
    setInsuranceBet(insBet)
    resolveAfterInsurance(true, insBet)
  }

  function doDeclineInsurance() {
    setInsuranceTaken(false)
    setInsuranceBet(0)
    resolveAfterInsurance(false, 0)
  }

  // ─ Player actions ─────────────────────────────────────────
  function doHit() {
    const d = draw(shoe, shoeIdx, rc)
    const newRc    = d.rcBefore + hiLo(d.card)
    const newHand  = [...activeHand, d.card]
    const newHands = playerHands.map((h, i) => i === activeIdx ? newHand : h)
    setShoe(d.shoe); setShoeIdx(d.idx); setRc(newRc); setPlayerHands(newHands)
    if (isBust(newHand))
      advance(newHands, activeIdx, dealerCards, newRc, d.shoe, d.idx, bets, isSplitGame, surrendered, preHandResults)
  }

  function doStand() {
    advance(playerHands, activeIdx, dealerCards, rc, shoe, shoeIdx, bets, isSplitGame, surrendered, preHandResults)
  }

  function doDouble() {
    if (!canDouble(activeHand) || bankroll < bets[activeIdx]) return
    const d = draw(shoe, shoeIdx, rc)
    const newRc    = d.rcBefore + hiLo(d.card)
    const newHand  = [...activeHand, d.card]
    const newHands = playerHands.map((h, i) => i === activeIdx ? newHand : h)
    const newBets  = bets.map((b, i) => i === activeIdx ? b * 2 : b)
    setBankroll(prev => prev - bets[activeIdx])
    setShoe(d.shoe); setShoeIdx(d.idx); setRc(newRc)
    setPlayerHands(newHands); setBets(newBets)
    advance(newHands, activeIdx, dealerCards, newRc, d.shoe, d.idx, newBets, isSplitGame, surrendered, preHandResults)
  }

  function doSplit() {
    if (!canSplit(activeHand) || playerHands.length >= 4 || bankroll < bets[activeIdx]) return
    const d1 = draw(shoe, shoeIdx, rc)
    const rc1 = d1.rcBefore + hiLo(d1.card)
    const d2  = draw(d1.shoe, d1.idx, rc1)
    const rc2 = d2.rcBefore + hiLo(d2.card)
    const h1 = [activeHand[0], d1.card], h2 = [activeHand[1], d2.card]
    const newHands = [...playerHands.slice(0, activeIdx), h1, h2, ...playerHands.slice(activeIdx + 1)]
    const newBets  = [...bets.slice(0, activeIdx), bets[activeIdx], bets[activeIdx], ...bets.slice(activeIdx + 1)]
    // Expand preHandResults with null for the new split hand
    const newPreRes = [...preHandResults.slice(0, activeIdx), null, null, ...preHandResults.slice(activeIdx + 1)]
    setBankroll(prev => prev - bets[activeIdx])
    setShoe(d2.shoe); setShoeIdx(d2.idx); setRc(rc2)
    setPlayerHands(newHands); setBets(newBets); setIsSplitGame(true)
    setPreHandResults(newPreRes)
  }

  function doSurrender() {
    const half = bets[activeIdx] / 2
    setBankroll(prev => prev + half)
    const newSurr = [...surrendered, activeIdx]
    setSurrendered(newSurr)
    advance(playerHands, activeIdx, dealerCards, rc, shoe, shoeIdx, bets, isSplitGame, newSurr, preHandResults)
  }

  // ─ Availability ───────────────────────────────────────────
  const playing = phase === 'playing'
  const canDbl  = playing && canDouble(activeHand) && bankroll >= bets[activeIdx]
  const canSpl  = playing && canSplit(activeHand) && playerHands.length < 4 && bankroll >= bets[activeIdx]
  const canSur  = playing && canSurr(activeHand, isSplitGame)

  const dealerRevealCount = phase === 'result' ? Infinity : phase === 'playing' ? 2 : revealCount

  // ─ Render ─────────────────────────────────────────────────
  return (
    <>
      <style>{`
        @keyframes slideIn {
          from { opacity:0; transform:translateY(-20px) scale(0.88); }
          to   { opacity:1; transform:translateY(0) scale(1); }
        }
        @keyframes flipCard {
          from { opacity:0; transform:perspective(500px) rotateY(90deg) scale(0.92); }
          to   { opacity:1; transform:perspective(500px) rotateY(0deg) scale(1); }
        }
        .card-deal { animation: slideIn  0.35s cubic-bezier(0.34,1.5,0.64,1) both; }
        .card-flip { animation: flipCard 0.45s cubic-bezier(0.25,0.8,0.25,1) both; }
      `}</style>

      <div className="min-h-screen bg-gradient-to-b from-green-950 via-green-900 to-green-950 flex flex-col p-3 gap-3 select-none">

        {/* ── Header ── */}
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <h1 className="text-white font-black text-xl tracking-tight">Blackjack Trainer Pro</h1>
            <p className="text-white/30 text-xs mt-0.5">6 decks · S17 · 3:2 · Hi-Lo</p>
          </div>
          <div className="flex gap-2 flex-wrap items-start">
            <CoveredPanel hidden={!showCounter} onToggle={() => setShowCounter(v => !v)} label="Hi-Lo" icon="🃏">
              <Counter rc={rc} tc={tc} />
            </CoveredPanel>
            {/* Hint panel — affiché dans le header pendant le jeu */}
            {(phase === 'playing' || phase === 'insurance') && (
              <CoveredPanel hidden={!showHint} onToggle={() => setShowHint(v => !v)} label="Hint" icon="💡" className="min-w-36">
                <div style={{ minHeight: '64px' }}>
                  {phase === 'insurance' && insuranceHint && (
                    <div className={`rounded-xl px-3 py-2 text-xs font-bold ${
                      insuranceHint === 'take'
                        ? 'bg-yellow-500/20 border border-yellow-400/40 text-yellow-300'
                        : 'bg-white/10 border border-white/10 text-white/60'
                    }`}>
                      {insuranceHint === 'take'
                        ? `★ TC${tc >= 0 ? '+' : ''}${tc.toFixed(1)} ≥ +3 → Take Insurance`
                        : `TC${tc >= 0 ? '+' : ''}${tc.toFixed(1)} < +3 → No Insurance`
                      }
                    </div>
                  )}
                  {phase === 'playing' && (hint
                    ? <HintBox hint={hint} />
                    : <div className="min-w-36 min-h-12 rounded-xl bg-black/20 border border-white/5" />
                  )}
                </div>
              </CoveredPanel>
            )}
            {/* Bankroll */}
            <div className="bg-black/40 border border-white/10 rounded-xl px-4 py-3 flex flex-col gap-1.5 min-w-40">
              <span className="text-white/40 text-xs font-bold tracking-widest uppercase">Bankroll</span>
              <span className={`font-black text-2xl leading-none ${bankroll <= 0 ? 'text-red-400' : 'text-yellow-400'}`}>
                {bankroll.toFixed(0)} €
              </span>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="text-white/40 text-xs">Bet</span>
                <button onClick={() => setBet(v => Math.max(MIN_BET, v - BET_STEP))}
                  disabled={phase !== 'betting' || bet <= MIN_BET}
                  className="w-6 h-6 bg-white/10 hover:bg-white/20 disabled:opacity-30 rounded text-white text-sm font-bold transition-colors">−</button>
                <span className="text-white font-bold text-sm min-w-10 text-center">{bet}€</span>
                <button onClick={() => setBet(v => Math.min(MAX_BET, Math.min(bankroll, v + BET_STEP)))}
                  disabled={phase !== 'betting' || bet >= Math.min(MAX_BET, bankroll)}
                  className="w-6 h-6 bg-white/10 hover:bg-white/20 disabled:opacity-30 rounded text-white text-sm font-bold transition-colors">+</button>
              </div>
            </div>
          </div>
        </div>

        {/* ── Table ── */}
        <div className="flex-1 flex flex-col gap-2 max-w-2xl mx-auto w-full">
          <div className="bg-black/25 border border-white/5 rounded-2xl p-4 min-h-36 flex flex-col items-center justify-center">
            {dealerCards.length > 0
              ? <HandDisplay cards={dealerCards} label="Dealer"
                  hideFirst={phase === 'playing' || phase === 'insurance'}
                  revealCount={dealerRevealCount}
                  isRevealing={phase === 'revealing'} />
              : <span className="text-white/15 text-sm">Dealer</span>
            }
          </div>

          {phase === 'result' && resultMsg && (
            <div className={`text-center rounded-2xl py-3 px-5 font-black shadow-xl border
              ${delta > 0 ? 'bg-emerald-600/90 border-emerald-500 text-white'
              : delta < 0 ? 'bg-red-600/90 border-red-500 text-white'
              : 'bg-gray-600/90 border-gray-500 text-white'}`}>
              <div className="text-base">{resultMsg}</div>
              {delta !== 0 && <div className="text-sm font-bold opacity-70 mt-0.5">Net: {delta > 0 ? `+${delta}€` : `${delta}€`}</div>}
            </div>
          )}

          <div className="bg-black/25 border border-white/5 rounded-2xl p-4 min-h-36 flex flex-col items-center justify-center">
            {playerHands.length > 0
              ? <div className="flex gap-3 flex-wrap justify-center">
                  {[...playerHands].map((_, di) => {
                    const i = playerHands.length - 1 - di  // Main 1 à droite
                    return (
                      <HandDisplay key={i} cards={playerHands[i]}
                        label={playerHands.length > 1 ? `Hand ${i+1}` : 'You'}
                        active={playing && i === activeIdx}
                        result={handResults[i] ?? null}
                        bet={bets[i] ?? bet} />
                    )
                  })}
                </div>
              : <span className="text-white/15 text-sm">Your hands</span>
            }
          </div>
        </div>

        {/* ── Controls ── */}
        <div className="flex flex-col items-center gap-3 max-w-2xl mx-auto w-full">

          {/* Playing: action buttons */}
          {playing && (
            <div className="flex flex-col gap-2">
              <div className="grid grid-cols-2 gap-2">
                <ActionBtn label="Hit"    onClick={doHit}    enabled={true} />
                <ActionBtn label="Stand"  onClick={doStand}  enabled={true} />
                <ActionBtn label="Double" onClick={doDouble} enabled={canDbl} />
                <ActionBtn label="Split"  onClick={doSplit}  enabled={canSpl} />
              </div>
              <ActionBtn label="Surrender" onClick={doSurrender} enabled={canSur} />
            </div>
          )}

          {/* Insurance */}
          {phase === 'insurance' && (
            <div className="flex flex-col items-center gap-3">
              <div className="bg-yellow-500/15 border border-yellow-400/30 rounded-2xl px-6 py-3 text-center">
                <p className="text-yellow-300 font-bold text-base">Dealer shows Ace</p>
                <p className="text-white/50 text-sm">Insurance pays 2:1 · bet: {bets[0] / 2}€</p>
              </div>
              <div className="flex gap-3">
                <button onClick={doTakeInsurance}
                  className="px-6 py-3 bg-yellow-500 hover:bg-yellow-400 active:scale-95 text-gray-900 font-black rounded-xl shadow-xl transition-all">
                  Take Insurance ({bets[0] / 2}€)
                </button>
                <button onClick={doDeclineInsurance}
                  className="px-6 py-3 bg-white/10 hover:bg-white/20 active:scale-95 text-white font-bold rounded-xl transition-all">
                  No Thanks
                </button>
              </div>
            </div>
          )}

          {/* Betting */}
          {phase === 'betting' && (
            <div className="flex flex-col items-center gap-4">
              <div className="flex items-center gap-3">
                <span className="text-white/40 text-sm">Hands:</span>
                {[1,2,3].map(n => (
                  <button key={n} onClick={() => setNumHands(n)}
                    className={`w-10 h-10 rounded-xl font-bold text-lg transition-all
                      ${numHands === n ? 'bg-yellow-500 text-gray-900 scale-110 shadow-lg' : 'bg-white/10 text-white/60 hover:bg-white/20'}`}>
                    {n}
                  </button>
                ))}
              </div>
              {numHands > 1 && <p className="text-white/25 text-xs">{bet}€ × {numHands} = {bet * numHands}€</p>}
              <button onClick={startHand} disabled={bankroll < bet * numHands}
                className="px-14 py-4 bg-yellow-500 hover:bg-yellow-400 disabled:opacity-40 active:scale-95 text-gray-900 font-black text-xl rounded-2xl shadow-xl transition-all">
                Deal
              </button>
            </div>
          )}

          {phase === 'revealing' && (
            <p className="text-white/30 text-sm animate-pulse">Dealer playing…</p>
          )}

          {phase === 'result' && (
            <button onClick={() => { setPhase('betting'); setHandResults([]); setPendingResult(null) }}
              className="px-14 py-4 bg-yellow-500 hover:bg-yellow-400 active:scale-95 text-gray-900 font-black text-xl rounded-2xl shadow-xl transition-all">
              Next hand →
            </button>
          )}

          <p className="text-white/20 text-xs">
            {shoe.length - shoeIdx} cards · {decksLeft.toFixed(1)} decks remaining
            {shoeIdx >= Math.floor(shoe.length * PENETRATION * 0.9) && ' · Shuffle soon 🔀'}
          </p>
        </div>
      </div>
    </>
  )
}
