import { type PointerEvent, useEffect, useMemo, useRef, useState } from 'react'

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
  person: 'border-accent',
  evidence: 'border-tag',
  statement: 'border-line',
}

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
  return (
    <div className="flex flex-col gap-2">
      <h2 className="font-bold">시간선</h2>
      {items.length === 0 && <Empty>시각이 기록된 증거를 찾으면 여기에 표시된다.</Empty>}
      <div className="relative mx-2 mt-6 mb-10 h-1 rounded bg-line" aria-hidden={items.length === 0}>
        {ticks.map((t) => (
          <span
            key={t}
            className="absolute -top-6 -translate-x-1/2 font-mono text-xs text-muted"
            style={{ left: `${pct(t)}%` }}
          >
            {t}
          </span>
        ))}
        {items.map((it, i) => (
          <div
            key={it.id}
            className="absolute -translate-x-1/2"
            style={{ left: `${pct(it.time)}%`, top: -5 }}
          >
            <span className="block h-3.5 w-3.5 rounded-full border-2 border-sheet bg-tag" />
            <span
              className="absolute left-1/2 mt-1 w-max max-w-40 -translate-x-1/2 text-center text-xs"
              style={{ top: 14 + (i % 2) * 18 }}
            >
              <span className="font-mono text-tag">{it.time}</span> {it.label}
            </span>
          </div>
        ))}
      </div>
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
          : '카드를 끌어서 옮긴다. 인물은 파란 테, 증거는 노란 테, 저장한 진술은 회색 테다.'}
      </p>

      <div className="overflow-x-auto rounded-lg border border-line bg-soft">
        <div
          ref={area}
          className="relative min-w-[760px]"
          style={{ height }}
          onPointerMove={onPointerMove}
          onPointerUp={() => (drag.current = null)}
        >
          <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden>
            {layout.links.map(([a, b]) => {
              const p = center(a)
              const q = center(b)
              if (!p || !q) return null
              return (
                <line
                  key={`${a}-${b}`}
                  x1={p.x}
                  y1={p.y}
                  x2={q.x}
                  y2={q.y}
                  stroke="var(--bad)"
                  strokeWidth={2}
                  strokeDasharray="5 4"
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
                className={`absolute flex touch-none flex-col gap-1 overflow-hidden rounded-md border-2 bg-sheet p-2 shadow-sm select-none ${
                  KIND_STYLE[c.kind]
                } ${linkMode ? 'cursor-pointer' : 'cursor-grab'} ${linking === c.id ? 'ring-2 ring-bad' : ''}`}
                style={{ left: p.x, top: p.y, width: CARD_W, height: CARD_H }}
              >
                <p className="flex items-baseline gap-1 text-sm font-bold">
                  {c.kind === 'evidence' && <EvidenceTag id={c.id} />}
                  <span className="truncate">{c.title}</span>
                </p>
                <p className="line-clamp-2 text-xs leading-snug text-muted">{c.body}</p>
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
