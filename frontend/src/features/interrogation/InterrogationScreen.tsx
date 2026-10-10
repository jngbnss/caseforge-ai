import { useEffect, useRef, useState } from 'react'

import { Button, EmotionBadge, Empty, EvidenceTag, Eyebrow, Panel } from '../../components/ui'
import { isDevMode } from '../../services/dev'
import { useGame } from '../../store/game'

const SUGGESTIONS = [
  '어젯밤 21시 이후에 어디 있었어요?',
  '경비 카드에 대해 아는 게 있어요?',
  'CCTV 녹화가 끊긴 이유를 알아요?',
  '동료들은 어떤 사람이에요?',
  '푸른 별 진열장은 언제 마지막으로 봤어요?',
]

function TrustMeter({ value }: { value: number }) {
  return (
    <span className="flex items-center gap-1" aria-label={`신뢰도 ${value}/3`}>
      {[1, 2, 3].map((i) => (
        <span key={i} className={`h-1.5 w-4 rounded-full ${i <= value ? 'bg-accent' : 'bg-line'}`} />
      ))}
    </span>
  )
}

export function InterrogationScreen() {
  const { session, chats, ask, present, togglePin, busy } = useGame()
  const [npcId, setNpcId] = useState(session?.suspects[0]?.suspect_id ?? '')
  const [question, setQuestion] = useState('')
  const [evidenceId, setEvidenceId] = useState('')
  const logRef = useRef<HTMLDivElement>(null)
  const dev = isDevMode()
  const messages = chats[npcId] ?? []

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight })
  }, [messages.length, npcId])

  if (!session) return null
  const suspect = session.suspects.find((s) => s.suspect_id === npcId)
  const state = session.npcs.find((n) => n.npc_id === npcId)
  const presentable = session.evidence.filter((e) => !state?.presented.includes(e.evidence_id))
  const finished = Boolean(session.deduction)
  const locked = Boolean(busy) || finished
  const pinned = Object.entries(chats).flatMap(([id, list]) =>
    list.filter((m) => m.pinned).map((m) => ({ npc: id, text: m.text })),
  )

  const send = (text: string) => {
    const q = text.trim()
    if (!q || locked) return
    setQuestion('')
    void ask(npcId, q)
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_280px]">
      <div className="flex min-w-0 flex-col gap-4">
        <Eyebrow>용의자 심문</Eyebrow>
        <div className="grid gap-2 sm:grid-cols-3" role="tablist" aria-label="용의자">
          {session.suspects.map((s) => {
            const st = session.npcs.find((n) => n.npc_id === s.suspect_id)
            const active = s.suspect_id === npcId
            return (
              <button
                key={s.suspect_id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setNpcId(s.suspect_id)}
                className={`flex items-center gap-3 rounded-lg border bg-sheet p-3 text-left ${
                  active ? 'border-accent ring-1 ring-accent' : 'border-line hover:border-accent'
                }`}
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-soft font-bold text-accent">
                  {s.name.slice(0, 1)}
                </span>
                <span className="flex min-w-0 flex-col gap-1">
                  <span className="font-bold">{s.name}</span>
                  <span className="flex flex-wrap items-center gap-2 text-xs text-muted">
                    {s.role}
                    {st && <EmotionBadge emotion={st.emotion} />}
                  </span>
                </span>
              </button>
            )
          })}
        </div>

        <Panel className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <p>
              <span className="font-bold">{suspect?.name}</span>
              <span className="text-muted"> · {suspect?.role}</span>
            </p>
            {state && (
              <span className="flex items-center gap-2 text-xs text-muted">
                신뢰 <TrustMeter value={state.trust} />
              </span>
            )}
          </div>

          <div
            ref={logRef}
            className="flex h-[22rem] flex-col gap-3 overflow-y-auto rounded-md bg-paper p-3"
            aria-live="polite"
          >
            {messages.length === 0 && (
              <Empty>{suspect?.name}에게 자유롭게 질문하자. 증거를 내밀면 반응이 달라질 수 있다.</Empty>
            )}
            {messages.map((m, i) =>
              m.role === 'system' ? (
                <p key={i} className="self-center text-xs text-muted">
                  {m.text}
                </p>
              ) : (
                <div
                  key={i}
                  className={`flex max-w-[85%] flex-col gap-1 ${m.role === 'player' ? 'self-end items-end' : 'self-start'}`}
                >
                  <div
                    className={`rounded-xl px-3 py-2 text-sm leading-relaxed ${
                      m.role === 'player'
                        ? 'bg-accent text-accent-ink'
                        : `border bg-sheet ${m.meta?.contradiction_detected ? 'border-bad' : 'border-line'}`
                    }`}
                  >
                    {m.text}
                  </div>
                  {m.role === 'npc' && (
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                      {m.emotion && <EmotionBadge emotion={m.emotion} />}
                      {m.meta?.contradiction_detected && <span className="text-bad">증거와 모순</span>}
                      <button
                        type="button"
                        onClick={() => togglePin(npcId, i)}
                        className={m.pinned ? 'text-tag' : 'hover:text-ink'}
                        aria-pressed={Boolean(m.pinned)}
                      >
                        {m.pinned ? '★ 저장됨' : '☆ 진술 저장'}
                      </button>
                      {dev && m.meta && (
                        <span className="font-mono">
                          turn {m.meta.turn} · revealed [{m.meta.revealed_fact_ids.join(', ')}] · trust{' '}
                          {m.meta.trust_delta >= 0 ? '+' : ''}
                          {m.meta.trust_delta}
                        </span>
                      )}
                      {dev && m.meta?.debug && (
                        <span className="w-full font-mono">
                          근거 [{m.meta.debug.grounding_fact_ids.join(', ')}] · 거짓말 [
                          {m.meta.debug.used_lie_ids.join(', ')}] · LLM {m.meta.debug.llm_calls}회 · 가드{' '}
                          {m.meta.debug.guard_violations.length
                            ? `차단 ${m.meta.debug.guard_violations.join(', ')}${m.meta.debug.fallback ? ' → 회피 대사' : ' → 재생성'}`
                            : '통과'}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ),
            )}
            {busy === '심문' && <p className="self-start text-sm text-muted">{suspect?.name}이(가) 생각하는 중…</p>}
          </div>

          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => send(s)}
                disabled={locked}
                className="rounded-full border border-line px-3 py-1 text-xs text-muted hover:border-accent hover:text-ink disabled:opacity-40"
              >
                {s}
              </button>
            ))}
          </div>

          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              send(question)
            }}
          >
            <label htmlFor="question" className="sr-only">
              질문
            </label>
            <input
              id="question"
              value={question}
              maxLength={300}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={`${suspect?.name}에게 질문`}
              autoComplete="off"
              disabled={finished}
              className="min-w-0 flex-1 rounded-md border border-line bg-sheet px-3 py-2 text-sm"
            />
            <Button type="submit" disabled={!question.trim() || locked}>
              질문
            </Button>
          </form>

          <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
            <label htmlFor="present" className="text-sm text-muted">
              증거 제시
            </label>
            <select
              id="present"
              value={evidenceId}
              onChange={(e) => setEvidenceId(e.target.value)}
              disabled={locked || presentable.length === 0}
              className="min-w-0 flex-1 rounded-md border border-line bg-sheet px-2 py-2 text-sm"
            >
              <option value="">{presentable.length ? '증거를 고른다' : '보여 줄 증거가 없다'}</option>
              {presentable.map((e) => (
                <option key={e.evidence_id} value={e.evidence_id}>
                  {e.evidence_id} · {e.name}
                </option>
              ))}
            </select>
            <Button
              variant="ghost"
              disabled={!evidenceId || locked}
              onClick={() => {
                void present(npcId, evidenceId)
                setEvidenceId('')
              }}
            >
              보여 주기
            </Button>
          </div>
        </Panel>
      </div>

      <aside className="flex flex-col gap-4">
        <Panel className="flex flex-col gap-2">
          <h2 className="font-bold">이 인물에게 보여 준 증거</h2>
          {state?.presented.length ? (
            state.presented.map((id) => (
              <p key={id} className="flex items-baseline gap-2 text-sm">
                <EvidenceTag id={id} />
                {session.evidence.find((e) => e.evidence_id === id)?.name}
              </p>
            ))
          ) : (
            <Empty>아직 없다.</Empty>
          )}
        </Panel>
        <Panel className="flex flex-col gap-2">
          <h2 className="font-bold">저장한 진술</h2>
          {pinned.length === 0 && <Empty>중요한 답변 아래 ☆를 눌러 저장한다.</Empty>}
          {pinned.map((p, i) => (
            <blockquote key={i} className="border-l-2 border-tag pl-2 text-sm">
              <p className="text-xs text-muted">
                {session.suspects.find((s) => s.suspect_id === p.npc)?.name}
              </p>
              {p.text}
            </blockquote>
          ))}
        </Panel>
      </aside>
    </div>
  )
}
