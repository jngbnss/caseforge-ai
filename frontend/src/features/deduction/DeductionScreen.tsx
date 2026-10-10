import { Button, EvidenceTag, Eyebrow, Panel } from '../../components/ui'
import type { DebriefView } from '../../services/api'
import { useGame } from '../../store/game'
import { DeductionForm } from './DeductionForm'

const SCORE_LABEL: Record<string, [string, number]> = {
  culprit: ['범인', 40],
  motive: ['동기', 20],
  method: ['수법', 20],
  evidence: ['증거 연결', 20],
}

function Debrief({ debrief }: { debrief: DebriefView }) {
  const { start } = useGame()
  const r = debrief.result
  const verdict = r.correct_culprit
    ? r.total >= 90
      ? '사건 해결'
      : '범인은 맞혔지만 추리가 부족하다'
    : '범인을 놓쳤다'
  return (
    <div className="flex flex-col gap-5">
      <Panel className="flex flex-col gap-4">
        <Eyebrow>사건 해설</Eyebrow>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className={`text-2xl font-bold ${r.correct_culprit ? 'text-ok' : 'text-bad'}`}>{verdict}</h2>
          <p className="font-mono text-3xl font-semibold">
            {r.total}
            <span className="text-base text-muted"> / 100</span>
          </p>
        </div>
        <div className="flex flex-col gap-2">
          {Object.entries(r.scores).map(([k, v]) => {
            const [label, max] = SCORE_LABEL[k] ?? [k, 20]
            return (
              <div key={k} className="grid grid-cols-[88px_1fr_56px] items-center gap-3 text-sm">
                <span>{label}</span>
                <span className="h-2 overflow-hidden rounded-full bg-soft">
                  <span className="block h-full bg-accent" style={{ width: `${(v / max) * 100}%` }} />
                </span>
                <span className="text-right font-mono">
                  {v}/{max}
                </span>
              </div>
            )
          })}
        </div>
        {r.unsupported_guess && (
          <p className="text-sm text-bad">범인을 맞혔지만 증거를 연결하지 않았다. 근거 없는 추측으로 본다.</p>
        )}
      </Panel>

      <Panel className="flex flex-col gap-3">
        <h2 className="font-bold">진상</h2>
        <p>
          범인은 <b>{debrief.culprit.name}</b>({debrief.culprit.role})이다. 동기는 {debrief.motive}.
        </p>
        <p className="text-sm text-muted">수법: {debrief.method}</p>
        <ol className="flex list-decimal flex-col gap-1 pl-5 text-sm">
          {debrief.method_steps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
      </Panel>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel className="flex flex-col gap-3">
          <h2 className="font-bold">핵심 증거</h2>
          {debrief.key_evidence.map((e) => (
            <p key={e.evidence_id} className="flex items-baseline gap-2 text-sm">
              <span className={e.collected ? 'text-ok' : 'text-bad'}>{e.collected ? '✓' : '✗'}</span>
              <EvidenceTag id={e.evidence_id} />
              {e.name}
              <span className="text-muted">· {e.spot}</span>
            </p>
          ))}
          {debrief.missed_key.length > 0 && (
            <p className="text-sm text-bad">놓친 단서 {debrief.missed_key.length}개: {debrief.missed_key.map((e) => e.name).join(', ')}</p>
          )}
          {debrief.wrong_links.length > 0 && (
            <div className="flex flex-col gap-1 border-t border-line pt-3 text-sm">
              <p className="font-medium text-bad">잘못 연결한 증거</p>
              {debrief.wrong_links.map((e) => (
                <p key={e.evidence_id}>
                  <EvidenceTag id={e.evidence_id} /> {e.name}
                  {e.role === 'red_herring' && <span className="text-muted"> · 수사를 엉뚱한 쪽으로 이끄는 함정 증거</span>}
                </p>
              ))}
            </div>
          )}
        </Panel>

        <Panel className="flex flex-col gap-2">
          <h2 className="font-bold">그날 밤의 시간선</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <tbody>
                {debrief.timeline.map((t, i) => (
                  <tr key={i} className={`border-t border-line ${t.is_crime ? 'text-bad' : ''}`}>
                    <td className="py-1.5 pr-3 font-mono whitespace-nowrap tabular-nums">
                      {t.start}–{t.end}
                    </td>
                    <td className="py-1.5 pr-3 whitespace-nowrap">{t.actor}</td>
                    <td className="py-1.5 pr-3 whitespace-nowrap text-muted">{t.location}</td>
                    <td className="py-1.5">{t.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <div>
        <Button onClick={() => void start(true)}>새 수사 시작</Button>
      </div>
    </div>
  )
}

export function DeductionScreen() {
  const { session, debrief, deduce, busy } = useGame()
  if (!session) return null
  if (session.deduction && debrief) return <Debrief debrief={debrief} />
  return (
    <Panel className="flex flex-col gap-4">
      <Eyebrow>최종 추리</Eyebrow>
      <p className="max-w-[68ch] text-sm text-muted">
        추리는 한 번만 제출할 수 있다. 범인, 동기, 수법을 고르고 그것을 증명하는 증거를 연결한다.
      </p>
      <DeductionForm
        suspects={session.suspects}
        motives={session.deduction_options.motives}
        methods={session.deduction_options.methods}
        evidence={session.evidence}
        disabled={Boolean(busy)}
        onSubmit={(s) => void deduce(s)}
      />
    </Panel>
  )
}
