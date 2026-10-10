import { useGame } from '../store/game'

/** 개발자 모드(?dev=1) 전용. 각 API 호출의 응답 원문을 보여 준다. */
export function DevPanel() {
  const { devLog, sessionId } = useGame()
  return (
    <aside className="flex max-h-[80vh] flex-col gap-2 overflow-y-auto rounded-lg bg-soft p-4 text-xs">
      <p className="font-mono tracking-widest text-accent uppercase">개발자 모드</p>
      <p className="font-mono break-all text-muted">session {sessionId}</p>
      {devLog.length === 0 && <p className="text-muted">행동하면 API 응답이 여기에 쌓인다.</p>}
      {devLog.map((e, i) => (
        <div key={i} className="border-l-2 border-line pl-2">
          <p className="font-mono font-semibold">
            {e.at} · {e.action}
          </p>
          <p className="font-mono break-all text-muted">{e.detail}</p>
        </div>
      ))}
    </aside>
  )
}
