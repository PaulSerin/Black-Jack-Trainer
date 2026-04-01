// blackjack.jsx - Blackjack Trainer Pro
import { useState, useMemo, useEffect, useRef } from 'react'
import basicStrategyImg from '../docs/references/basic-blackjack-strategy-chart.png'
import i18Img          from '../docs/references/Illustrious_18_Deviations.png'

// URL du simulateur Streamlit - configurable via react/.env (VITE_SIMULATOR_URL)
const SIMULATOR_URL = import.meta.env.VITE_SIMULATOR_URL || 'http://localhost:8501'

// ── Constants ─────────────────────────────────────────────────
const NUM_DECKS   = 6
const PENETRATION = 0.75
const INIT_BANK   = 1000
const MAX_BET     = 500

const DEFAULT_CONFIG = {
  bjPayout:           1.5,    // 1.5 = 3:2,  1.2 = 6:5
  dealerHitsSoft17:   false,  // false = S17, true = H17
  lateSurrender:      true,
  doubleRestriction:  'any',  // 'any' | '9-11' | '10-11'
  doubleAfterSplit:   true,
  maxSplitHands:      4,      // max total hands via splits (2,3,4)
  resplitAces:        false,
  numDecks:           6,
  penetration:        0.75,
}

const SUITS = ['clubs','diamonds','hearts','spades']
const RANKS = ['2','3','4','5','6','7','8','9','10','jack','queen','king','ace']
const RANK_VALUES = {
  '2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
  '10':10,'jack':10,'queen':10,'king':10,'ace':11,
}
const UPCARD_ORDER = ['2','3','4','5','6','7','8','9','10','ace']

const RANK_LABEL = {
  'ace':'A','2':'2','3':'3','4':'4','5':'5','6':'6',
  '7':'7','8':'8','9':'9','10':'10','jack':'J','queen':'Q','king':'K',
}

const SUIT_CHAR  = { clubs:'♣', diamonds:'♦', hearts:'♥', spades:'♠' }
const SUIT_COLOR = { clubs:'#1a1a1a', spades:'#1a1a1a', hearts:'#cc1111', diamonds:'#cc1111' }

const CHIPS = [
  { value: 2,   fill:'#d4d4d8', text:'#1a1a1a', stroke:'#a1a1aa' },
  { value: 5,   fill:'#c0392b', text:'#fff',    stroke:'#e74c3c' },
  { value: 10,  fill:'#2563eb', text:'#fff',    stroke:'#3b82f6' },
  { value: 20,  fill:'#7c3aed', text:'#fff',    stroke:'#8b5cf6' },
  { value: 50,  fill:'#16a34a', text:'#fff',    stroke:'#22c55e' },
  { value: 100, fill:'#1a1a1a', text:'#f0c040', stroke:'#f0c040' },
  { value: 200, fill:'#c2410c', text:'#fff',    stroke:'#f97316' },
  { value: 500, fill:'#6c1a2a', text:'#f0c040', stroke:'#f0c040' },
]

// ── Pure game logic ───────────────────────────────────────────
function buildDeck(n = NUM_DECKS) {
  const cards = []
  for (let d = 0; d < n; d++)
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

// ── Hi-Lo ─────────────────────────────────────────────────────
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

// ── SVG Card ──────────────────────────────────────────────────
function SVGCard({ card, faceDown, animCls = '', animDelay = 0 }) {
  const W = 70, H = 98
  const wrapStyle = animCls
    ? { animationDelay: `${animDelay}s`, animationFillMode: 'both' }
    : undefined

  if (faceDown || !card) {
    return (
      <div className={`flex-shrink-0 ${animCls}`} style={wrapStyle}>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} xmlns="http://www.w3.org/2000/svg"
          style={{ display:'block', filter:'drop-shadow(0 3px 8px rgba(0,0,0,0.6))' }}>
          <rect width={W} height={H} rx="7" fill="white"/>
          <rect x="2" y="2" width={W-4} height={H-4} rx="6" fill="#1a2a6c"/>
          {Array.from({length:7}, (_,row) =>
            Array.from({length:5}, (_,col) => {
              const cx = 7 + col * 12, cy = 9 + row * 13
              return (
                <polygon key={`${row}-${col}`}
                  points={`${cx},${cy-4} ${cx+5},${cy} ${cx},${cy+4} ${cx-5},${cy}`}
                  fill="#2a3a8c"/>
              )
            })
          )}
          <rect x="4" y="4" width={W-8} height={H-8} rx="5" fill="none"
            stroke="#f0c040" strokeWidth="1"/>
        </svg>
      </div>
    )
  }

  const sym = SUIT_CHAR[card.suit]
  const col = SUIT_COLOR[card.suit]
  const lbl = RANK_LABEL[card.rank]
  const isWide = lbl === '10'

  return (
    <div className={`flex-shrink-0 ${animCls}`} style={wrapStyle}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} xmlns="http://www.w3.org/2000/svg"
        style={{ display:'block', filter:'drop-shadow(0 3px 8px rgba(0,0,0,0.6))' }}>
        <rect width={W} height={H} rx="7" fill="white" stroke="#d1d5db" strokeWidth="0.5"/>
        <text x={isWide ? 4 : 5} y="15"
          fontFamily="'Rajdhani',sans-serif" fontWeight="700" fontSize="13" fill={col}>{lbl}</text>
        <text x="7" y="27" textAnchor="middle"
          fontFamily="Arial,sans-serif" fontSize="11" fill={col}>{sym}</text>
        <text x={W/2} y={H/2 + 2} textAnchor="middle" dominantBaseline="central"
          fontFamily="Arial,sans-serif" fontSize="36" fill={col}>{sym}</text>
        <g transform={`translate(${W},${H}) rotate(180)`}>
          <text x={isWide ? 4 : 5} y="15"
            fontFamily="'Rajdhani',sans-serif" fontWeight="700" fontSize="13" fill={col}>{lbl}</text>
          <text x="7" y="27" textAnchor="middle"
            fontFamily="Arial,sans-serif" fontSize="11" fill={col}>{sym}</text>
        </g>
      </svg>
    </div>
  )
}

// ── Hand display ──────────────────────────────────────────────
function HandDisplay({ cards, label, hideFirst = false, active = false,
                       result = null, bet = 0, revealCount = Infinity, isRevealing = false,
                       breatheHidden = false, cardDelays = null, badge = null }) {
  const shown   = cards.slice(0, Math.min(cards.length, revealCount))
  const seenIds = useRef(new Set())
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
    <div className={`flex flex-col items-center gap-1.5 px-3 py-2 rounded-xl transition-all duration-300 ${ring} ${bj ? 'bj-glow' : ''}`}>
      <div className="flex items-center gap-1.5">
        <span className="text-white/50 text-xs uppercase tracking-wider font-semibold">{label}</span>
        {bet > 0 && <span className="text-yellow-400/60 text-xs font-bold">{Math.round(bet)}€</span>}
      </div>
      <div className="flex items-end" style={{ minHeight:'98px' }}>
        {shown.map((card, i) => {
          const fd     = hideFirst && i === 0
          const realId = fd ? `back-${card.id}` : card.id
          const isNew  = !seenIds.current.has(realId)
          if (isNew) seenIds.current.add(realId)
          const cls = isRevealing
            ? (i === 0 ? 'card-flip' : i >= 2 ? 'card-deal' : '')
            : isNew ? 'card-deal' : ''
          const delay = cardDelays?.[i] !== undefined ? cardDelays[i] : 0
          const n = shown.length
          const offset = n <= 2 ? -34 : n === 3 ? -28 : -24
          const mid = (n - 1) / 2
          const rot = n >= 3 ? (i - mid) * 2.5 : 0
          return (
            <div key={realId}
              className={fd && breatheHidden ? 'card-breathe' : ''}
              style={{
                marginLeft: i > 0 ? `${offset}px` : 0,
                zIndex: i + 1,
                position: 'relative',
                transform: `rotate(${rot}deg)`,
                transformOrigin: 'bottom center',
              }}>
              <SVGCard card={card} faceDown={fd} animCls={cls} animDelay={delay} />
            </div>
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
      {badge && (
        <div style={{
          padding:'4px 14px', borderRadius:'20px', fontWeight:800, fontSize:'13px', letterSpacing:'0.5px',
          background: badge.type === 'bj'   ? '#b8860b'
                    : badge.type === 'win'  ? '#059669'
                    : badge.type === 'lose' ? '#dc2626'
                    : '#475569',
          color: '#fff',
          boxShadow: badge.type === 'bj'   ? '0 0 12px rgba(240,192,64,0.4)'
                   : badge.type === 'win'  ? '0 0 12px rgba(5,150,105,0.4)'
                   : badge.type === 'lose' ? '0 0 12px rgba(220,38,38,0.3)'
                   : 'none',
          animation: 'badgePop 0.2s cubic-bezier(0.34,1.56,0.64,1) both',
        }}>
          {badge.label}
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
        {hint.isDeviation ? '★ I18 Deviation' : 'Best Play'}
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

// ── Covered panel ─────────────────────────────────────────────
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
    </div>
  )
}

// ── Hi-Lo counter ─────────────────────────────────────────────
function Counter({ rc, tc }) {
  const tcColor = tc >= 2 ? '#4ade80' : tc >= 1 ? '#a3e635' : tc <= -2 ? '#f87171' : tc < 0 ? '#fb923c' : '#ffffff'
  return (
    <div style={{ background:'#0d2214', border:'1px solid #2a5a3a', borderRadius:'10px', padding:'8px 12px' }}>
      <div style={{ color:'#f0c040', fontSize:'9px', fontWeight:700, letterSpacing:'2px', textTransform:'uppercase', marginBottom:'6px' }}>
        HI-LO
      </div>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', gap:'12px' }}>
        <div>
          <div style={{ color:'rgba(255,255,255,0.4)', fontSize:'9px' }}>RC</div>
          <div style={{ color: rc > 0 ? '#4ade80' : rc < 0 ? '#f87171' : '#fff', fontSize:'26px', fontWeight:900, lineHeight:1 }}>
            {rc > 0 ? '+' : ''}{rc}
          </div>
        </div>
        <div style={{ textAlign:'right' }}>
          <div style={{ color:'rgba(255,255,255,0.4)', fontSize:'9px' }}>TC</div>
          <div style={{ color: tcColor, fontSize:'26px', fontWeight:900, lineHeight:1 }}>
            {tc > 0 ? '+' : ''}{tc.toFixed(1)}
          </div>
        </div>
      </div>
      {Math.abs(tc) >= 1 && (
        <div style={{ color: tcColor, fontSize:'9px', textAlign:'center', marginTop:'4px', opacity:0.8 }}>
          {tc >= 1 ? '▲ Favorable' : '▼ Unfavorable'}
        </div>
      )}
    </div>
  )
}

// ── SVG Chip ──────────────────────────────────────────────────
function ChipSVG({ chip, size = 52, disabled = false, onClick }) {
  const S = size, R = S / 2
  const lbl = String(chip.value)
  return (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}
      style={{ cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.3 : 1,
        transition: 'transform 0.15s, filter 0.15s', display: 'block' }}
      onClick={disabled ? undefined : onClick}
      onMouseEnter={e => { if (!disabled) { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.filter = 'drop-shadow(0 6px 10px rgba(0,0,0,0.5))' }}}
      onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.filter = 'none' }}
      onMouseDown={e => { if (!disabled) e.currentTarget.style.transform = 'scale(0.92)' }}
      onMouseUp={e => { if (!disabled) e.currentTarget.style.transform = 'translateY(-4px)' }}
    >
      <circle cx={R} cy={R} r={R-1} fill={chip.stroke}/>
      <circle cx={R} cy={R} r={R-3} fill={chip.fill}/>
      {/* Double-cercle pointillé uniforme sur tous les jetons */}
      <circle cx={R} cy={R} r={R-5}  fill="none" stroke="rgba(255,255,255,0.32)" strokeWidth="1.5" strokeDasharray="4 3"/>
      <circle cx={R} cy={R} r={R-10} fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1"   strokeDasharray="4 3"/>
      <text x={R} y={R} textAnchor="middle" dominantBaseline="central"
        fontFamily="'Rajdhani',sans-serif" fontWeight="700"
        fontSize={lbl.length > 2 ? Math.round(S * 0.21) : Math.round(S * 0.25)} fill={chip.text}>
        {lbl}
      </text>
    </svg>
  )
}

// ── Shoe visual ───────────────────────────────────────────────
function ShoeVisual({ cardsLeft, totalCards }) {
  const fillRatio = totalCards > 0 ? cardsLeft / totalCards : 0
  const barH      = Math.round(fillRatio * 76)
  const fillCol   = fillRatio > 0.5 ? '#4ade80' : fillRatio > 0.25 ? '#fbbf24' : '#f87171'
  // 3D top/side faces
  const W = 58, H = 104, depth = 10
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:'4px', flexShrink:0 }}>
      <svg width={W + depth} height={H + depth} viewBox={`0 0 ${W + depth} ${H + depth}`}
        style={{ display:'block', filter:'drop-shadow(0 4px 10px rgba(0,0,0,0.6))' }}>
        {/* Right side face (3D) */}
        <polygon points={`${W},4 ${W+depth},4 ${W+depth},${H+depth} ${W},${H}`}
          fill="#0e0905"/>
        {/* Bottom face (3D) */}
        <polygon points={`4,${H} ${W},${H} ${W+depth},${H+depth} ${4+depth},${H+depth}`}
          fill="#0a0704"/>
        {/* Top face (3D) */}
        <polygon points={`4,4 ${W},4 ${W+depth},4 ${4+depth},4`}
          fill="#3a2810"/>
        {/* Main front face */}
        <rect x="2" y="2" width={W} height={H} rx="6"
          fill="#1e1408" stroke="#5a3e18" strokeWidth="1.5"/>
        {/* Highlight stripe */}
        <rect x="2" y="2" width={W * 0.45} height={H} rx="6"
          fill="rgba(255,255,255,0.04)"/>
        {/* Card slot at top */}
        <rect x="9" y="3" width={W - 18} height="9" rx="3"
          fill="#08050200" stroke="#3a2810" strokeWidth="0.5"/>
        <rect x="9" y="3" width={W - 18} height="9" rx="3" fill="#080502"/>
        {/* Inner recessed panel */}
        <rect x="9" y="17" width={W - 22} height="76" rx="4"
          fill="#0f0a04" stroke="#3a2810" strokeWidth="0.75"/>
        {/* Fill bar bg */}
        <rect x={W - 10} y="18" width="6" height="74" rx="3"
          fill="rgba(255,255,255,0.07)"/>
        {/* Fill bar */}
        {barH > 0 && (
          <rect x={W - 10} y={92 - barH} width="6" height={barH} rx="3" fill={fillCol}/>
        )}
        {/* Gold corner brackets */}
        {[[4,4],[W-8,4],[4,H-8],[W-8,H-8]].map(([x,y],k) => (
          <rect key={k} x={x} y={y} width="8" height="8" rx="1.5"
            fill="none" stroke="rgba(200,151,42,0.55)" strokeWidth="1.25"/>
        ))}
        {/* Logo */}
        <text x={W / 2 - 5} y={H / 2 + 2} textAnchor="middle" dominantBaseline="central"
          fill="rgba(200,151,42,0.28)" fontSize="11" fontFamily="Georgia,serif"
          letterSpacing="3" transform={`rotate(-90,${W/2 - 5},${H/2 + 2})`}>SHOE</text>
      </svg>
      <div style={{ color: fillRatio <= 0.25 ? fillCol : 'rgba(255,255,255,0.4)',
        fontSize:'10px', fontWeight: fillRatio <= 0.25 ? 700 : 400, letterSpacing:'0.5px' }}>
        {cardsLeft} cards
      </div>
    </div>
  )
}

// ── Discard pile ──────────────────────────────────────────────
function DiscardPile({ count }) {
  const layers = count === 0 ? 0 : Math.min(1 + Math.floor(count / 4), 9)
  const CW = 46, CH = 66  // card dimensions in discard pile
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:'4px', flexShrink:0 }}>
      <div style={{ position:'relative', width:`${CW}px`, height:`${CH + layers * 3 + 10}px`,
        display:'flex', alignItems:'flex-end', justifyContent:'center' }}>
        {count === 0
          ? <div style={{ width:`${CW}px`, height:`${CH}px`,
              border:'1px dashed rgba(255,255,255,0.1)', borderRadius:'5px' }} />
          : Array.from({ length: layers }, (_, idx) => (
            <svg key={idx} width={CW} height={CH} viewBox={`0 0 ${CW} ${CH}`}
              style={{ display:'block', position:'absolute', bottom:`${idx * 3}px`, left:0,
                filter:'drop-shadow(0 2px 4px rgba(0,0,0,0.55))' }}>
              <rect width={CW} height={CH} rx="5" fill="white"/>
              <rect x="1" y="1" width={CW-2} height={CH-2} rx="4.5" fill="#1a2a6c"/>
              {Array.from({length:6}, (_,row) =>
                Array.from({length:4}, (_,col) => {
                  const cx = 6 + col * 9, cy = 7 + row * 9
                  return <polygon key={`${row}-${col}`}
                    points={`${cx},${cy-3} ${cx+4},${cy} ${cx},${cy+3} ${cx-4},${cy}`}
                    fill="#2a3a8c"/>
                })
              )}
              <rect x="2" y="2" width={CW-4} height={CH-4} rx="4" fill="none"
                stroke="rgba(240,192,64,0.55)" strokeWidth="0.8"/>
            </svg>
          ))
        }
      </div>
      <div style={{ color:'rgba(255,255,255,0.35)', fontSize:'10px' }}>
        {count > 0 ? `${count} disc.` : 'discard'}
      </div>
    </div>
  )
}

// ── Action button ─────────────────────────────────────────────
const ACTION_BTN_STYLE = {
  Hit:       { bg:'#f59e0b', text:'#1a1a1a' },
  Stand:     { bg:'#059669', text:'#fff'    },
  Double:    { bg:'#2563eb', text:'#fff'    },
  Split:     { bg:'#64748b', text:'#fff'    },
  Surrender: { bg:'#dc2626', text:'#fff'    },
}

function ActionBtn({ label, onClick, enabled }) {
  const s = ACTION_BTN_STYLE[label] ?? { bg:'#374151', text:'#fff' }
  return (
    <button onClick={enabled ? onClick : undefined} disabled={!enabled}
      style={{ background: s.bg, color: s.text, border:'none', borderRadius:'10px',
        padding:'0 20px', height:'52px', minWidth:'110px',
        fontFamily:"'Rajdhani',sans-serif", fontWeight:700, fontSize:'15px', letterSpacing:'0.5px',
        cursor: enabled ? 'pointer' : 'not-allowed', opacity: enabled ? 1 : 0.3,
        transition:'transform 0.12s, filter 0.12s',
        boxShadow: enabled ? '0 4px 12px rgba(0,0,0,0.3)' : 'none' }}
      onMouseEnter={e => { if (enabled) { e.currentTarget.style.filter='brightness(1.15)'; e.currentTarget.style.transform='translateY(-2px)' }}}
      onMouseLeave={e => { e.currentTarget.style.filter='none'; e.currentTarget.style.transform='translateY(0)' }}
      onMouseDown={e => { if (enabled) e.currentTarget.style.transform='scale(0.96)' }}
      onMouseUp={e => { if (enabled) e.currentTarget.style.transform='translateY(-2px)' }}
    >
      {label}
    </button>
  )
}

// ── Bet helpers ───────────────────────────────────────────────
function buildChipsFromAmount(amount) {
  let rem = Math.floor(amount)
  const chips = []
  const sorted = [...CHIPS].sort((a, b) => b.value - a.value)
  for (const c of sorted) {
    while (rem >= c.value && chips.reduce((s,v)=>s+v,0) + c.value <= MAX_BET) {
      chips.push(c.value); rem -= c.value
    }
  }
  return chips
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
  const [preHandResults, setPreHandResults] = useState([])

  // ─ Bankroll ─
  const [bankroll, setBankroll] = useState(INIT_BANK)
  const [bets,     setBets]     = useState([])

  // ─ Per-hand bet chips - spots dynamiques (1 à 6) ─────────
  const [handBetChips,     setHandBetChips]     = useState([[]])
  const [lastHandBetChips, setLastHandBetChips] = useState([[]])
  const [selectedBetHand,  setSelectedBetHand]  = useState(0)
  // IDs stables par spot pour les animations React (key)
  const [spotIds,          setSpotIds]          = useState([0])
  const [nextSpotId,       setNextSpotId]       = useState(1)
  const [hoveredSpot,      setHoveredSpot]      = useState(null)
  const [removingSpotId,   setRemovingSpotId]   = useState(null)

  // ─ Phase & animation ─
  const [phase,         setPhase]         = useState('betting')
  const [revealCount,   setRevealCount]   = useState(0)
  const [pendingResult, setPendingResult] = useState(null)

  // ─ Result display ─
  const [resultMsg,   setResultMsg]   = useState('')
  const [delta,       setDelta]       = useState(0)
  const [handResults, setHandResults] = useState([])

  // ─ Insurance (par main) ─
  const [insHandIdx,  setInsHandIdx]  = useState(0)
  const [insDecisions, setInsDecisions] = useState([])

  // ─ Shuffle banner ─
  const [showShuffle, setShowShuffle] = useState(false)

  // ─ Session stats ─
  const [sessionHands, setSessionHands] = useState(0)
  const [sessionWins,  setSessionWins]  = useState(0)
  const [sessionDelta, setSessionDelta] = useState(0)

  // ─ Round delta brief display ─
  const [showRoundDelta, setShowRoundDelta] = useState(false)

  // ─ Chip usage counters (session) ─
  const [chipUsage, setChipUsage] = useState({})

  // ─ Shoe/discard animation ─
  const [discardCount, setDiscardCount] = useState(0)
  const [dealRoundKey, setDealRoundKey] = useState(0)
  // Per-card deal delays (keyed by 'pN' for player hand N, 'd' for dealer)
  const dealDelays = useRef({})

  // ─ UI toggles ─
  const [showHint,     setShowHint]     = useState(true)
  const [showHiLo,     setShowHiLo]     = useState(true)
  const [showBSOverlay,  setShowBSOverlay]  = useState(false)
  const [showI18Overlay, setShowI18Overlay] = useState(false)
  const [bsHov,          setBsHov]          = useState(false)
  const [i18Hov,         setI18Hov]         = useState(false)

  // ─ Session mistakes ─
  const [sessionMistakes,  setSessionMistakes]  = useState(0)
  const [sessionDecisions, setSessionDecisions] = useState(0)

  // ─ Bankroll edit ─
  const [editingBankroll, setEditingBankroll] = useState(false)
  const [bankrollInput,   setBankrollInput]   = useState('')
  const bankrollInputRef = useRef(null)

  // ─ Game config ────────────────────────────────────────────
  const [gameConfig,   setGameConfig]   = useState(DEFAULT_CONFIG)
  const [showSettings, setShowSettings] = useState(false)
  const [editConfig,   setEditConfig]   = useState(DEFAULT_CONFIG)

  // ─ Derived ─
  const decksLeft = (shoe.length - shoeIdx) / 52
  const tc        = useMemo(() => calcTC(rc, decksLeft), [rc, decksLeft])
  const activeHand = playerHands[activeIdx] ?? []
  const upcard     = dealerCards[1] ?? null

  // Per-hand computed bet amounts
  const handBetAmounts = handBetChips.map(chips => chips.reduce((s,v)=>s+v, 0))
  const numSpots = spotIds.length
  // Active spots : spots avec mise > 0 (ignorés si vides au Deal)
  const activeSlots = handBetAmounts.map((b, i) => ({ slot: i, bet: b })).filter(x => x.bet > 0)
  const canDeal = activeSlots.length > 0
    && bankroll >= activeSlots.reduce((s, x) => s + x.bet, 0)

  // canSur doit être défini AVANT le useMemo hint (sinon TDZ → ReferenceError)
  const playing = phase === 'playing'
  const canSur  = playing && canSurr(activeHand, isSplitGame) && gameConfig.lateSurrender

  const hint = useMemo(() => {
    if (phase !== 'playing' || !upcard || !activeHand.length) return null
    if (preHandResults[activeIdx] != null) return null
    const h = getHint(activeHand, upcard, tc)
    if (!h) return null
    // Si Surrender recommandé mais non disponible → fallback Hit (BS sans surrender)
    if (h.action === 'SUR' && !canSur) {
      return { ...h, action: 'H' }
    }
    // Si Double recommandé mais main > 2 cartes → fallback D→H, Ds→S
    if ((h.action === 'D' || h.action === 'Ds') && !canDouble(activeHand)) {
      const fallback = h.action === 'Ds' ? 'S' : 'H'
      return { ...h, action: fallback }
    }
    return h
  }, [phase, activeHand, upcard, tc, activeIdx, preHandResults, playerHands, dealerCards, canSur])

  const insuranceHint = phase === 'insurance' ? (tc >= 3 ? 'take' : 'decline') : null

  // ─ Mistake tracking ───────────────────────────────────────
  function trackDecision(playerAction) {
    if (!hint) return
    setSessionDecisions(n => n + 1)
    const normAction = a => a === 'Ds' ? 'D' : a === 'Y/N' ? 'Y' : a
    if (normAction(playerAction) !== normAction(hint.action)) {
      setSessionMistakes(n => n + 1)
    }
  }

  // ─ Fermeture overlays via Échap ──────────────────────────
  useEffect(() => {
    const onKey = e => {
      if (e.key === 'Escape') { setShowBSOverlay(false); setShowI18Overlay(false) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // ─ Dealer reveal + session stats ──────────────────────────
  useEffect(() => {
    if (phase !== 'revealing') return
    const t = setTimeout(() => {
      if (revealCount >= dealerCards.length) {
        if (pendingResult) {
          setBankroll(prev => prev + pendingResult.bankrollReturn)
          setResultMsg(pendingResult.msg)
          setDelta(pendingResult.displayDelta)
          setHandResults(pendingResult.results)
          // Session stats - compté par main individuelle
          const handWins = pendingResult.results.filter(r => r === 'win' || r === 'bj').length
          setSessionHands(n => n + pendingResult.results.length)
          setSessionWins(n => n + handWins)
          setSessionDelta(n => n + pendingResult.displayDelta)
          setShowRoundDelta(true)
        }
        setPhase('result')
      } else {
        setRevealCount(n => n + 1)
      }
    }, 450)
    return () => clearTimeout(t)
  }, [phase, revealCount, dealerCards.length, pendingResult])

  // ─ Round delta auto-hide ───────────────────────────────────
  useEffect(() => {
    if (!showRoundDelta) return
    const t = setTimeout(() => setShowRoundDelta(false), 3000)
    return () => clearTimeout(t)
  }, [showRoundDelta])

  // ─ Shuffle banner auto-hide ───────────────────────────────
  useEffect(() => {
    if (!showShuffle) return
    const t = setTimeout(() => setShowShuffle(false), 2000)
    return () => clearTimeout(t)
  }, [showShuffle])

  // ─ Shoe helpers ───────────────────────────────────────────
  function draw(s, i, r) {
    if (i >= Math.floor(s.length * gameConfig.penetration)) {
      s = shuffle(buildDeck(gameConfig.numDecks)); i = 0; r = 0
    }
    return { card: s[i], shoe: s, idx: i + 1, rcBefore: r }
  }

  // ─ Compute full dealer hand ───────────────────────────────
  function computeDealer(dCards, curRc, curShoe, curIdx) {
    let s = curShoe, i = curIdx, r = curRc
    const hand = [...dCards]
    r += hiLo(hand[0])
    const mustHit = h =>
      handValue(h) < 17 || (gameConfig.dealerHitsSoft17 && handValue(h) === 17 && isSoft(h))
    while (mustHit(hand)) {
      const d = draw(s, i, r)
      s = d.shoe; i = d.idx; r = d.rcBefore + hiLo(d.card)
      hand.push(d.card)
    }
    return { hand, newShoe: s, newIdx: i, newRc: r }
  }

  // ─ Start dealer reveal ────────────────────────────────────
  function startReveal(hands, dCards, curRc, curShoe, curIdx, handBets, wasSplit, surr, preRes) {
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
      if (preRes[hi] != null) {
        const gain = Math.floor(b * gameConfig.bjPayout)
        results.push(preRes[hi])
        if (preRes[hi] === 'bj') {
          displayDelta += gain
          msgs.push(hands.length > 1 ? `H${hi+1}: BJ +${gain}€` : `Blackjack! +${gain}€`)
        } else if (preRes[hi] === 'push') {
          msgs.push(hands.length > 1 ? `H${hi+1}: Push BJ` : 'Push - Both BJ')
        } else {
          displayDelta -= b
          msgs.push(hands.length > 1 ? `H${hi+1}: Dealer BJ` : 'Dealer Blackjack')
        }
        return
      }
      if (surr.includes(hi)) {
        results.push('lose'); displayDelta -= b / 2
        msgs.push(hands.length > 1 ? `H${hi+1}: Surrender` : 'Surrender')
        return
      }
      const pTotal = handValue(hand)
      const pBJ    = isBlackjack(hand, wasSplit)
      if (isBust(hand)) {
        results.push('lose'); displayDelta -= b
        msgs.push(hands.length > 1 ? `H${hi+1}: Bust` : 'Bust')
      } else if (pBJ && !dBJ) {
        const gain = Math.floor(b * gameConfig.bjPayout)
        bankrollReturn += b + gain; displayDelta += gain
        results.push('bj')
        msgs.push(hands.length > 1 ? `H${hi+1}: BJ +${gain}€` : `Blackjack! +${gain}€`)
      } else if (dBJ && !pBJ) {
        results.push('lose'); displayDelta -= b
        msgs.push(hands.length > 1 ? `H${hi+1}: Dealer BJ` : 'Dealer Blackjack')
      } else if (pBJ && dBJ) {
        bankrollReturn += b; results.push('push')
        msgs.push('Push - Both BJ')
      } else if (dTotal > 21 || pTotal > dTotal) {
        bankrollReturn += b * 2; displayDelta += b
        results.push('win')
        msgs.push(hands.length > 1 ? `H${hi+1}: +${b}€` : `Win +${b}€`)
      } else if (pTotal < dTotal) {
        results.push('lose'); displayDelta -= b
        msgs.push(hands.length > 1 ? `H${hi+1}: Lose` : 'Lose')
      } else {
        bankrollReturn += b; results.push('push')
        msgs.push(hands.length > 1 ? `H${hi+1}: Push` : 'Push')
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
    while (next < hands.length && preRes[next] != null) next++
    if (next < hands.length) {
      setActiveIdx(next)
    } else {
      startReveal(hands, dCards, curRc, curShoe, curShoIdx, handBets, wasSplit, surr, preRes)
    }
  }

  // ─ Chip bet handlers ──────────────────────────────────────
  function addChip(chipValue) {
    if (phase !== 'betting') return
    const currentBet = handBetAmounts[selectedBetHand]
    if (currentBet + chipValue > MAX_BET || currentBet + chipValue > bankroll) return
    setHandBetChips(prev => {
      const next = [...prev]
      next[selectedBetHand] = [...next[selectedBetHand], chipValue]
      return next
    })
    setChipUsage(prev => ({ ...prev, [chipValue]: (prev[chipValue] ?? 0) + 1 }))
  }

  function clearBet() {
    setHandBetChips(prev => {
      const next = [...prev]
      next[selectedBetHand] = []
      return next
    })
  }

  function clearAllBets() {
    setHandBetChips(prev => prev.map(() => []))
  }

  function repeatBet() {
    const lastChips = lastHandBetChips[selectedBetHand]
    if (!lastChips?.length) return
    const total = lastChips.reduce((s, v) => s + v, 0)
    if (total > bankroll) return
    setHandBetChips(prev => {
      const next = [...prev]
      next[selectedBetHand] = [...lastChips]
      return next
    })
  }

  // ─ Gestion dynamique des spots ────────────────────────────
  function addSpot(side) {
    if (numSpots >= 6) return
    const newId = nextSpotId
    setNextSpotId(n => n + 1)
    if (side === 'left') {
      setSpotIds(prev => [newId, ...prev])
      setHandBetChips(prev => [[], ...prev])
      setSelectedBetHand(0)
    } else {
      setSpotIds(prev => [...prev, newId])
      setHandBetChips(prev => [...prev, []])
      setSelectedBetHand(numSpots) // numSpots = ancienne longueur = nouvel index
    }
  }

  function removeSpot(si) {
    if (numSpots <= 1 || handBetAmounts[si] > 0) return
    const spotId = spotIds[si]
    setRemovingSpotId(spotId)
    setTimeout(() => {
      setSpotIds(prev => prev.filter(id => id !== spotId))
      setHandBetChips(prev => prev.filter((_, i) => i !== si))
      setSelectedBetHand(prev => {
        if (prev === si)  return Math.max(0, si - 1)
        if (prev > si)    return prev - 1
        return prev
      })
      setRemovingSpotId(null)
    }, 200)
  }

  // ─ Start hand ────────────────────────────────────────────
  function startHand(overrideChips = null) {
    let handBetsFinal, actualNumHands

    if (Array.isArray(overrideChips)) {
      const slots = overrideChips
        .map((c, idx) => ({ idx, bet: c.reduce((s, v) => s + v, 0) }))
        .filter(x => x.bet > 0)
      if (!slots.length) return
      handBetsFinal  = slots.map(x => x.bet)
      actualNumHands = slots.length
      if (bankroll < handBetsFinal.reduce((s, v) => s + v, 0)) return
    } else {
      if (!canDeal) return                        // garde normale
      handBetsFinal  = activeSlots.map(x => x.bet)
      actualNumHands = handBetsFinal.length
    }

    const total = handBetsFinal.reduce((s, v) => s + v, 0)

    // Calcul des délais séquentiels (ordre classique : P0, P1, P2, D_up, P0, P1, P2, D_hole)
    {
      const n = actualNumHands, step = 0.15
      const dd = {}
      for (let h = 0; h < n; h++) {
        dd[`p${h}`] = { 0: h * step, 1: (n + 1 + h) * step }
      }
      dd['d'] = { 0: (2 * n + 1) * step, 1: n * step }
      dealDelays.current = dd
    }

    // Save chips for repeat, reset bet state (préserve la longueur)
    const chipsToSave = Array.isArray(overrideChips) ? overrideChips : handBetChips
    setLastHandBetChips(chipsToSave.map(c => [...c]))
    setHandBetChips(prev => prev.map(() => []))

    let s = shoe, i = shoeIdx, r = rc
    if (i >= Math.floor(s.length * gameConfig.penetration)) {
      s = shuffle(buildDeck(gameConfig.numDecks)); i = 0; r = 0
      setShowShuffle(true)
      setDiscardCount(0)
    }
    setDealRoundKey(k => k + 1)

    const handCards = Array.from({ length: actualNumHands }, () => [])
    for (let h = 0; h < actualNumHands; h++) handCards[h].push(s[i++])
    const hole = s[i++]
    for (let h = 0; h < actualNumHands; h++) handCards[h].push(s[i++])
    const up = s[i++]
    const dHand = [hole, up]

    for (let h = 0; h < actualNumHands; h++)
      r += hiLo(handCards[h][0]) + hiLo(handCards[h][1])
    r += hiLo(up)

    setBankroll(prev => prev - total)
    setShoe(s); setShoeIdx(i); setRc(r)
    setPlayerHands(handCards); setDealerCards(dHand)
    setActiveIdx(0); setBets(handBetsFinal)
    setSurrendered([]); setIsSplitGame(false)
    setResultMsg(''); setDelta(0); setHandResults([])
    setPendingResult(null)

    const pBJs = handCards.map(h => isBlackjack(h))
    const dBJ  = isBlackjack(dHand)

    if (up.rank === 'ace') {
      setPreHandResults(Array(actualNumHands).fill(null))
      setInsHandIdx(0)
      setInsDecisions([])
      setPhase('insurance')

    } else if (dBJ) {
      setRc(r + hiLo(hole))
      const preRes = Array(actualNumHands).fill(null)
      let bankrollReturn = 0, displayDelta = 0
      const msgs = [], results = []
      handCards.forEach((_h, hi) => {
        const b = handBetsFinal[hi]
        if (pBJs[hi]) {
          bankrollReturn += b; results.push('push'); preRes[hi] = 'push'
          msgs.push(actualNumHands > 1 ? `H${hi+1}: Push BJ` : 'Push - Both Blackjack!')
        } else {
          displayDelta -= b; results.push('lose'); preRes[hi] = 'lose'
          msgs.push(actualNumHands > 1 ? `H${hi+1}: Dealer BJ` : 'Dealer Blackjack')
        }
      })
      setPreHandResults(preRes)
      setPendingResult({ bankrollReturn, displayDelta, msg: msgs.join('  ·  '), results })
      setRevealCount(2)
      setPhase('revealing')

    } else if (pBJs.every(Boolean)) {
      const preRes = Array(actualNumHands).fill('bj')
      let bankrollReturn = 0, displayDelta = 0
      const msgs = []
      handCards.forEach((_h, hi) => {
        const b = handBetsFinal[hi]
        const gain = Math.floor(b * gameConfig.bjPayout)
        bankrollReturn += b + gain; displayDelta += gain
        msgs.push(actualNumHands > 1 ? `H${hi+1}: BJ +${gain}€` : `Blackjack! +${gain}€`)
      })
      setPreHandResults(preRes)
      setPendingResult({ bankrollReturn, displayDelta, msg: msgs.join('  ·  '), results: preRes })
      setRevealCount(2)
      setPhase('revealing')

    } else if (pBJs.some(Boolean)) {
      const preRes = pBJs.map(bj => bj ? 'bj' : null)
      let bjReturn = 0
      pBJs.forEach((bj, hi) => {
        if (bj) bjReturn += handBetsFinal[hi] + Math.floor(handBetsFinal[hi] * gameConfig.bjPayout)
      })
      setBankroll(prev => prev + bjReturn)
      setPreHandResults(preRes)
      setHandResults(preRes)
      const firstPlayable = pBJs.findIndex(bj => !bj)
      setActiveIdx(firstPlayable)
      setPhase('playing')

    } else {
      setPreHandResults(Array(actualNumHands).fill(null))
      setPhase('playing')
    }
  }

  // ─ Insurance resolution (par main) ───────────────────────
  function resolveAfterInsurance(decisions) {
    // decisions[hi] = { taken: bool, insBet: number } - insBet déjà déduit du bankroll
    const dBJ  = isBlackjack(dealerCards)
    const pBJs = playerHands.map(h => isBlackjack(h))

    // Delta net assurance (gain si dBJ, perte sinon)
    const insNetDelta = decisions.reduce((s, d) => {
      if (!d.taken) return s
      return s + (dBJ ? d.insBet : -d.insBet)
    }, 0)
    // Ce qui revient au bankroll côté assurance si dBJ (2:1)
    const insReturn = decisions.reduce((s, d) => s + (d.taken && dBJ ? d.insBet * 2 : 0), 0)

    // Messages assurance
    const insMsgParts = decisions
      .map((d, hi) => {
        if (!d.taken) return null
        const tag = decisions.length > 1 ? `H${hi+1}: ` : ''
        return dBJ
          ? `${tag}Insurance +${d.insBet}€`
          : `${tag}Insurance -${d.insBet}€`
      })
      .filter(Boolean)

    if (dBJ) {
      setRc(prev => prev + hiLo(dealerCards[0]))
      let bankrollReturn = insReturn
      let displayDelta   = insNetDelta
      const msgs = [...insMsgParts], results = []
      playerHands.forEach((_h, hi) => {
        const b = bets[hi]
        if (pBJs[hi]) {
          bankrollReturn += b; results.push('push')
          msgs.push(playerHands.length > 1 ? `H${hi+1}: Push BJ` : 'Push - Both BJ')
        } else {
          displayDelta -= b; results.push('lose')
          msgs.push(playerHands.length > 1 ? `H${hi+1}: Dealer BJ` : 'Dealer Blackjack')
        }
      })
      const preRes = playerHands.map((_, hi) => pBJs[hi] ? 'push' : 'lose')
      setPreHandResults(preRes)
      setPendingResult({ bankrollReturn, displayDelta, msg: msgs.join('  ·  '), results })
      setRevealCount(2)
      setPhase('revealing')

    } else {
      if (pBJs.every(Boolean)) {
        const preRes = Array(playerHands.length).fill('bj')
        let bankrollReturn = 0, displayDelta = insNetDelta
        const msgs = [...insMsgParts]
        playerHands.forEach((_h, hi) => {
          const gain = Math.floor(bets[hi] * 1.5)
          bankrollReturn += bets[hi] + gain; displayDelta += gain
          msgs.push(playerHands.length > 1 ? `H${hi+1}: BJ +${gain}€` : `Blackjack! +${gain}€`)
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

  function doInsuranceDecide(taken) {
    const hi     = insHandIdx
    const insBet = taken ? bets[hi] / 2 : 0
    if (taken) setBankroll(prev => prev - insBet)
    const newDecisions = [...insDecisions, { taken, insBet }]
    const nextIdx = hi + 1
    if (nextIdx < bets.length) {
      setInsHandIdx(nextIdx)
      setInsDecisions(newDecisions)
    } else {
      resolveAfterInsurance(newDecisions)
    }
  }

  // ─ Player actions ─────────────────────────────────────────
  function doHit() {
    trackDecision('H')
    const d = draw(shoe, shoeIdx, rc)
    const newRc    = d.rcBefore + hiLo(d.card)
    const newHand  = [...activeHand, d.card]
    const newHands = playerHands.map((h, i) => i === activeIdx ? newHand : h)
    setShoe(d.shoe); setShoeIdx(d.idx); setRc(newRc); setPlayerHands(newHands)
    if (isBust(newHand) || handValue(newHand) === 21)
      advance(newHands, activeIdx, dealerCards, newRc, d.shoe, d.idx, bets, isSplitGame, surrendered, preHandResults)
  }

  function doStand() {
    trackDecision('S')
    advance(playerHands, activeIdx, dealerCards, rc, shoe, shoeIdx, bets, isSplitGame, surrendered, preHandResults)
  }

  function doDouble() {
    if (!canDouble(activeHand) || bankroll < bets[activeIdx]) return
    trackDecision('D')
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
    if (!canSplit(activeHand) || playerHands.length >= gameConfig.maxSplitHands || bankroll < bets[activeIdx]) return
    trackDecision('Y')
    const d1 = draw(shoe, shoeIdx, rc)
    const rc1 = d1.rcBefore + hiLo(d1.card)
    const d2  = draw(d1.shoe, d1.idx, rc1)
    const rc2 = d2.rcBefore + hiLo(d2.card)
    const h1 = [activeHand[0], d1.card], h2 = [activeHand[1], d2.card]
    const newHands  = [...playerHands.slice(0, activeIdx), h1, h2, ...playerHands.slice(activeIdx + 1)]
    const newBets   = [...bets.slice(0, activeIdx), bets[activeIdx], bets[activeIdx], ...bets.slice(activeIdx + 1)]
    const newPreRes = [...preHandResults.slice(0, activeIdx), null, null, ...preHandResults.slice(activeIdx + 1)]
    setBankroll(prev => prev - bets[activeIdx])
    setShoe(d2.shoe); setShoeIdx(d2.idx); setRc(rc2)
    setPlayerHands(newHands); setBets(newBets); setIsSplitGame(true)
    setPreHandResults(newPreRes)
  }

  function doSurrender() {
    trackDecision('SUR')
    const half = bets[activeIdx] / 2
    setBankroll(prev => prev + half)
    const newSurr = [...surrendered, activeIdx]
    setSurrendered(newSurr)
    advance(playerHands, activeIdx, dealerCards, rc, shoe, shoeIdx, bets, isSplitGame, newSurr, preHandResults)
  }

  // ─ Post-round quick actions ───────────────────────────────
  const lastTotal = lastHandBetChips.reduce((s, c) => s + c.reduce((ss, v) => ss + v, 0), 0)
  const canRepeat = lastTotal > 0 && bankroll >= lastTotal
  const canDouble2x = lastTotal > 0 && bankroll >= lastTotal * 2
  const canHalf   = lastTotal >= 2

  function doRepeatBets() {
    setDiscardCount(shoeIdx)
    setSelectedBetHand(0)
    startHand(lastHandBetChips)
  }
  function doDoubleBets() {
    if (!canDouble2x) return
    const doubled = lastHandBetChips.map(c => {
      const tot = c.reduce((s, v) => s + v, 0)
      return tot > 0 ? buildChipsFromAmount(Math.min(tot * 2, MAX_BET)) : []
    })
    setDiscardCount(shoeIdx)
    setSelectedBetHand(0)
    startHand(doubled)
  }
  function doHalfBets() {
    if (!canHalf) return
    const halved = lastHandBetChips.map(c => {
      const tot = c.reduce((s, v) => s + v, 0)
      return tot >= 2 ? buildChipsFromAmount(Math.floor(tot / 2)) : []
    })
    setDiscardCount(shoeIdx)
    setSelectedBetHand(0)
    startHand(halved)
  }
  function doNewBets() {
    setDiscardCount(shoeIdx)
    setPhase('betting')
    setHandResults([])
    setPendingResult(null)
    setHandBetChips([[]])
    setSpotIds([0])
    setNextSpotId(1)
    setPlayerHands([])
    setDealerCards([])
    setSelectedBetHand(0)
    setResultMsg('')
    setDelta(0)
  }

  // ─ Apply game config ──────────────────────────────────────
  function applyAndReset(cfg) {
    setGameConfig(cfg)
    setShoe(shuffle(buildDeck(cfg.numDecks)))
    setShoeIdx(0); setRc(0); setDiscardCount(0)
    setPhase('betting')
    setHandBetChips([[]]); setSpotIds([0]); setNextSpotId(1)
    setSelectedBetHand(0); setLastHandBetChips([[]])
    setPlayerHands([]); setDealerCards([])
    setHandResults([]); setPendingResult(null)
    setResultMsg(''); setDelta(0)
    setBankroll(INIT_BANK)
    setSessionHands(0); setSessionWins(0); setSessionDelta(0)
    setSessionMistakes(0); setSessionDecisions(0)
    setShowSettings(false)
  }

  // ─ Bankroll edit handlers ─────────────────────────────────
  function startEditBankroll() {
    if (phase !== 'betting') return
    setEditingBankroll(true)
    setBankrollInput(String(Math.round(bankroll)))
  }
  function commitBankrollEdit(inputRef) {
    const v = parseFloat(bankrollInput)
    if (!isNaN(v) && v >= 10 && v <= 1_000_000) {
      setBankroll(v)
      setEditingBankroll(false)
    } else {
      if (inputRef?.current) {
        inputRef.current.classList.add('bankroll-shake')
        setTimeout(() => { inputRef?.current?.classList.remove('bankroll-shake') }, 400)
      }
      setEditingBankroll(false)
    }
  }

  // ─ Availability ───────────────────────────────────────────
  // (playing et canSur déjà déclarés plus haut, avant hint useMemo)

  // Double selon la restriction de règles
  function canDoubleHand(cards) {
    if (!canDouble(cards)) return false
    const v = handValue(cards)
    if (gameConfig.doubleRestriction === '10-11') return v === 10 || v === 11
    if (gameConfig.doubleRestriction === '9-11')  return v >= 9 && v <= 11
    return true
  }

  const canDbl  = playing && canDoubleHand(activeHand)
    && (!isSplitGame || gameConfig.doubleAfterSplit)
    && bankroll >= bets[activeIdx]
  const canSpl  = playing && canSplit(activeHand)
    && playerHands.length < gameConfig.maxSplitHands
    && bankroll >= bets[activeIdx]
  const dealerRevealCount = phase === 'result' ? Infinity : (phase === 'playing' || phase === 'insurance') ? 2 : revealCount

  // ─ Per-hand result deltas (computed at render time) ───────
  const handDeltas = handResults.map((r, i) => {
    const b = bets[i] ?? 0
    if (r === 'bj')   return Math.floor(b * gameConfig.bjPayout)
    if (r === 'win')  return b
    if (r === 'push') return 0
    if (r === 'lose') return surrendered.includes(i) ? -(b / 2) : -b
    return null
  })

  // ─ Render helpers ─────────────────────────────────────────
  const sidebarStyle = {
    width: '140px', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '10px',
  }
  const sidebarPanelStyle = {
    background: 'rgba(0,0,0,0.45)', border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: '12px', padding: '10px 12px',
  }

  // ─ Render ─────────────────────────────────────────────────
  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&display=swap');
        * { box-sizing: border-box; }
        body { background: #0a1a0a; font-family: 'Rajdhani', sans-serif; margin: 0; }

        @keyframes dealCard {
          from { opacity:0; transform: translate(160px,-50px) rotate(18deg) scale(0.85); }
          to   { opacity:1; transform: translate(0,0) rotate(0deg) scale(1); }
        }
        @keyframes breathe {
          0%,100% { transform: scale(1) translateY(0); }
          50%     { transform: scale(1.025) translateY(-2px); }
        }
        @keyframes flipCard {
          0%   { transform:perspective(500px) rotateY(90deg) scale(0.92); opacity:0.5; }
          100% { transform:perspective(500px) rotateY(0deg) scale(1); opacity:1; }
        }
        @keyframes bjPulse {
          0%,100% { box-shadow:0 0 0 0 rgba(240,192,64,0); }
          33%      { box-shadow:0 0 24px 8px rgba(240,192,64,0.55); }
          66%      { box-shadow:0 0 24px 8px rgba(240,192,64,0.55); }
        }
        @keyframes shuffleIn {
          0%   { opacity:0; transform:translateY(-10px) scale(0.96); }
          15%  { opacity:1; transform:translateY(0) scale(1); }
          80%  { opacity:1; }
          100% { opacity:0; }
        }
        @keyframes fadeSlideUp {
          0%   { opacity:1; transform:translateY(0); }
          70%  { opacity:1; }
          100% { opacity:0; transform:translateY(-12px); }
        }
        @keyframes spotPulse {
          0%,100% { box-shadow:0 0 0 0 rgba(240,192,64,0.3); }
          50%      { box-shadow:0 0 12px 4px rgba(240,192,64,0.5); }
        }
        @keyframes menuIn {
          from { opacity:0; transform: translateY(8px) scale(0.96); }
          to   { opacity:1; transform: translateY(0) scale(1); }
        }
        @keyframes netIn {
          0%   { opacity:0; transform: scale(0.75); }
          70%  { transform: scale(1.04); }
          100% { opacity:1; transform: scale(1); }
        }
        @keyframes badgePop {
          0%   { opacity:0; transform: scale(0.7); }
          100% { opacity:1; transform: scale(1); }
        }
        @keyframes shake {
          0%,100% { transform:translateX(0); }
          20%,60% { transform:translateX(-6px); }
          40%,80% { transform:translateX(6px); }
        }
        .bankroll-shake { animation: shake 0.35s ease; }
        @keyframes spotIn {
          0%   { transform: scale(0); opacity: 0; }
          100% { transform: scale(1); opacity: 1; }
        }
        @keyframes spotOut {
          0%   { transform: scale(1); opacity: 1; }
          100% { transform: scale(0); opacity: 0; }
        }
        @keyframes fadeInFast {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes plusFadeOut {
          from { opacity: 1; transform: scale(1); }
          to   { opacity: 0; transform: scale(0.8); }
        }
        .card-deal   { animation: dealCard 0.3s 0s cubic-bezier(0.25,0.46,0.45,0.94) both; }
        .card-flip   { animation: flipCard  0.4s cubic-bezier(0.25,0.8,0.25,1) both; }
        .card-breathe { animation: breathe 2s 0.5s ease-in-out infinite; }
        .bj-glow     { animation: bjPulse   0.9s ease-in-out 3; }
        .shuffle-banner { animation: shuffleIn 2s ease-in-out forwards; }
        .round-delta { animation: fadeSlideUp 3s ease-out forwards; }
        .bet-spot-active { animation: spotPulse 1.4s ease-in-out infinite; }
      `}</style>

      {/* Vignette overlay */}
      <div style={{ position:'fixed', inset:0, pointerEvents:'none', zIndex:0,
        background:'radial-gradient(ellipse at 50% 40%, transparent 35%, rgba(0,0,0,0.65) 100%)' }} />

      <div style={{ minHeight:'100vh', background:'#0a1a0a', display:'flex', flexDirection:'column',
        userSelect:'none', fontFamily:"'Rajdhani',sans-serif", color:'#f0ece0', position:'relative', zIndex:1 }}>

        {/* ── 3-column layout ── */}
        <div style={{ flex:1, display:'flex', gap:'10px', padding:'10px', minHeight:0 }}>

          {/* ══ LEFT SIDEBAR ══ */}
          <div style={sidebarStyle}>

            {/* Hi-Lo HUD */}
            <CoveredPanel hidden={!showHiLo} onToggle={() => setShowHiLo(v => !v)} label="Hi-Lo" icon="🎴">
              <Counter rc={rc} tc={tc} />
              {/* Config résumé discret sous le counter */}
              <div style={{ textAlign:'center', fontSize:'10px', color:'#4a7a5a', marginTop:'4px', letterSpacing:'0.5px' }}>
                {gameConfig.numDecks}D · {gameConfig.dealerHitsSoft17 ? 'H17' : 'S17'} · {gameConfig.bjPayout === 1.5 ? '3:2' : '6:5'} · {gameConfig.lateSurrender ? 'LS' : 'No LS'}
              </div>
            </CoveredPanel>

            {/* Best Play panel */}
            <CoveredPanel hidden={!showHint} onToggle={() => setShowHint(v => !v)} label="Hint" icon="💡">
              <div style={{ background:'rgba(0,0,0,0.3)', border:'1px solid rgba(255,255,255,0.07)', borderRadius:'12px', padding:'10px 12px', height:'78px', boxSizing:'border-box', display:'flex', flexDirection:'column', justifyContent:'space-between' }}>
                <div style={{ color:'rgba(255,255,255,0.35)', fontSize:'9px', fontWeight:700, letterSpacing:'2px', textTransform:'uppercase' }}>Best Play</div>
                <div style={{ flex:1, display:'flex', flexDirection:'column', justifyContent:'center' }}>
                {phase === 'insurance' && insuranceHint
                  ? (
                    <div>
                      <div style={{ fontSize:'18px', fontWeight:900, color: insuranceHint === 'take' ? '#fde047' : 'rgba(255,255,255,0.7)', lineHeight:1 }}>
                        {insuranceHint === 'take' ? 'Take Ins.' : 'No Ins.'}
                      </div>
                      <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.4)', marginTop:'3px' }}>
                        {insuranceHint === 'take' ? `TC${tc >= 0 ? '+' : ''}${tc.toFixed(1)} ≥ +3` : `TC${tc >= 0 ? '+' : ''}${tc.toFixed(1)} < +3`}
                      </div>
                    </div>
                  ) : phase === 'playing' && hint
                  ? (() => {
                    const ACTION_COLORS = { H:'#f59e0b', S:'#059669', D:'#2563eb', Ds:'#2563eb', Y:'#64748b', 'Y/N':'#64748b', SUR:'#dc2626' }
                    const ACTION_LABELS = { H:'Hit', S:'Stand', D:'Double', Ds:'Double/Stand', Y:'Split', 'Y/N':'Split (DAS)', SUR:'Surrender' }
                    const col = ACTION_COLORS[hint.action] ?? '#888'
                    const lbl = ACTION_LABELS[hint.action] ?? hint.action
                    return (
                      <div>
                        <div style={{ fontSize:'20px', fontWeight:900, color: col, lineHeight:1 }}>{lbl}</div>
                        <div style={{ fontSize:'10px', marginTop:'3px', color: hint.isDeviation ? '#fb923c' : 'rgba(255,255,255,0.4)' }}>
                          {hint.isDeviation ? `★ TC dev (${hint.basic})` : 'Basic + 18 deviations'}
                        </div>
                      </div>
                    )
                  })()
                  : <div style={{ color:'rgba(255,255,255,0.15)', fontSize:'18px', fontWeight:900, lineHeight:1 }}>-</div>
                }
                </div>
              </div>
            </CoveredPanel>

            {/* Boutons Basic Strategy + I18 */}
            {(() => {
              const btnBase = hovered => ({
                width:'36px', height:'36px', borderRadius:'6px', border:'none', cursor:'pointer',
                background: hovered ? '#132b1c' : '#0d2214',
                outline: hovered ? '1px solid #c8963c' : '1px solid #2a5a3a',
                display:'flex', alignItems:'center', justifyContent:'center',
                transition:'outline 0.15s, background 0.15s',
                position:'relative', flexShrink:0,
              })
              const tipStyle = {
                position:'absolute', left:'calc(100% + 8px)', top:'50%', transform:'translateY(-50%)',
                background:'#0d2214', border:'1px solid #c8963c', borderRadius:'4px',
                color:'#fff', fontSize:'11px', padding:'4px 8px',
                whiteSpace:'nowrap', pointerEvents:'none', zIndex:10,
                animation:'fadeInFast 0.15s both',
              }
              return (
                <div style={{ display:'flex', justifyContent:'center', gap:'8px' }}>
                  {/* Basic Strategy */}
                  <button
                    style={btnBase(bsHov)}
                    onMouseEnter={() => setBsHov(true)}
                    onMouseLeave={() => setBsHov(false)}
                    onClick={() => setShowBSOverlay(true)}
                  >
                    <svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                      {[['#059669','#dc2626','#2563eb'],['#059669','#059669','#dc2626'],['#2563eb','#059669','#059669']].map((row, ri) =>
                        row.map((col, ci) => (
                          <rect key={`${ri}-${ci}`} x={2 + ci*6} y={2 + ri*6} width="5" height="5" rx="1" fill={col} opacity="0.85"/>
                        ))
                      )}
                    </svg>
                    {bsHov && <div style={tipStyle}>Basic Strategy chart</div>}
                  </button>
                  {/* Illustrious 18 */}
                  <button
                    style={btnBase(i18Hov)}
                    onMouseEnter={() => setI18Hov(true)}
                    onMouseLeave={() => setI18Hov(false)}
                    onClick={() => setShowI18Overlay(true)}
                  >
                    <svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                      <polygon points="10,2 18,18 2,18" fill="none" stroke="#f0c040" strokeWidth="1.8" strokeLinejoin="round"/>
                      <text x="10" y="15" textAnchor="middle" fontFamily="'Rajdhani',sans-serif"
                        fontWeight="700" fontSize="7" fill="#f0c040">I18</text>
                    </svg>
                    {i18Hov && <div style={tipStyle}>Illustrious 18 deviations</div>}
                  </button>
                </div>
              )
            })()}

            {/* Decks remaining */}
            <div style={{ ...sidebarPanelStyle }}>
              <div style={{ color:'rgba(255,255,255,0.35)', fontSize:'9px', fontWeight:700,
                letterSpacing:'2px', textTransform:'uppercase', marginBottom:'4px' }}>Shoe</div>
              <div style={{ color:'#f0ece0', fontWeight:700, fontSize:'16px' }}>
                {decksLeft.toFixed(1)} <span style={{ color:'rgba(255,255,255,0.35)', fontWeight:400, fontSize:'11px' }}>decks</span>
              </div>
              <div style={{ color:'rgba(255,255,255,0.3)', fontSize:'10px', marginTop:'2px' }}>
                {shoe.length - shoeIdx} cards left
              </div>
              {shoeIdx >= Math.floor(shoe.length * PENETRATION * 0.85) && (
                <div style={{ color:'#fbbf24', fontSize:'9px', marginTop:'4px', letterSpacing:'1px' }}>
                  ⚠ Shuffle soon
                </div>
              )}
            </div>

            {/* Session stats */}
            <div style={{ ...sidebarPanelStyle, flex:1 }}>
              <div style={{ color:'rgba(255,255,255,0.35)', fontSize:'9px', fontWeight:700,
                letterSpacing:'2px', textTransform:'uppercase', marginBottom:'8px' }}>Session</div>
              <div style={{ display:'flex', flexDirection:'column', gap:'6px' }}>
                <div>
                  <div style={{ color:'rgba(255,255,255,0.35)', fontSize:'9px' }}>Hands</div>
                  <div style={{ color:'#f0ece0', fontWeight:700, fontSize:'18px', lineHeight:1 }}>{sessionHands}</div>
                </div>
                <div>
                  <div style={{ color:'rgba(255,255,255,0.35)', fontSize:'9px' }}>Win Rate</div>
                  <div style={{ color:'#f0ece0', fontWeight:700, fontSize:'18px', lineHeight:1 }}>
                    {sessionHands > 0 ? Math.round(sessionWins / sessionHands * 100) : 0}
                    <span style={{ color:'rgba(255,255,255,0.35)', fontWeight:400, fontSize:'11px' }}>%</span>
                  </div>
                </div>
                <div>
                  <div style={{ color:'rgba(255,255,255,0.35)', fontSize:'9px' }}>Mistakes</div>
                  <div style={{ fontWeight:700, fontSize:'18px', lineHeight:1,
                    color: sessionDecisions > 0
                      ? (sessionMistakes/sessionDecisions < 0.05 ? '#4ade80'
                        : sessionMistakes/sessionDecisions < 0.15 ? '#fbbf24' : '#f87171')
                      : '#f0ece0' }}>
                    {sessionDecisions > 0 ? (sessionMistakes/sessionDecisions*100).toFixed(1) : '0.0'}
                    <span style={{ color:'rgba(255,255,255,0.35)', fontWeight:400, fontSize:'11px' }}>%</span>
                  </div>
                </div>
                <div>
                  <div style={{ color:'rgba(255,255,255,0.35)', fontSize:'9px' }}>Net P&L</div>
                  <div style={{ fontWeight:700, fontSize:'18px', lineHeight:1,
                    color: sessionDelta > 0 ? '#4ade80' : sessionDelta < 0 ? '#f87171' : '#f0ece0' }}>
                    {sessionDelta > 0 ? '+' : ''}{sessionDelta}€
                  </div>
                </div>
              </div>
            </div>

            {/* Bouton Simulator */}
            <a href={SIMULATOR_URL} target="_blank" rel="noreferrer"
              style={{
                display:'block', width:'100%', padding:'9px 0', textAlign:'center',
                background:'rgba(200,150,60,0.08)', border:'1px solid rgba(200,150,60,0.3)',
                borderRadius:'8px', cursor:'pointer', textDecoration:'none',
                transition:'background 150ms, border-color 150ms',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(200,150,60,0.18)'
                e.currentTarget.style.borderColor = 'rgba(200,150,60,0.8)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(200,150,60,0.08)'
                e.currentTarget.style.borderColor = 'rgba(200,150,60,0.3)'
              }}
            >
              <div style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:'6px' }}>
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                  <rect x="1" y="10" width="3" height="5" rx="1" fill="#c8963c"/>
                  <rect x="6" y="6"  width="3" height="9" rx="1" fill="#c8963c" opacity="0.8"/>
                  <rect x="11" y="2" width="3" height="13" rx="1" fill="#c8963c" opacity="0.6"/>
                </svg>
                <span style={{ color:'#c8963c', fontSize:'10px', fontWeight:700, letterSpacing:'2px', textTransform:'uppercase' }}>Simulator</span>
              </div>
            </a>

          </div>

          {/* ══ CASINO TABLE ══ */}
          {/* Bordure bois extérieure */}
          <div style={{
            flex: 1, position:'relative', borderRadius:'28px',
            background: 'linear-gradient(145deg, #6b3f1a 0%, #7d4c22 20%, #5c3516 45%, #7a4828 70%, #4d2e12 100%)',
            boxShadow: '0 30px 90px rgba(0,0,0,0.92), 0 0 0 1px rgba(0,0,0,0.6), inset 0 2px 3px rgba(255,255,255,0.13), inset 0 -2px 5px rgba(0,0,0,0.55)',
            padding: '16px',
            minHeight: '512px',
            display: 'flex', flexDirection: 'column',
          }}>
            {/* Grain bois */}
            <div style={{ position:'absolute', inset:0, borderRadius:'inherit', pointerEvents:'none', zIndex:0,
              backgroundImage: 'repeating-linear-gradient(105deg, transparent, transparent 4px, rgba(0,0,0,0.025) 4px, rgba(0,0,0,0.025) 8px)',
            }} />
            {/* Filet doré intérieur */}
            <div style={{ position:'absolute', inset:'14px', borderRadius:'16px', pointerEvents:'none', zIndex:1,
              border: '1.5px solid #c8963c',
              boxShadow: 'inset 0 0 14px rgba(200,150,60,0.1)',
            }} />

            {/* Tapis vert intérieur */}
            <div style={{
              position:'relative', zIndex:2, borderRadius:'12px', overflow:'hidden', flex:1,
              background:'radial-gradient(ellipse at 50% 30%, #225c30 0%, #1a5c2a 40%, #123d1c 100%)',
              display:'flex', flexDirection:'column',
            }}>
              {/* Texture feutre SVG */}
              <svg style={{ position:'absolute', inset:0, width:'100%', height:'100%', pointerEvents:'none', zIndex:0 }} xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <pattern id="felt-texture" x="0" y="0" width="4" height="4" patternUnits="userSpaceOnUse">
                    <line x1="0" y1="4" x2="4" y2="0" stroke="rgba(255,255,255,0.04)" strokeWidth="0.5"/>
                    <line x1="-1" y1="1" x2="1" y2="-1" stroke="rgba(255,255,255,0.04)" strokeWidth="0.5"/>
                    <line x1="3" y1="5" x2="5" y2="3" stroke="rgba(255,255,255,0.04)" strokeWidth="0.5"/>
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#felt-texture)"/>
              </svg>
              {/* Spotlight */}
              <div style={{ position:'absolute', inset:0, pointerEvents:'none', zIndex:1,
                background:'radial-gradient(ellipse 75% 55% at 50% 15%, rgba(255,255,255,0.05) 0%, transparent 70%)' }} />

            {/* Shuffle banner */}
            {showShuffle && (
              <div className="shuffle-banner" style={{
                position:'absolute', inset:0, zIndex:50, display:'flex', flexDirection:'column',
                alignItems:'center', justifyContent:'center', background:'rgba(0,0,0,0.65)',
                borderRadius:'inherit', gap:'8px', pointerEvents:'none' }}>
                <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                  <path d="M6 14h20l-6-6M34 26H14l6 6M6 26l10-12M34 14L24 26"
                    stroke="#f0c040" strokeWidth="2.5" strokeLinecap="round"/>
                </svg>
                <div style={{ color:'#f0ece0', fontWeight:700, fontSize:'16px', letterSpacing:'2px' }}>
                  NEW SHOE
                </div>
              </div>
            )}


            {/* Table inner */}
            <div style={{ position:'relative', zIndex:2, flex:1, display:'flex', flexDirection:'column', padding:'12px' }}>

              {/* Dealer zone */}
              <div style={{ paddingTop:'16px', paddingBottom:'16px', display:'flex', flexDirection:'row',
                alignItems:'center', justifyContent:'center', gap:'20px', minHeight:'195px' }}>
                {/* Discard pile - left */}
                <DiscardPile count={discardCount} />
                {/* Dealer hand - centre */}
                <div style={{ flex:1, display:'flex', justifyContent:'center', alignItems:'center', minWidth:0 }}>
                  {dealerCards.length > 0
                    ? <HandDisplay key={`dealer-${dealRoundKey}`}
                        cards={dealerCards} label="Dealer"
                        hideFirst={phase === 'playing' || phase === 'insurance'}
                        revealCount={dealerRevealCount} isRevealing={phase === 'revealing'}
                        breatheHidden={phase === 'playing' || phase === 'insurance'}
                        cardDelays={dealDelays.current['d']} />
                    : <span style={{ color:'rgba(255,255,255,0.12)', fontSize:'13px' }}>Dealer</span>
                  }
                </div>
                {/* Shoe - right */}
                <ShoeVisual cardsLeft={shoe.length - shoeIdx} totalCards={shoe.length} />
              </div>
              {/* Séparateur dealer/joueur - courbe SVG dorée */}
              <svg width="100%" height="36" viewBox="0 0 400 36" preserveAspectRatio="none"
                style={{ display:'block', overflow:'visible', margin:'2px 0', flexShrink:0 }}>
                <defs>
                  <filter id="glow-sep" x="-20%" y="-100%" width="140%" height="300%">
                    <feGaussianBlur stdDeviation="1.5" result="blur"/>
                    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                  </filter>
                </defs>
                {/* Courbe principale */}
                <path d="M 8 30 Q 200 6 392 30"
                  fill="none" stroke="#c8963c" strokeWidth="1.2" opacity="0.5" filter="url(#glow-sep)"/>
                {/* Ornements aux extrémités */}
                <circle cx="8"   cy="30" r="3.5" fill="none" stroke="#c8963c" strokeWidth="0.8" opacity="0.38"/>
                <circle cx="8"   cy="30" r="1.5" fill="#c8963c" opacity="0.32"/>
                <circle cx="392" cy="30" r="3.5" fill="none" stroke="#c8963c" strokeWidth="0.8" opacity="0.38"/>
                <circle cx="392" cy="30" r="1.5" fill="#c8963c" opacity="0.32"/>
                {/* Ornement centre */}
                <circle cx="200" cy="6"  r="3.5" fill="none" stroke="#c8963c" strokeWidth="0.8" opacity="0.38"/>
                <circle cx="200" cy="6"  r="1.5" fill="#c8963c" opacity="0.32"/>
              </svg>

              {/* Ornement casino central */}
              <div style={{ display:'flex', justifyContent:'center', alignItems:'center', margin:'-2px 0 0' }}>
                <svg width="180" height="34" viewBox="0 0 180 34" style={{ overflow:'visible' }}>
                  <path d="M 90 4 L 104 17 L 90 30 L 76 17 Z"
                    fill="none" stroke="#c8963c" strokeWidth="0.7" opacity="0.2"/>
                  <circle cx="90" cy="17" r="6" fill="none" stroke="#c8963c" strokeWidth="0.7" opacity="0.2"/>
                  <text x="16"  y="23" fontSize="15" fill="#c8963c" opacity="0.17" textAnchor="middle" fontFamily="serif">♠</text>
                  <text x="48"  y="23" fontSize="15" fill="#c8963c" opacity="0.17" textAnchor="middle" fontFamily="serif">♥</text>
                  <text x="132" y="23" fontSize="15" fill="#c8963c" opacity="0.17" textAnchor="middle" fontFamily="serif">♦</text>
                  <text x="164" y="23" fontSize="15" fill="#c8963c" opacity="0.17" textAnchor="middle" fontFamily="serif">♣</text>
                </svg>
              </div>

              {/* Inscription BLACKJACK PAYS 3 TO 2 - sous le séparateur, jamais masquée */}
              <div style={{ textAlign:'center', pointerEvents:'none', margin:'2px 0 4px' }}>
                <span style={{ color:'#c8963c', opacity:0.25, fontFamily:"Georgia,'Times New Roman',serif",
                  fontSize:'11px', letterSpacing:'6px', textTransform:'uppercase' }}>
                  Blackjack Pays 3 to 2
                </span>
              </div>

              {/* Player zone + result overlay (same block, result est absolue) */}
              <div style={{ flex:1, paddingTop:'16px', paddingBottom:'8px', display:'flex', flexDirection:'column',
                alignItems:'center', minHeight:'160px', justifyContent:'center', position:'relative' }}>

                {/* Result banner - superposé, ne déplace pas les mains */}
                {phase === 'result' && (
                  <div style={{ position:'absolute', top:'-4px', left:0, right:0, zIndex:6,
                    display:'flex', flexDirection:'column', alignItems:'center', gap:'2px',
                    pointerEvents:'none' }}>
                    <div style={{ fontSize:'11px', color:'rgba(255,255,255,0.35)', letterSpacing:'2px',
                      textTransform:'uppercase' }}>
                      {resultMsg}
                    </div>
                    {delta !== 0 && (
                      <div style={{ fontWeight:900, fontSize:'28px', lineHeight:1, letterSpacing:'-0.5px',
                        color: delta > 0 ? '#34d399' : '#f87171',
                        animation:'netIn 0.35s cubic-bezier(0.34,1.56,0.64,1) both' }}>
                        {delta > 0 ? `+${delta}€` : `${delta}€`}
                      </div>
                    )}
                  </div>
                )}
                {phase !== 'betting' && playerHands.length > 0
                  ? <div style={{ display:'flex', gap:'12px', flexWrap:'wrap', justifyContent:'center' }}>
                      {[...playerHands].map((_, di) => {
                        const i = playerHands.length - 1 - di
                        return (
                          <HandDisplay key={`${i}-${dealRoundKey}`} cards={playerHands[i]}
                            label={playerHands.length > 1 ? `Hand ${i+1}` : 'You'}
                            active={playing && i === activeIdx}
                            result={handResults[i] ?? null}
                            bet={bets[i] ?? 0}
                            cardDelays={dealDelays.current[`p${i}`]}
                            badge={(() => {
                              if (phase !== 'result') return null
                              const r = handResults[i], d = handDeltas[i]
                              if (d == null) return null
                              if (r === 'bj')   return { type:'bj',   label:`BJ +${d}€` }
                              if (r === 'win')  return { type:'win',  label:`WIN +${d}€` }
                              if (r === 'push') return { type:'push', label:'PUSH' }
                              if (r === 'lose') return { type:'lose', label:`LOSE ${d}€` }
                              return null
                            })()} />
                        )
                      })}
                    </div>
                  : phase === 'betting'
                    ? (() => {
                      // Diamètre adaptatif selon le nombre de spots
                      const D = [76, 72, 68, 60, 54, 48][numSpots - 1]
                      // Style commun des boutons "+"
                      const plusBtnStyle = hov => ({
                        width:'38px', height:'38px', borderRadius:'50%', flexShrink:0,
                        border: hov ? '2px solid rgba(200,150,60,0.8)' : '2px dashed rgba(200,150,60,0.4)',
                        background:'transparent', cursor:'pointer', padding:0,
                        color:'rgba(200,150,60,0.5)', fontSize:'20px', lineHeight:1,
                        display:'flex', alignItems:'center', justifyContent:'center',
                        transform: hov ? 'scale(1.1)' : 'scale(1)',
                        transition:'all 0.15s',
                      })
                      return (
                        /* Spots de mise dynamiques */
                        <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:'10px', width:'100%' }}>
                          {/* Rangée: [+ gauche] [spots] [+ droit] */}
                          <div style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:'8px' }}>

                            {/* + gauche */}
                            {numSpots < 6
                              ? <button onClick={() => addSpot('left')}
                                  onMouseEnter={() => setHoveredSpot('left')}
                                  onMouseLeave={() => setHoveredSpot(null)}
                                  style={plusBtnStyle(hoveredSpot === 'left')}>+</button>
                              : <div style={{ width:'38px' }} />}

                            {/* Spots + ghosts */}
                            <div style={{ display:'flex', gap:'32px', alignItems:'center' }}>
                              {handBetChips.map((chips, si) => {
                                const spotId      = spotIds[si]
                                const betAmt      = handBetAmounts[si]
                                const isActive    = si === selectedBetHand
                                const isRemoving  = removingSpotId === spotId
                                const isHovered   = hoveredSpot === si
                                const canRemove   = isHovered && betAmt === 0 && !isActive && numSpots > 1 && !isRemoving
                                const showClearTip= isHovered && betAmt > 0 && !isActive
                                const topChips    = chips.slice(-3)
                                const chipPx      = Math.round(D * 0.52)

                                return (
                                  <div key={spotId}
                                    onMouseEnter={() => setHoveredSpot(si)}
                                    onMouseLeave={() => setHoveredSpot(null)}
                                    style={{
                                      display:'flex', flexDirection:'column', alignItems:'center', gap:'3px',
                                      position:'relative', flexShrink:0,
                                      animation: isRemoving
                                        ? 'spotOut 0.2s ease forwards'
                                        : 'spotIn 0.25s cubic-bezier(0.34,1.56,0.64,1) both',
                                    }}>

                                    {/* Label "● PLACING BETS" */}
                                    <div style={{
                                      fontSize:'9px', fontWeight:700, letterSpacing:'1px',
                                      color: isActive ? '#f0c040' : 'transparent',
                                      textTransform:'uppercase', height:'12px', lineHeight:'12px',
                                      whiteSpace:'nowrap',
                                    }}>
                                      {isActive ? '● PLACING BETS' : '\u00a0'}
                                    </div>

                                    {/* Cercle */}
                                    <div
                                      className={isActive ? 'bet-spot-active' : ''}
                                      onClick={() => !isRemoving && setSelectedBetHand(si)}
                                      style={{
                                        width:`${D}px`, height:`${D}px`, borderRadius:'50%',
                                        border: isActive
                                          ? '2px solid rgba(240,192,64,0.75)'
                                          : '2px dashed rgba(255,255,255,0.2)',
                                        background: isActive
                                          ? 'rgba(240,192,64,0.08)'
                                          : betAmt > 0 ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.12)',
                                        cursor: isRemoving ? 'default' : 'pointer',
                                        position:'relative',
                                        display:'flex', flexDirection:'column',
                                        alignItems:'center', justifyContent:'center',
                                        transition:'border 0.15s',
                                      }}>

                                      {/* × suppression */}
                                      {canRemove && (
                                        <div onClick={e => { e.stopPropagation(); removeSpot(si) }}
                                          style={{
                                            position:'absolute', top:'-7px', right:'-7px',
                                            width:'18px', height:'18px', borderRadius:'50%',
                                            background:'#dc2626', color:'#fff',
                                            display:'flex', alignItems:'center', justifyContent:'center',
                                            fontSize:'13px', fontWeight:700, lineHeight:1,
                                            cursor:'pointer', zIndex:10,
                                            animation:'fadeInFast 0.15s ease both',
                                          }}>×</div>
                                      )}

                                      {/* Tooltip "Clear bet first" */}
                                      {showClearTip && (
                                        <div style={{
                                          position:'absolute', top:'-26px', left:'50%',
                                          transform:'translateX(-50%)',
                                          background:'rgba(0,0,0,0.82)', color:'rgba(255,255,255,0.7)',
                                          fontSize:'9px', padding:'3px 7px', borderRadius:'6px',
                                          whiteSpace:'nowrap', pointerEvents:'none',
                                          animation:'fadeInFast 0.15s ease both',
                                        }}>Clear bet first</div>
                                      )}

                                      {/* Contenu */}
                                      {betAmt > 0 ? (
                                        <>
                                          {topChips.map((v, idx) => {
                                            const chip = CHIPS.find(c => c.value === v) ?? CHIPS[0]
                                            return (
                                              <div key={idx} style={{
                                                position:'absolute',
                                                top:`${Math.round(D * 0.1) + idx * 4}px`,
                                                width:`${chipPx}px`, height:`${chipPx}px`,
                                                borderRadius:'50%',
                                                background:chip.fill, border:`2px solid ${chip.stroke}`,
                                                display:'flex', alignItems:'center', justifyContent:'center',
                                                fontSize:'8px', fontWeight:700, color:chip.text,
                                                fontFamily:"'Rajdhani',sans-serif", zIndex: idx + 1,
                                              }}>{v}</div>
                                            )
                                          })}
                                          <div style={{
                                            position:'absolute',
                                            bottom:`${Math.round(D * 0.15)}px`,
                                            color:'#f0c040', fontWeight:900, fontSize:'11px',
                                            background:'rgba(0,0,0,0.7)', borderRadius:'8px',
                                            padding:'1px 5px', zIndex:10,
                                          }}>{Math.round(betAmt)}€</div>
                                        </>
                                      ) : (
                                        !isActive && (
                                          <div style={{ color:'rgba(255,255,255,0.3)', fontSize:'16px', lineHeight:1 }}>+</div>
                                        )
                                      )}
                                    </div>

                                    {/* Montant sous le cercle */}
                                    <div style={{
                                      height:'12px', lineHeight:'12px', fontSize:'9px', fontWeight:600,
                                      color: betAmt > 0 && !isActive ? 'rgba(255,255,255,0.4)' : 'transparent',
                                    }}>{betAmt > 0 && !isActive ? `${Math.round(betAmt)}€` : '\u00a0'}</div>
                                  </div>
                                )
                              })}

                            </div>

                            {/* + droit */}
                            {numSpots < 6
                              ? <button onClick={() => addSpot('right')}
                                  onMouseEnter={() => setHoveredSpot('right')}
                                  onMouseLeave={() => setHoveredSpot(null)}
                                  style={plusBtnStyle(hoveredSpot === 'right')}>+</button>
                              : <div style={{ width:'38px' }} />}

                          </div>

                          {/* Clear / Repeat / Clear All */}
                          <div style={{ display:'flex', gap:'6px' }}>
                            {[
                              { label:'Clear',     action: clearBet,     dis: handBetAmounts[selectedBetHand] === 0 },
                              { label:'Repeat',    action: repeatBet,    dis: !lastHandBetChips[selectedBetHand]?.length },
                              { label:'Clear All', action: clearAllBets, dis: handBetAmounts.every(b => b === 0) },
                            ].map(btn => (
                              <button key={btn.label} onClick={btn.action} disabled={btn.dis}
                                style={{
                                  padding:'4px 10px',
                                  background:'rgba(255,255,255,0.07)',
                                  border:'1px solid rgba(255,255,255,0.1)', borderRadius:'8px',
                                  color: btn.dis ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.65)',
                                  fontSize:'11px', cursor: btn.dis ? 'not-allowed' : 'pointer',
                                  fontFamily:"'Rajdhani',sans-serif", fontWeight:600,
                                }}>{btn.label}</button>
                            ))}
                          </div>
                        </div>
                      )
                    })()
                    : <span style={{ color:'rgba(255,255,255,0.12)', fontSize:'13px' }}>Your hand</span>
                }
              </div>

              {/* Controls */}
              <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:'10px', paddingBottom:'10px' }}>

                {/* Playing: action buttons */}
                {playing && (
                  <div style={{ display:'flex', gap:'8px', flexWrap:'wrap', justifyContent:'center' }}>
                    <ActionBtn label="Hit"       onClick={doHit}       enabled={true}   />
                    <ActionBtn label="Stand"     onClick={doStand}     enabled={true}   />
                    <ActionBtn label="Double"    onClick={doDouble}    enabled={canDbl} />
                    <ActionBtn label="Split"     onClick={doSplit}     enabled={canSpl} />
                    <ActionBtn label="Surrender" onClick={doSurrender} enabled={canSur} />
                  </div>
                )}

                {/* Insurance (par main) */}
                {phase === 'insurance' && (
                  <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:'10px' }}>
                    <div style={{ background:'rgba(234,179,8,0.12)', border:'1px solid rgba(234,179,8,0.3)',
                      borderRadius:'14px', padding:'10px 24px', textAlign:'center' }}>
                      <div style={{ color:'#fde047', fontWeight:700, fontSize:'15px' }}>
                        Dealer shows Ace
                        {bets.length > 1 && (
                          <span style={{ color:'rgba(255,255,255,0.45)', fontWeight:500, fontSize:'13px',
                            marginLeft:'8px' }}>
                            - Hand {insHandIdx + 1} of {bets.length}
                          </span>
                        )}
                      </div>
                      <div style={{ color:'rgba(255,255,255,0.5)', fontSize:'12px' }}>
                        Insurance 2:1 · bet: {bets[insHandIdx] != null ? Math.round(bets[insHandIdx] / 2) : 0}€
                      </div>
                    </div>
                    <div style={{ display:'flex', gap:'10px' }}>
                      <button onClick={() => doInsuranceDecide(true)} style={{ padding:'12px 24px',
                        background:'#eab308', color:'#1a1a1a', border:'none', borderRadius:'12px',
                        fontFamily:"'Rajdhani',sans-serif", fontWeight:900, fontSize:'14px',
                        cursor:'pointer', boxShadow:'0 4px 12px rgba(0,0,0,0.3)' }}>
                        Take Insurance ({bets[insHandIdx] != null ? Math.round(bets[insHandIdx] / 2) : 0}€)
                      </button>
                      <button onClick={() => doInsuranceDecide(false)} style={{ padding:'12px 24px',
                        background:'rgba(255,255,255,0.1)', color:'#f0ece0',
                        border:'1px solid rgba(255,255,255,0.15)', borderRadius:'12px',
                        fontFamily:"'Rajdhani',sans-serif", fontWeight:700, fontSize:'14px',
                        cursor:'pointer' }}>
                        No Thanks
                      </button>
                    </div>
                  </div>
                )}

                {/* Betting: Deal button */}
                {phase === 'betting' && (
                  <button onClick={startHand} disabled={!canDeal}
                    style={{ padding:'14px 56px',
                      background: canDeal ? '#f0c040' : 'rgba(240,192,64,0.25)',
                      color: canDeal ? '#1a1a1a' : 'rgba(26,26,26,0.4)',
                      border:'none', borderRadius:'20px',
                      fontFamily:"'Rajdhani',sans-serif", fontWeight:900, fontSize:'20px',
                      letterSpacing:'1px', cursor: canDeal ? 'pointer' : 'not-allowed',
                      boxShadow: canDeal ? '0 6px 20px rgba(240,192,64,0.3)' : 'none',
                      transition:'all 0.2s' }}>
                    Deal
                  </button>
                )}

                {phase === 'revealing' && (
                  <div style={{ color:'rgba(255,255,255,0.4)', fontSize:'13px', letterSpacing:'1px' }}
                    className="animate-pulse">
                    Dealer playing…
                  </div>
                )}

                {phase === 'result' && (() => {
                  const menuBtns = [
                    { label:'Repeat Bets', sub: canRepeat ? `${lastTotal}€` : 'No prev bets',
                      color:'#059669', dis:!canRepeat, fn: doRepeatBets, delay:'0ms',
                      icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74"/><path d="M3 3v5h5"/></svg> },
                    { label:'Double Bets', sub: canDouble2x ? `${lastTotal}€ → ${lastTotal*2}€` : 'Insufficient funds',
                      color:'#2563eb', dis:!canDouble2x, fn: doDoubleBets, delay:'80ms',
                      icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><text x="3" y="17" fontFamily="sans-serif" fontWeight="800" fontSize="14" fill="currentColor" stroke="none">×2</text></svg> },
                    { label:'Half Bets', sub: canHalf ? `${lastTotal}€ → ${Math.floor(lastTotal/2)}€` : 'No prev bets',
                      color:'#64748b', dis:!canHalf, fn: doHalfBets, delay:'160ms',
                      icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><text x="1" y="17" fontFamily="sans-serif" fontWeight="800" fontSize="13" fill="currentColor" stroke="none">÷2</text></svg> },
                    { label:'New Bets', sub:'Clear all bets',
                      color:'#d97706', dis:false, fn: doNewBets, delay:'240ms',
                      icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg> },
                  ]
                  return (
                    <div style={{ display:'flex', gap:'8px', flexWrap:'wrap', justifyContent:'center' }}>
                      {menuBtns.map(btn => (
                        <button key={btn.label} onClick={btn.dis ? undefined : btn.fn} disabled={btn.dis}
                          style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:'4px',
                            padding:'10px 16px', minWidth:'108px',
                            background: btn.dis ? 'rgba(255,255,255,0.05)' : btn.color,
                            border: btn.dis ? '1px solid rgba(255,255,255,0.08)' : `1px solid ${btn.color}`,
                            borderRadius:'14px', cursor: btn.dis ? 'not-allowed' : 'pointer',
                            opacity: btn.dis ? 0.35 : 1,
                            fontFamily:"'Rajdhani',sans-serif", color:'#fff',
                            boxShadow: btn.dis ? 'none' : '0 4px 12px rgba(0,0,0,0.3)',
                            animation:`menuIn 0.22s ${btn.delay} ease both`,
                            transition:'filter 0.12s, transform 0.12s' }}
                          onMouseEnter={e => { if (!btn.dis) { e.currentTarget.style.filter='brightness(1.15)'; e.currentTarget.style.transform='translateY(-2px)' }}}
                          onMouseLeave={e => { e.currentTarget.style.filter='none'; e.currentTarget.style.transform='translateY(0)' }}>
                          <div style={{ display:'flex', alignItems:'center', gap:'6px' }}>
                            {btn.icon}
                            <span style={{ fontWeight:700, fontSize:'13px', letterSpacing:'0.3px' }}>{btn.label}</span>
                          </div>
                          <span style={{ fontSize:'10px', opacity:0.7, fontWeight:400 }}>{btn.sub}</span>
                        </button>
                      ))}
                    </div>
                  )
                })()}

              </div>
            </div>
          </div>{/* /felt inner */}

          </div>{/* /wood outer */}

          {/* ══ RIGHT SIDEBAR ══ */}
          <div style={{ ...sidebarStyle }}>

            {/* Bankroll */}
            <div style={{ ...sidebarPanelStyle }}>
              <div style={{ color:'#f0c040', fontSize:'9px', fontWeight:700,
                letterSpacing:'2px', textTransform:'uppercase', marginBottom:'4px' }}>Bankroll</div>
              {editingBankroll
                ? <input
                    ref={bankrollInputRef}
                    autoFocus
                    type="number"
                    value={bankrollInput}
                    onChange={e => setBankrollInput(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') commitBankrollEdit(bankrollInputRef)
                      if (e.key === 'Escape') setEditingBankroll(false)
                    }}
                    onBlur={() => commitBankrollEdit(bankrollInputRef)}
                    style={{ background:'transparent', border:'1px solid #f0c040', borderRadius:'6px',
                      color:'#f0ece0', fontFamily:"'Rajdhani',sans-serif", fontWeight:900, fontSize:'24px',
                      width:'100%', padding:'2px 4px', outline:'none' }}
                  />
                : <div
                    onDoubleClick={startEditBankroll}
                    style={{ cursor: phase === 'betting' ? 'text' : 'default' }}
                    title={phase === 'betting' ? 'Double-click to edit' : ''}>
                    <div style={{ color: bankroll <= 0 ? '#f87171' : '#f0ece0', fontWeight:900, fontSize:'24px', lineHeight:1 }}>
                      {bankroll.toFixed(0)}€
                    </div>
                    {showRoundDelta && delta !== 0 && (
                      <div className="round-delta" style={{ color: delta > 0 ? '#4ade80' : '#f87171', fontWeight:700, fontSize:'14px', marginTop:'4px' }}>
                        {delta > 0 ? '+' : ''}{delta}€
                      </div>
                    )}
                    {phase === 'betting' && (
                      <div style={{ fontSize:'9px', color:'rgba(255,255,255,0.25)', marginTop:'2px' }}>dbl-click to edit</div>
                    )}
                  </div>
              }
            </div>

            {/* Chip grid 2×4 */}
            <div style={{ ...sidebarPanelStyle, flex:1, padding:'8px' }}>
              <div style={{ color:'rgba(255,255,255,0.35)', fontSize:'9px', fontWeight:700,
                letterSpacing:'2px', textTransform:'uppercase', marginBottom:'6px' }}>Chips</div>
              {/* paddingTop pour absorber le translateY(-4px) du hover sans dépasser */}
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'8px', paddingTop:'6px' }}>
                {CHIPS.map(chip => {
                  const currentHandBet = handBetAmounts[selectedBetHand]
                  const disabled = phase !== 'betting'
                    || currentHandBet + chip.value > MAX_BET
                    || chip.value > bankroll
                  return (
                    <div key={chip.value} style={{ display:'flex', justifyContent:'center', alignItems:'center' }}>
                      <ChipSVG chip={chip} size={52} disabled={disabled} onClick={() => addChip(chip.value)} />
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Bouton Settings */}
            <button
              onClick={() => { setEditConfig({...gameConfig}); setShowSettings(true) }}
              style={{
                width:'100%', padding:'9px 0', textAlign:'center',
                background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.1)',
                borderRadius:'8px', cursor:'pointer',
                transition:'background 150ms, border-color 150ms',
                fontFamily:"'Rajdhani',sans-serif",
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.09)'
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.25)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'
              }}
            >
              <div style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:'6px' }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" stroke="#c8963c" strokeWidth="1.8"/>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" stroke="#c8963c" strokeWidth="1.8"/>
                </svg>
                <span style={{ color:'rgba(255,255,255,0.55)', fontSize:'10px', fontWeight:700, letterSpacing:'2px', textTransform:'uppercase' }}>Settings</span>
              </div>
            </button>

          </div>

        </div>
      </div>
        {/* ══ SETTINGS MODAL ══ */}
        {showSettings && (() => {
          const cfg = editConfig
          const set = patch => setEditConfig(c => ({...c, ...patch}))

          // Helpers de rendu
          const Section = ({title}) => (
            <div style={{ color:'#c8963c', fontSize:'10px', fontWeight:700, letterSpacing:'2px',
              textTransform:'uppercase', marginBottom:'10px', marginTop:'18px',
              borderBottom:'1px solid rgba(200,150,60,0.2)', paddingBottom:'6px' }}>{title}</div>
          )
          const Row = ({label, children}) => (
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between',
              marginBottom:'10px', gap:'12px' }}>
              <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.7)', flexShrink:0 }}>{label}</div>
              <div style={{ display:'flex', gap:'6px', flexShrink:0 }}>{children}</div>
            </div>
          )
          const Opt = ({active, onClick, children}) => (
            <button onClick={onClick} style={{
              padding:'4px 10px', borderRadius:'8px', fontSize:'11px', fontWeight:600,
              cursor:'pointer', border: active ? '1px solid #c8963c' : '1px solid rgba(255,255,255,0.12)',
              background: active ? 'rgba(200,150,60,0.18)' : 'rgba(255,255,255,0.05)',
              color: active ? '#f0c040' : 'rgba(255,255,255,0.5)',
              transition:'all 0.12s',
            }}>{children}</button>
          )

          return (
            <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.72)', zIndex:200,
              display:'flex', alignItems:'center', justifyContent:'center' }}
              onClick={() => setShowSettings(false)}>
              <div style={{ background:'#0d2214', border:'1px solid rgba(200,150,60,0.38)',
                borderRadius:'14px', padding:'24px', width:'380px', maxHeight:'85vh',
                overflow:'auto', position:'relative' }}
                onClick={e => e.stopPropagation()}>

                {/* Header */}
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'4px' }}>
                  <div style={{ color:'#c8963c', fontWeight:700, fontSize:'13px', letterSpacing:'1.5px' }}>
                    GAME RULES & SETTINGS
                  </div>
                  <button onClick={() => setShowSettings(false)}
                    style={{ background:'none', border:'none', color:'rgba(255,255,255,0.4)',
                      fontSize:'20px', cursor:'pointer', lineHeight:1, padding:'0 2px' }}>×</button>
                </div>

                {/* ─ Payout & Rules ─ */}
                <Section title="Payout & Rules" />

                <Row label="Blackjack Payout">
                  <Opt active={cfg.bjPayout===1.5}  onClick={()=>set({bjPayout:1.5})}>Standard 3:2</Opt>
                  <Opt active={cfg.bjPayout===1.2}  onClick={()=>set({bjPayout:1.2})}>Single Deck 6:5</Opt>
                </Row>

                <Row label="Dealer Rule">
                  <Opt active={!cfg.dealerHitsSoft17} onClick={()=>set({dealerHitsSoft17:false})}>S17</Opt>
                  <Opt active={cfg.dealerHitsSoft17}  onClick={()=>set({dealerHitsSoft17:true})}>H17</Opt>
                </Row>

                <Row label="Late Surrender">
                  <Opt active={cfg.lateSurrender}  onClick={()=>set({lateSurrender:true})}>ON</Opt>
                  <Opt active={!cfg.lateSurrender} onClick={()=>set({lateSurrender:false})}>OFF</Opt>
                </Row>

                <Row label="Double Down">
                  <Opt active={cfg.doubleRestriction==='any'}   onClick={()=>set({doubleRestriction:'any'})}>Any 2</Opt>
                  <Opt active={cfg.doubleRestriction==='9-11'}  onClick={()=>set({doubleRestriction:'9-11'})}>9-11</Opt>
                  <Opt active={cfg.doubleRestriction==='10-11'} onClick={()=>set({doubleRestriction:'10-11'})}>10-11</Opt>
                </Row>

                <Row label="Double After Split">
                  <Opt active={cfg.doubleAfterSplit}  onClick={()=>set({doubleAfterSplit:true})}>ON</Opt>
                  <Opt active={!cfg.doubleAfterSplit} onClick={()=>set({doubleAfterSplit:false})}>OFF</Opt>
                </Row>

                <Row label="Max Hands (splits)">
                  {[2,3,4].map(n => (
                    <Opt key={n} active={cfg.maxSplitHands===n} onClick={()=>set({maxSplitHands:n})}>{n} hands</Opt>
                  ))}
                </Row>

                <Row label="Re-split Aces">
                  <Opt active={cfg.resplitAces}  onClick={()=>set({resplitAces:true})}>ON</Opt>
                  <Opt active={!cfg.resplitAces} onClick={()=>set({resplitAces:false})}>OFF</Opt>
                </Row>

                {/* ─ Shoe Settings ─ */}
                <Section title="Shoe Settings" />

                <Row label="Number of Decks">
                  {[2,4,6,8].map(n => (
                    <Opt key={n} active={cfg.numDecks===n} onClick={()=>set({numDecks:n})}>{n}</Opt>
                  ))}
                </Row>
                {cfg.numDecks <= 2 && (
                  <div style={{ fontSize:'10px', color:'#f97316', marginBottom:'8px', marginTop:'-4px' }}>
                    ⚠ 6:5 payout recommended for single/double deck
                  </div>
                )}

                <Row label={`Penetration - ${Math.round(cfg.penetration*100)}%`}>
                  <input type="range" min="50" max="90" step="5"
                    value={Math.round(cfg.penetration*100)}
                    onChange={e => set({penetration: parseInt(e.target.value)/100})}
                    style={{ width:'140px', accentColor:'#c8963c' }} />
                </Row>
                <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.3)', marginBottom:'8px', marginTop:'-6px' }}>
                  Shuffle after {Math.round(cfg.penetration*100)}% of shoe dealt
                </div>

                {/* ─ Buttons ─ */}
                <div style={{ display:'flex', gap:'8px', marginTop:'20px', justifyContent:'center' }}>
                  <button onClick={() => setShowSettings(false)}
                    style={{ padding:'8px 18px', borderRadius:'10px', border:'1px solid rgba(255,255,255,0.15)',
                      background:'rgba(255,255,255,0.06)', color:'rgba(255,255,255,0.55)',
                      fontSize:'12px', fontWeight:600, cursor:'pointer',
                      fontFamily:"'Rajdhani',sans-serif" }}>Cancel</button>
                  <button onClick={() => applyAndReset(editConfig)}
                    style={{ padding:'8px 22px', borderRadius:'10px', border:'none',
                      background:'#c8963c', color:'#1a1a1a',
                      fontSize:'12px', fontWeight:700, cursor:'pointer',
                      fontFamily:"'Rajdhani',sans-serif",
                      boxShadow:'0 4px 12px rgba(200,150,60,0.3)' }}>
                    Apply & New Shoe
                  </button>
                </div>

              </div>
            </div>
          )
        })()}

        {/* ══ OVERLAY BASIC STRATEGY ══ */}
        {showBSOverlay && (() => {
          const subtitle = [
            `${gameConfig.numDecks} Decks`,
            gameConfig.dealerHitsSoft17 ? 'H17' : 'S17',
            gameConfig.doubleAfterSplit ? 'DAS' : 'No DAS',
            gameConfig.lateSurrender ? 'Late Surrender' : 'No Surrender',
          ].join(' · ')
          const situation = (phase === 'playing' || phase === 'insurance') && activeHand.length > 0 && upcard
          return (
            <div
              style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.85)', zIndex:300,
                display:'flex', alignItems:'center', justifyContent:'center' }}
              onClick={() => setShowBSOverlay(false)}
            >
              <div
                style={{ background:'#0d2214', border:'1px solid rgba(200,150,60,0.5)',
                  borderRadius:'12px', padding:'16px', maxWidth:'90vw', maxHeight:'90vh',
                  display:'flex', flexDirection:'column', gap:'12px' }}
                onClick={e => e.stopPropagation()}
              >
                {/* Header */}
                <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:'16px' }}>
                  <div>
                    <div style={{ color:'#f0ece0', fontWeight:800, fontSize:'16px', fontFamily:"'Rajdhani',sans-serif" }}>
                      Basic Strategy
                    </div>
                    <div style={{ color:'rgba(255,255,255,0.35)', fontSize:'11px', marginTop:'2px' }}>{subtitle}</div>
                  </div>
                  <button onClick={() => setShowBSOverlay(false)}
                    style={{ background:'none', border:'none', color:'#c8963c', fontSize:'20px',
                      cursor:'pointer', lineHeight:1, padding:'0', opacity:0.7,
                      transition:'opacity 0.15s' }}
                    onMouseEnter={e => e.currentTarget.style.opacity='1'}
                    onMouseLeave={e => e.currentTarget.style.opacity='0.7'}
                  >×</button>
                </div>
                {/* Image */}
                <img src={basicStrategyImg} alt="Basic Strategy chart"
                  style={{ maxWidth:'100%', maxHeight:'calc(90vh - 100px)',
                    objectFit:'contain', borderRadius:'8px', display:'block' }} />
                {/* Bannière contextuelle */}
                {situation && (
                  <div style={{ background:'#1a3a1a', borderLeft:'3px solid #f0c040',
                    padding:'8px 12px', borderRadius:'0 6px 6px 0', fontSize:'12px',
                    color:'rgba(255,255,255,0.8)', animation:'fadeInFast 0.2s both' }}>
                    Current situation: <strong>{handValue(activeHand)}{isSoft(activeHand) ? ' soft' : ''}</strong> vs <strong>{upcard.rank.toUpperCase()}</strong>
                  </div>
                )}
              </div>
            </div>
          )
        })()}

        {/* ══ OVERLAY ILLUSTRIOUS 18 ══ */}
        {showI18Overlay && (() => {
          const situation = (phase === 'playing' || phase === 'insurance') && activeHand.length > 0 && upcard
          return (
            <div
              style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.85)', zIndex:300,
                display:'flex', alignItems:'center', justifyContent:'center' }}
              onClick={() => setShowI18Overlay(false)}
            >
              <div
                style={{ background:'#0d2214', border:'1px solid rgba(200,150,60,0.5)',
                  borderRadius:'12px', padding:'16px', maxWidth:'90vw', maxHeight:'90vh',
                  display:'flex', flexDirection:'column', gap:'12px' }}
                onClick={e => e.stopPropagation()}
              >
                {/* Header */}
                <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:'16px' }}>
                  <div>
                    <div style={{ color:'#f0ece0', fontWeight:800, fontSize:'16px', fontFamily:"'Rajdhani',sans-serif" }}>
                      Illustrious 18 - Hi-Lo Deviations
                    </div>
                    <div style={{ color:'rgba(255,255,255,0.35)', fontSize:'11px', marginTop:'2px' }}>
                      Override basic strategy at True Count threshold
                    </div>
                  </div>
                  <button onClick={() => setShowI18Overlay(false)}
                    style={{ background:'none', border:'none', color:'#c8963c', fontSize:'20px',
                      cursor:'pointer', lineHeight:1, padding:'0', opacity:0.7,
                      transition:'opacity 0.15s' }}
                    onMouseEnter={e => e.currentTarget.style.opacity='1'}
                    onMouseLeave={e => e.currentTarget.style.opacity='0.7'}
                  >×</button>
                </div>
                {/* Image */}
                <img src={i18Img} alt="Illustrious 18 deviations"
                  style={{ maxWidth:'100%', maxHeight:'calc(90vh - 100px)',
                    objectFit:'contain', borderRadius:'8px', display:'block' }} />
                {/* Bannière contextuelle */}
                {situation && (
                  <div style={{ background:'#1a3a1a', borderLeft:'3px solid #f0c040',
                    padding:'8px 12px', borderRadius:'0 6px 6px 0', fontSize:'12px',
                    color:'rgba(255,255,255,0.8)', animation:'fadeInFast 0.2s both' }}>
                    Current situation: <strong>{handValue(activeHand)}{isSoft(activeHand) ? ' soft' : ''}</strong> vs <strong>{upcard.rank.toUpperCase()}</strong>
                  </div>
                )}
              </div>
            </div>
          )
        })()}

    </>
  )
}
