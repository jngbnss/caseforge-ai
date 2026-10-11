import { Polaroid, Portrait } from '../../components/art'
import { Button, Eyebrow, Panel } from '../../components/ui'
import { useGame } from '../../store/game'

export function BriefingScreen() {
  const { session, goTo } = useGame()
  if (!session) return null
  const b = session.briefing
  return (
    <div className="flex flex-col gap-5">
      <Panel className="relative flex flex-col gap-4 overflow-hidden">
        <span className="stamp absolute top-5 right-5 rounded px-3 py-1 text-lg font-extrabold" aria-hidden>
          수사 의뢰
        </span>
        <Eyebrow>사건 브리핑</Eyebrow>
        <div className="flex flex-wrap items-start gap-5">
          <Polaroid name={b.damage} caption="피해품" tilt={-4} size={88} />
          <p className="max-w-[60ch] flex-1 leading-relaxed">{b.summary}</p>
        </div>
        <dl className="grid gap-3 text-sm sm:grid-cols-[96px_1fr]">
          <dt className="text-muted">피해</dt>
          <dd>{b.damage}</dd>
          <dt className="text-muted">수사 목표</dt>
          <dd className="font-medium">{b.objective}</dd>
          <dt className="text-muted">확보된 사실</dt>
          <dd>
            <ul className="flex list-disc flex-col gap-1 pl-4">
              {b.public_facts.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          </dd>
        </dl>
      </Panel>

      <section className="flex flex-col gap-3">
        <h2 className="font-title text-xl font-bold">폐관 후 관내에 남아 있던 사람</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {session.suspects.map((s, i) => (
            <Panel key={s.suspect_id} className="flex flex-col items-center gap-3 text-center">
              <div className="rotate-[-2deg] bg-white p-2 pb-6 shadow-md">
                <Portrait role={s.role} index={i} size={112} />
              </div>
              <div>
                <p className="font-title text-lg font-bold">{s.name}</p>
                <p className="text-sm text-muted">{s.role}</p>
              </div>
              <p className="text-left text-sm leading-relaxed text-muted">{s.public_profile}</p>
            </Panel>
          ))}
        </div>
      </section>

      <div>
        <Button onClick={() => goTo('scene')} className="px-6 py-3 text-base">
          현장 조사 시작
        </Button>
      </div>
    </div>
  )
}
