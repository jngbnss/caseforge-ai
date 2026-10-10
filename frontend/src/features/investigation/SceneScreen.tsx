import { Button, Empty, EvidenceTag, Eyebrow, Panel } from '../../components/ui'
import type { SceneObjectView } from '../../services/api'
import { useGame } from '../../store/game'
import { MUSEUM_ROOMS, spotPosition, VIEWBOX } from './layout'

function FloorPlan({
  scene,
  onInspect,
  disabled,
}: {
  scene: SceneObjectView[]
  onInspect: (id: string) => void
  disabled: boolean
}) {
  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${VIEWBOX.w} ${VIEWBOX.h}`}
        className="h-auto w-full min-w-[560px]"
        role="group"
        aria-label="한빛시립박물관 평면도"
      >
        {MUSEUM_ROOMS.map((room) => (
          <g key={room.name}>
            <rect
              x={room.x}
              y={room.y}
              width={room.w}
              height={room.h}
              rx={6}
              fill={room.outdoor ? 'transparent' : 'var(--sheet)'}
              stroke="var(--line)"
              strokeWidth={2}
              strokeDasharray={room.outdoor ? '6 5' : undefined}
            />
            <text x={room.x + 10} y={room.y + 22} fontSize={13} fill="var(--muted)">
              {room.name}
            </text>
          </g>
        ))}
        {MUSEUM_ROOMS.map((room) => {
          const here = scene.filter((o) => o.location_name === room.name)
          return here.map((obj, i) => {
            const { cx, cy } = spotPosition(room, i, here.length)
            return (
              <g
                key={obj.evidence_id}
                role="button"
                tabIndex={obj.collected || disabled ? -1 : 0}
                aria-label={`${obj.spot} 조사${obj.collected ? ' (완료)' : ''}`}
                onClick={() => !obj.collected && !disabled && onInspect(obj.evidence_id)}
                onKeyDown={(e) => {
                  if ((e.key === 'Enter' || e.key === ' ') && !obj.collected && !disabled) {
                    e.preventDefault()
                    onInspect(obj.evidence_id)
                  }
                }}
                className={`spot ${obj.collected ? '' : 'cursor-pointer'}`}
              >
                {/* 고정 크기 클릭 영역: 맥박 애니메이션과 무관하게 누르기 쉽다 */}
                <circle className="spot-ring" cx={cx} cy={cy} r={26} fill="transparent" />
                {!obj.collected && (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={20}
                    fill="var(--tag)"
                    opacity={0.18}
                    pointerEvents="none"
                  >
                    <animate attributeName="r" values="14;22;14" dur="2.4s" repeatCount="indefinite" />
                  </circle>
                )}
                <circle
                  cx={cx}
                  cy={cy}
                  r={11}
                  fill={obj.collected ? 'var(--tag)' : 'var(--sheet)'}
                  stroke="var(--tag)"
                  strokeWidth={2.5}
                />
                <text
                  x={cx}
                  y={cy + 30}
                  textAnchor="middle"
                  fontSize={12}
                  fill={obj.collected ? 'var(--tag)' : 'var(--ink)'}
                >
                  {obj.spot}
                </text>
              </g>
            )
          })
        })}
      </svg>
    </div>
  )
}

export function SceneScreen() {
  const { session, collect, busy, goTo } = useGame()
  if (!session) return null
  const done = session.scene.filter((o) => o.collected).length
  const openPuzzles = session.puzzles.filter((p) => p.available && !p.solved)
  const finished = Boolean(session.deduction)

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
      <Panel className="flex min-w-0 flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <Eyebrow>현장 조사</Eyebrow>
          <p className="font-mono text-sm text-muted">
            조사 {done} / {session.scene.length}
          </p>
        </div>
        <p className="text-sm text-muted">노란 점을 눌러 조사한다. 찾은 것은 사건 노트에 기록된다.</p>
        <FloorPlan
          scene={session.scene}
          onInspect={(id) => void collect(id)}
          disabled={Boolean(busy) || finished}
        />
        <ul className="flex flex-wrap gap-2" aria-label="조사 지점 목록">
          {session.scene.map((o) => (
            <li key={o.evidence_id}>
              <button
                type="button"
                disabled={o.collected || Boolean(busy) || finished}
                onClick={() => void collect(o.evidence_id)}
                className={`rounded-full border px-3 py-1 text-xs ${
                  o.collected ? 'border-tag bg-tag-soft text-tag' : 'border-line hover:border-accent'
                }`}
              >
                {o.location_name} · {o.spot}
              </button>
            </li>
          ))}
        </ul>
      </Panel>

      <aside className="flex flex-col gap-4">
        <Panel className="flex flex-col gap-3">
          <h2 className="font-bold">사건 노트</h2>
          {session.evidence.length === 0 && <Empty>아직 찾은 증거가 없다.</Empty>}
          <ul className="flex flex-col gap-3">
            {session.evidence.map((e) => (
              <li key={e.evidence_id} className="border-t border-line pt-3 first:border-0 first:pt-0">
                <p className="flex items-baseline gap-2">
                  <EvidenceTag id={e.evidence_id} />
                  <span className="font-medium">{e.name}</span>
                </p>
                <p className="mt-1 text-sm leading-relaxed text-muted">{e.description}</p>
              </li>
            ))}
          </ul>
        </Panel>
        {openPuzzles.length > 0 && (
          <Panel className="flex flex-col gap-2 border-tag">
            <p className="text-sm">풀 수 있는 퍼즐이 {openPuzzles.length}개 있다.</p>
            <ul className="text-sm text-muted">
              {openPuzzles.map((p) => (
                <li key={p.puzzle_id}>· {p.title}</li>
              ))}
            </ul>
            <Button variant="ghost" onClick={() => goTo('puzzles')}>
              퍼즐로 이동
            </Button>
          </Panel>
        )}
      </aside>
    </div>
  )
}
