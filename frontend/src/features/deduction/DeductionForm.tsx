import { useState } from 'react'

import { Button, Empty, EvidenceTag } from '../../components/ui'
import type { DeductionSubmission, EvidenceView, SuspectView } from '../../services/api'

interface Option {
  id: string
  text: string
}

export interface DeductionFormProps {
  suspects: SuspectView[]
  motives: Option[]
  methods: Option[]
  evidence: EvidenceView[]
  disabled?: boolean
  onSubmit: (submission: DeductionSubmission) => void
}

/** 범인 · 동기 · 수법 · 핵심 증거 · 자유 서술. 제출 전 한 번 더 확인한다. */
export function DeductionForm({ suspects, motives, methods, evidence, disabled, onSubmit }: DeductionFormProps) {
  const [culprit, setCulprit] = useState('')
  const [motive, setMotive] = useState('')
  const [method, setMethod] = useState('')
  const [chosen, setChosen] = useState<string[]>([])
  const [narrative, setNarrative] = useState('')
  const [confirming, setConfirming] = useState(false)

  const missing = [!culprit && '범인', !motive && '동기', !method && '수법'].filter(Boolean)
  const toggle = (id: string) =>
    setChosen((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c, id]))

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault()
        if (missing.length) return
        if (!confirming) return setConfirming(true)
        onSubmit({
          culprit_id: culprit,
          motive_id: motive,
          method_id: method,
          evidence_ids: chosen,
          narrative: narrative.trim(),
        })
      }}
    >
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-bold">범인</legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {suspects.map((s) => (
            <label
              key={s.suspect_id}
              className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 ${
                culprit === s.suspect_id ? 'border-bad ring-1 ring-bad' : 'border-line'
              }`}
            >
              <input
                type="radio"
                name="culprit"
                value={s.suspect_id}
                checked={culprit === s.suspect_id}
                onChange={() => setCulprit(s.suspect_id)}
                className="accent-[var(--bad)]"
              />
              <span>
                <span className="block font-bold">{s.name}</span>
                <span className="text-xs text-muted">{s.role}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-2">
          <span className="font-bold">동기</span>
          <select
            value={motive}
            onChange={(e) => setMotive(e.target.value)}
            className="rounded-md border border-line bg-sheet px-2 py-2 text-sm"
          >
            <option value="">동기를 고른다</option>
            {motives.map((o) => (
              <option key={o.id} value={o.id}>
                {o.text}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-2">
          <span className="font-bold">수법</span>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="rounded-md border border-line bg-sheet px-2 py-2 text-sm"
          >
            <option value="">수법을 고른다</option>
            {methods.map((o) => (
              <option key={o.id} value={o.id}>
                {o.text}
              </option>
            ))}
          </select>
        </label>
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 font-bold">핵심 증거</legend>
        <p className="text-sm text-muted">추리를 뒷받침하는 증거만 고른다. 엉뚱한 증거를 연결하면 감점된다.</p>
        {evidence.length === 0 && <Empty>수집한 증거가 없다.</Empty>}
        <div className="grid gap-2 sm:grid-cols-2">
          {evidence.map((e) => (
            <label key={e.evidence_id} className="flex cursor-pointer items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={chosen.includes(e.evidence_id)}
                onChange={() => toggle(e.evidence_id)}
                className="mt-1"
              />
              <span>
                <EvidenceTag id={e.evidence_id} /> {e.name}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <label className="flex flex-col gap-2">
        <span className="font-bold">추리 과정</span>
        <textarea
          rows={4}
          maxLength={2000}
          value={narrative}
          onChange={(e) => setNarrative(e.target.value)}
          placeholder="누가, 왜, 어떻게 했는지 증거와 함께 적는다."
          className="rounded-md border border-line bg-sheet px-3 py-2 text-sm"
        />
      </label>

      <div className="flex flex-col gap-2">
        {missing.length > 0 && (
          <p className="text-sm text-muted">{missing.join(', ')}을(를) 골라야 제출할 수 있다.</p>
        )}
        {confirming && !missing.length && (
          <p role="alert" className="text-sm text-bad">
            제출하면 수사가 끝나고 더는 심문할 수 없다. 이대로 제출할까?
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={Boolean(missing.length) || disabled}>
            {confirming ? '확정하고 제출' : '추리 제출'}
          </Button>
          {confirming && (
            <Button variant="ghost" onClick={() => setConfirming(false)}>
              더 수사하기
            </Button>
          )}
        </div>
      </div>
    </form>
  )
}
