import { type PointerEvent, useEffect, useMemo, useRef, useState } from 'react'

import { EvidenceIcon, Portrait } from '../../components/art'
import { Button, Empty, EvidenceTag, Eyebrow, Panel } from '../../components/ui'
import { useGame } from '../../store/game'
import {
  type BoardLayout,
  CARD_H,
  CARD_W,
  defaultPosition,
  loadLayout,
  minutes,
  type Point,
  sameLink,
  saveLayout,
} from './boardLayout'

interface Card {
  id: string
  kind: 'person' | 'evidence' | 'statement'
  title: string
  body: string
  row: number
  index: number
}

const KIND_STYLE: Record<Card['kind'], string> = {
  person: 'border-[#2f4a68]',
  evidence: 'border-[#9a6408]',
  statement: 'border-[#d8b84a]',
}

/** 카드를 조금씩 기울여 손으로 붙인 느낌을 낸다. */
const TILTS = [-2, 1.5, -1, 2, -1.5, 1]

const TYPE_LABEL: Record<string, string> = {
  location: '장소',
  time: '시간',
  statement: '진술',
  person: '인물',
  possession: '소유물',
}

function Timeline({ items }: { items: { id: string; label: string; time: string }[] }) {
  const start = minutes('20:30')
  const end = minutes('22:00')
  const pct = (t: string) => ((minutes(t) - start) / (end - start)) * 100
  const ticks = ['20:30', '21:00', '21:30', '22:00']
  // 5분 안에 몰린 점은 위로 쌓는다
  const stack = (i: number) =>
    items.slice(0, i).filter((x) => Math.abs(minutes(x.time) - minutes(items[i].time)) < 5).length
  return (
    <div className="flex flex-col gap-2">
      <h2 className="font-bold">시간선</h2>
      {items.length === 0 && <Empty>시각이 기록된 증거를 찾으면 여기에 표시된다.</Empty>}
      <div className="relative mx-2 mt-14 mb-8 h-1 rounded bg-line" aria-hidden>
        {ticks.map((t) => (
          <span
            key={t}
            className="absolute top-3 -translate-x-1/2 font-mono text-xs text-muted"
            style={{ left: `${pct(t)}%` }}
          >
            {t}
          </span>
        ))}
        {items.map((it, i) => (
          <span
            key={it.id}
            className="absolute flex h-5 w-5 -translate-x-1/2 items-center justify-center rounded-full border-2 border-sheet bg-tag font-mono text-[10px] font-bold text-sheet"
            style={{ left: `${pct(it.time)}%`, top: -8 - stack(i) * 22 }}
          >
            {i + 1}
          </span>
        ))}
      </div>
      {/* 같은 시각에 몰려도 겹치지 않게 이름은 번호와 함께 목록으로 */}
      <ol className="flex flex-col gap-1 text-sm">
        {items.map((it, i) => (
          <li key={it.id} className="flex items-baseline gap-2">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-tag font-mono text-[10px] font-bold text-sheet">
              {i + 1}
            </span>
            <span className="font-mono text-tag">{it.time}</span>
            <span>{it.label}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}

export function BoardScreen() {
  const { session, board, loadBoard, chats, sessionId } = useGame()
  const [layout, setLayout] = useState<BoardLayout>(() => loadLayout(sessionId ?? ''))
  const [linking, setLinking] = useState<string | null>(null)
  const [linkMode, setLinkMode] = useState(false)
  const drag = useRef<{ id: string; dx: number; dy: number } | null>(null)
  const area = useRef<HTMLDivElement>(null)

  useEffect(() => {
    void loadBoard()
  }, [loadBoard])

  useEffect(() => {
    if (sessionId) saveLayout(sessionId, layout)
  }, [sessionId, layout])

  const cards = useMemo<Card[]>(() => {
    if (!session) return []
    const people = session.suspects.map((s, i) => ({
      id: s.suspect_id,
      kind: 'person' as const,
      title: s.name,
      body: s.role,
      row: 0,
      index: i,
    }))
    const evidence = session.evidence.map((e, i) => ({
      id: e.evidence_id,
      kind: 'evidence' as const,
      title: e.name,
      body: e.description,
      row: 1 + Math.floor(i / 4),
      index: i % 4,
    }))
    const pinned = Object.entries(chats).flatMap(([npc, list]) =>
      list
        .filter((m) => m.pinned && m.meta)
        .map((m) => ({ npc, text: m.text, turn: m.meta!.turn })),
    )
    const evidenceRows = Math.ceil(session.evidence.length / 4)
    const statements = pinned.map((p, i) => ({
      id: `stmt-${p.npc}-${p.turn}`,
      kind: 'statement' as const,
      title: `진술 · ${session.suspects.find((s) => s.suspect_id === p.npc)?.name ?? p.npc}`,
      body: p.text,
      row: 1 + evidenceRows + Math.floor(i / 4),
      index: i % 4,
    }))
    return [...people, ...evidence, ...statements]
  }, [session, chats])

  if (!session) return null

  const pos = (c: Card): Point => layout.positions[c.id] ?? defaultPosition(c.row, c.index)
  const height = Math.max(
    360,
    ...cards.map((c) => pos(c).y + CARD_H + 24),
  )
  const center = (id: string) => {
    const c = cards.find((x) => x.id === id)
    if (!c) return null
    const p = pos(c)
    return { x: p.x + CARD_W / 2, y: p.y + CARD_H / 2 }
  }

  const onPointerDown = (e: PointerEvent, c: Card) => {
    if (linkMode) return
    const p = pos(c)
    const rect = area.current!.getBoundingClientRect()
    drag.current = { id: c.id, dx: e.clientX - rect.left - p.x, dy: e.clientY - rect.top - p.y }
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }
  const onPointerMove = (e: PointerEvent) => {
    if (!drag.current || !area.current) return
    const rect = area.current.getBoundingClientRect()
    const x = Math.min(Math.max(0, e.clientX - rect.left - drag.current.dx), rect.width - CARD_W)
    const y = Math.max(0, e.clientY - rect.top - drag.current.dy)
    const id = drag.current.id
    setLayout((l) => ({ ...l, positions: { ...l.positions, [id]: { x, y } } }))
  }
  const onCardClick = (c: Card) => {
    if (!linkMode) return
    if (!linking) return setLinking(c.id)
    if (linking !== c.id) {
      const link: [string, string] = [linking, c.id]
      setLayout((l) =>
        l.links.some((x) => sameLink(x, link))
          ? { ...l, links: l.links.filter((x) => !sameLink(x, link)) }
          : { ...l, links: [...l.links, link] },
      )
    }
    setLinking(null)
  }

  const timed = session.evidence
    .filter((e) => e.time)
    .map((e) => ({ id: e.evidence_id, label: e.name, time: e.time! }))
    .sort((a, b) => minutes(a.time) - minutes(b.time))

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Eyebrow>수사 보드</Eyebrow>
        <div className="flex flex-wrap gap-2">
          <Button
            variant={linkMode ? 'primary' : 'ghost'}
            onClick={() => {
              setLinkMode(!linkMode)
              setLinking(null)
            }}
            aria-pressed={linkMode}
          >
            {linkMode ? '연결 끝내기' : '카드 연결하기'}
          </Button>
          <Button
            variant="ghost"
            onClick={() => setLayout({ positions: {}, links: [] })}
          >
            배치 초기화
          </Button>
        </div>
      </div>
      <p className="text-sm text-muted">
        {linkMode
          ? linking
            ? '이어 붙일 두 번째 카드를 누른다. 이미 이어진 두 카드를 누르면 연결이 풀린다.'
            : '연결할 첫 번째 카드를 누른다.'
          : '카드를 끌어서 옮기고, "카드 연결하기"로 빨간 실을 이어 보자. 노란 쪽지는 심문에서 저장한 진술이다.'}
      </p>

      <div className="cork overflow-x-auto rounded-lg">
        <div
          ref={area}
          className="relative min-w-[820px]"
          style={{ height }}
          onPointerMove={onPointerMove}
          onPointerUp={() => (drag.current = null)}
        >
          <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden>
            {layout.links.map(([a, b]) => {
              const p = center(a)
              const q = center(b)
              if (!p || !q) return null
              // 압정에서 압정으로, 살짝 처지는 빨간 실
              const y1 = p.y - CARD_H / 2
              const y2 = q.y - CARD_H / 2
              const sag = Math.min(60, Math.hypot(q.x - p.x, y2 - y1) / 5)
              return (
                <path
                  key={`${a}-${b}`}
                  d={`M${p.x} ${y1} Q${(p.x + q.x) / 2} ${(y1 + y2) / 2 + sag} ${q.x} ${y2}`}
                  stroke="#c62828"
                  strokeWidth={2.5}
                  fill="none"
                  style={{ filter: 'drop-shadow(0 2px 1px rgb(0 0 0 / 0.35))' }}
                />
              )
            })}
          </svg>
          {cards.map((c) => {
            const p = pos(c)
            return (
              <div
                key={c.id}
                role={linkMode ? 'button' : undefined}
                tabIndex={linkMode ? 0 : undefined}
                aria-label={`${c.title} 카드`}
                onPointerDown={(e) => onPointerDown(e, c)}
                onClick={() => onCardClick(c)}
                onKeyDown={(e) => e.key === 'Enter' && onCardClick(c)}
                className={`pin absolute flex touch-none gap-2 rounded-sm border-t-4 p-2 shadow-[0_4px_8px_rgb(0_0_0/0.35)] select-none ${
                  c.kind === 'statement' ? 'bg-[#fff4b8] text-[#2a2018]' : 'bg-[#fbf6ea] text-[#2a2018]'
                } ${KIND_STYLE[c.kind]} ${linkMode ? 'cursor-pointer' : 'cursor-grab'} ${linking === c.id ? 'ring-4 ring-bad' : ''}`}
                style={{
                  left: p.x,
                  top: p.y,
                  width: CARD_W,
                  height: CARD_H,
                  transform: `rotate(${TILTS[cards.indexOf(c) % TILTS.length]}deg)`,
                }}
              >
                {c.kind === 'person' && (
                  <Portrait role={c.body} index={c.index} emotion={session.npcs.find((n) => n.npc_id === c.id)?.emotion} size={60} />
                )}
                {c.kind === 'evidence' && (
                  <span className="flex h-[60px] w-[60px] shrink-0 items-center justify-center bg-[var(--photo)]">
                    <EvidenceIcon name={c.title} size={48} />
                  </span>
                )}
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="flex items-baseline gap-1 text-sm font-bold">
                    {c.kind === 'evidence' && <EvidenceTag id={c.id} />}
                    <span className="truncate">{c.title}</span>
                  </span>
                  <span className={`line-clamp-3 text-xs leading-snug text-[#6b5a47] ${c.kind === 'statement' ? 'font-hand text-base leading-4' : ''}`}>
                    {c.body}
                  </span>
                </span>
              </div>
            )
          })}
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel>
          <Timeline items={timed} />
        </Panel>
        <Panel className="flex flex-col gap-3">
          <h2 className="font-bold">모순</h2>
          {!board?.contradictions.length && (
            <Empty>거짓 진술과 그것을 뒤집는 증거가 모두 확보되면 여기에 표시된다.</Empty>
          )}
          {board?.contradictions.map((c, i) => (
            <div
              key={i}
              data-source={c.source}
              className={`flex flex-col gap-1 border-l-2 pl-3 text-sm ${c.source === 'rule' ? 'border-bad' : 'border-dashed border-tag'}`}
            >
              <p className="flex flex-wrap items-center gap-2 text-xs text-muted">
                <span className={`font-medium ${c.source === 'rule' ? 'text-bad' : 'text-tag'}`}>
                  {TYPE_LABEL[c.type] ?? c.type} 모순
                </span>
                {session.suspects.find((s) => s.suspect_id === c.npc_id)?.name}
                <span className="rounded bg-soft px-1.5 font-mono">
                  {c.source === 'rule' ? '규칙 판정' : `AI 판정 ${Math.round((c.confidence ?? 0) * 100)}%`}
                </span>
              </p>
              <p>“{c.statement}”</p>
              {c.other_statements?.map((s) => (
                <p key={s} className="text-muted">
                  ↔ 앞선 진술 “{s}”
                </p>
              ))}
              {c.evidence_id && (
                <p className="text-muted">
                  ↔ <EvidenceTag id={c.evidence_id} /> {c.evidence_name}
                </p>
              )}
              {c.explanation && <p className="text-xs text-muted">{c.explanation}</p>}
            </div>
          ))}
          {board?.contradictions.some((c) => c.source === 'llm') && (
            <p className="text-xs text-muted">AI 판정은 보조 자료다. 확정된 모순은 규칙 판정이다.</p>
          )}
        </Panel>
      </div>
    </div>
  )
}
