import { Polaroid } from '../../components/art'
import { Button, Empty, EvidenceTag, Eyebrow, Panel } from '../../components/ui'
import type { SceneObjectView } from '../../services/api'
import { useGame } from '../../store/game'
import { MUSEUM_ROOMS, type Room, spotPosition, VIEWBOX } from './layout'

/** 방 이름으로 바닥 무늬를 고른다 (장식). */
function floorFill(room: Room): string {
  if (room.outdoor) return /주차/.test(room.name) ? 'url(#asphalt)' : 'url(#grass)'
  if (/전시/.test(room.name)) return 'url(#marble)'
  return 'url(#wood)'
}

/** 방 이름으로 가구 그림을 고른다 (장식, 정답과 무관). */
function Furniture({ room }: { room: Room }) {
  const { x, y, w, h } = room
  const common = { stroke: '#3a2c20', strokeWidth: 1.5, opacity: 0.6 }
  if (/전시/.test(room.name))
    return (
      <g {...common}>
        {[0.25, 0.5, 0.75].map((f) => (
          <g key={f}>
            <rect x={x + w * f - 16} y={y + 34} width={32} height={22} fill="#cfe6f2" />
            <path d={`M${x + w * f - 6} ${y + 45} l6 -6 l6 6 l-6 6 z`} fill="#9fd0f2" />
          </g>
        ))}
        <rect x={x + w / 2 - 50} y={y + h - 30} width={100} height={12} rx={6} fill="#b98a5a" />
      </g>
    )
  if (/보안/.test(room.name))
    return (
      <g {...common}>
        {[0, 1, 2].map((i) => (
          <rect key={i} x={x + 14 + i * 34} y={y + 32} width={28} height={18} fill="#1f2e3d" />
        ))}
        <rect x={x + 10} y={y + 52} width={w - 20} height={8} fill="#8a6a4a" />
      </g>
    )
  if (/사무/.test(room.name))
    return (
      <g {...common}>
        <rect x={x + 16} y={y + 34} width={60} height={26} fill="#8a6a4a" />
        <rect x={x + 26} y={y + 38} width={18} height={12} fill="#fffdf6" />
        <rect x={x + w - 32} y={y + 30} width={20} height={60} fill="#a07850" />
      </g>
    )
  if (/휴게/.test(room.name))
    return (
      <g {...common}>
        <rect x={x + 12} y={y + 34} width={54} height={18} rx={6} fill="#9b6b8a" />
        {[0, 1, 2, 3].map((i) => (
          <rect
            key={i}
            x={x + w - 52 + (i % 2) * 20}
            y={y + 30 + Math.floor(i / 2) * 22}
            width={18}
            height={20}
            fill="#9aa4ad"
          />
        ))}
      </g>
    )
  if (/복원/.test(room.name))
    return (
      <g {...common}>
        <rect x={x + 12} y={y + 34} width={w - 48} height={22} fill="#7f6a55" />
        <circle cx={x + 36} cy={y + 45} r={6} fill="#cfe6f2" />
        <rect x={x + w - 30} y={y + 30} width={18} height={28} fill="#5a5a5a" />
      </g>
    )
  if (/흡연/.test(room.name))
    return (
      <g {...common}>
        <rect x={x + 16} y={y + 34} width={50} height={8} fill="#8a6a4a" />
        <rect x={x + w - 40} y={y + 28} width={22} height={34} fill="#c0392b" />
      </g>
    )
  if (/주차/.test(room.name))
    return (
      <g {...common}>
        {[0, 1].map((i) => (
          <rect key={i} x={x + 30 + i * 90} y={y + 30} width={60} height={28} rx={8} fill={i ? '#6f8fb0' : '#b0706f'} />
        ))}
      </g>
    )
  return null
}

function Magnifier({ cx, cy, done }: { cx: number; cy: number; done: boolean }) {
  if (done)
    return (
      <g pointerEvents="none">
        <circle cx={cx} cy={cy} r={13} fill="var(--ok)" stroke="#fff" strokeWidth={2} />
        <path d={`M${cx - 6} ${cy} l4 5 l8 -10`} stroke="#fff" strokeWidth={3} fill="none" strokeLinecap="round" />
      </g>
    )
  return (
    <g pointerEvents="none">
      <circle cx={cx} cy={cy} r={22} fill="#f2b632" opacity={0.35}>
        <animate attributeName="r" values="14;25;14" dur="2.2s" repeatCount="indefinite" />
      </circle>
      <circle cx={cx - 2} cy={cy - 2} r={9} fill="#fff8e1" stroke="#2a2018" strokeWidth={3} />
      <path d={`M${cx + 4} ${cy + 4} l8 8`} stroke="#2a2018" strokeWidth={4} strokeLinecap="round" />
    </g>
  )
}

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
    <div className="overflow-x-auto rounded-md bg-[#cdbd9c] p-1 shadow-inner">
      <svg
        viewBox={`0 0 ${VIEWBOX.w} ${VIEWBOX.h}`}
        className="h-auto w-full min-w-[560px]"
        role="group"
        aria-label="현장 평면도"
      >
        <defs>
          <pattern id="wood" width={16} height={16} patternUnits="userSpaceOnUse">
            <rect width={16} height={16} fill="#e7d3b0" />
            <path d="M0 8 H16" stroke="#d6bd93" strokeWidth={1} />
          </pattern>
          <pattern id="marble" width={24} height={24} patternUnits="userSpaceOnUse">
            <rect width={24} height={24} fill="#f2efe8" />
            <path d="M0 0 H24 V24" stroke="#ddd6c8" strokeWidth={1} fill="none" />
          </pattern>
          <pattern id="grass" width={12} height={12} patternUnits="userSpaceOnUse">
            <rect width={12} height={12} fill="#b9cf9a" />
            <path d="M3 9 l1 -4 M8 10 l1 -4" stroke="#93ad74" strokeWidth={1} />
          </pattern>
          <pattern id="asphalt" width={10} height={10} patternUnits="userSpaceOnUse">
            <rect width={10} height={10} fill="#a8a8a4" />
            <circle cx={3} cy={4} r={0.8} fill="#8c8c88" />
          </pattern>
        </defs>
        {MUSEUM_ROOMS.map((room) => (
          <g key={room.name}>
            <rect
              x={room.x}
              y={room.y}
              width={room.w}
              height={room.h}
              rx={4}
              fill={floorFill(room)}
              stroke="#5a4634"
              strokeWidth={room.outdoor ? 2 : 4}
              strokeDasharray={room.outdoor ? '6 5' : undefined}
            />
            <Furniture room={room} />
            <rect
              x={room.x + 6}
              y={room.y + 6}
              width={room.name.length * 13 + 12}
              height={20}
              rx={3}
              fill="#fbf6ea"
              opacity={0.92}
            />
            <text x={room.x + 12} y={room.y + 21} fontSize={13} fontWeight={700} fill="#3a2c20">
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
                <Magnifier cx={cx} cy={cy} done={obj.collected} />
                <rect
                  x={cx - obj.spot.length * 6.5 - 6}
                  y={cy + 21}
                  width={obj.spot.length * 13 + 12}
                  height={18}
                  rx={9}
                  fill={obj.collected ? 'var(--ok)' : '#2a2018'}
                  opacity={0.88}
                  pointerEvents="none"
                />
                <text x={cx} y={cy + 34} textAnchor="middle" fontSize={12} fill="#fff8ee" pointerEvents="none">
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
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
      <Panel className="flex min-w-0 flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <Eyebrow>현장 조사</Eyebrow>
          <p className="font-mono text-sm text-muted">
            조사 {done} / {session.scene.length}
          </p>
        </div>
        <p className="text-sm text-muted">반짝이는 돋보기를 눌러 조사한다. 찾은 증거는 사진으로 사건 노트에 붙는다.</p>
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
                  o.collected ? 'border-tag bg-tag-soft text-tag' : 'border-line bg-sheet hover:border-accent'
                }`}
              >
                {o.collected ? '✓ ' : ''}
                {o.location_name} · {o.spot}
              </button>
            </li>
          ))}
        </ul>
      </Panel>

      <aside className="flex flex-col gap-4">
        <Panel className="flex flex-col gap-3">
          <h2 className="font-title text-lg font-bold">사건 노트</h2>
          {session.evidence.length === 0 && <Empty>아직 찾은 증거가 없다.</Empty>}
          <ul className="flex flex-col gap-3">
            {session.evidence.map((e, i) => (
              <li key={e.evidence_id} className="pop-in flex gap-3 border-t border-line pt-3 first:border-0 first:pt-0">
                <Polaroid name={e.name} tilt={i % 2 ? 3 : -3} size={44} />
                <div className="min-w-0">
                  <p className="flex items-baseline gap-2">
                    <EvidenceTag id={e.evidence_id} />
                    <span className="font-medium">{e.name}</span>
                  </p>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{e.description}</p>
                </div>
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
