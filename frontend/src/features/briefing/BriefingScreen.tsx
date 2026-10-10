import { Button, Eyebrow, Panel } from '../../components/ui'
import { useGame } from '../../store/game'

export function BriefingScreen() {
  const { session, goTo } = useGame()
  if (!session) return null
  const b = session.briefing
  return (
    <div className="flex flex-col gap-5">
      <Panel className="flex flex-col gap-4">
        <Eyebrow>사건 브리핑</Eyebrow>
        <p className="max-w-[68ch] leading-relaxed">{b.summary}</p>
        <dl className="grid gap-3 text-sm sm:grid-cols-[96px_1fr]">
          <dt className="text-muted">피해</dt>
          <dd>{b.damage}</dd>
          <dt className="text-muted">수사 목표</dt>
          <dd>{b.objective}</dd>
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
        <h2 className="text-lg font-bold">폐관 후 관내에 남아 있던 사람</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {session.suspects.map((s) => (
            <Panel key={s.suspect_id} className="flex flex-col gap-2">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-soft text-lg font-bold text-accent">
                  {s.name.slice(0, 1)}
                </span>
                <div>
                  <p className="font-bold">{s.name}</p>
                  <p className="text-sm text-muted">{s.role}</p>
                </div>
              </div>
              <p className="text-sm leading-relaxed text-muted">{s.public_profile}</p>
            </Panel>
          ))}
        </div>
      </section>

      <div>
        <Button onClick={() => goTo('scene')}>현장 조사 시작</Button>
      </div>
    </div>
  )
}
