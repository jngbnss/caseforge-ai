import { useEffect, useRef, useState } from 'react'

import { Polaroid, Portrait } from '../../components/art'
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
        <span key={i} className={`h-2 w-5 rounded-full ${i <= value ? 'bg-ok' : 'bg-desk-ink/25'}`} />
      ))}
    </span>
  )
}

export function InterrogationScreen() {
  const { session, chats, ask, present, togglePin, busy } = useGame()
  const [npcId, setNpcId] = useState(session?.suspects[0]?.suspect_id ?? '')
  const [question, setQuestion] = useState('')
  const logRef = useRef<HTMLDivElement>(null)
  const dev = isDevMode()
  const messages = chats[npcId] ?? []

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight })
  }, [messages.length, npcId])

  if (!session) return null
  const index = session.suspects.findIndex((s) => s.suspect_id === npcId)
  const suspect = session.suspects[index]
  const state = session.npcs.find((n) => n.npc_id === npcId)
  const emotion = state?.emotion ?? 'calm'
  const finished = Boolean(session.deduction)
  const locked = Boolean(busy) || finished
  const pinned = Object.entries(chats).flatMap(([id, list]) =>
    list.filter((m) => m.pinned).map((m) => ({ npc: id, text: m.text })),
  )
  const shaken = emotion === 'shaken' || emotion === 'nervous'

  const send = (text: string) => {
    const q = text.trim()
    if (!q || locked) return
    setQuestion('')
    void ask(npcId, q)
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_260px]">
      <div className="flex min-w-0 flex-col gap-4">
        <Eyebrow>용의자 심문</Eyebrow>
        <div className="grid gap-2 sm:grid-cols-3" role="tablist" aria-label="용의자">
          {session.suspects.map((s, i) => {
            const st = session.npcs.find((n) => n.npc_id === s.suspect_id)
            const active = s.suspect_id === npcId
            return (
              <button
                key={s.suspect_id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setNpcId(s.suspect_id)}
                className={`flex items-center gap-3 rounded-lg border bg-sheet p-2 text-left transition-transform ${
                  active ? 'border-accent ring-2 ring-accent' : 'border-line hover:-translate-y-0.5 hover:border-accent'
                }`}
              >
                <Portrait role={s.role} index={i} emotion={st?.emotion} size={48} />
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

        {/* 심문실: 왼쪽 인물, 오른쪽 대화 */}
        <section className="grid overflow-hidden rounded-lg border border-line shadow-md md:grid-cols-[220px_minmax(0,1fr)]">
          <div className="relative flex flex-col items-center justify-center gap-3 bg-[radial-gradient(circle_at_50%_0%,#5b4a36_0%,#2a2018_70%)] px-4 pt-8 pb-4 text-desk-ink">
            {/* 천장 조명 */}
            <span className="absolute top-0 left-1/2 h-4 w-16 -translate-x-1/2 rounded-b-full bg-[#f6d27a] shadow-[0_0_40px_12px_rgb(246_210_122/0.35)]" aria-hidden />
            <div key={`${npcId}-${emotion}`} className={shaken ? 'shake' : 'pop-in'}>
              <Portrait role={suspect?.role ?? ''} index={index} emotion={emotion} size={168} className="rounded-xl shadow-lg" />
            </div>
            <div className="text-center">
              <p className="font-title text-lg font-bold">{suspect?.name}</p>
              <p className="text-xs opacity-75">{suspect?.role}</p>
            </div>
            {state && (
              <div className="flex items-center gap-3 text-xs">
                <EmotionBadge emotion={emotion} />
                <span className="flex items-center gap-1.5">
                  신뢰 <TrustMeter value={state.trust} />
                </span>
              </div>
            )}
          </div>

          <div className="flex min-w-0 flex-col gap-3 bg-sheet p-4">
            <div
              ref={logRef}
              className="flex h-[20rem] flex-col gap-3 overflow-y-auto rounded-md bg-paper p-3"
              aria-live="polite"
            >
              {messages.length === 0 && (
                <Empty>{suspect?.name}에게 자유롭게 질문하자. 아래 증거 사진을 누르면 그 증거를 내민다.</Empty>
              )}
              {messages.map((m, i) =>
                m.streaming && !m.text ? null : m.role === 'system' ? (
                  <p key={i} className="self-center rounded-full bg-tag-soft px-3 py-1 text-xs text-tag">
                    {m.text}
                  </p>
                ) : (
                  <div
                    key={i}
                    className={`pop-in flex max-w-[88%] flex-col gap-1 ${m.role === 'player' ? 'self-end items-end' : 'self-start'}`}
                  >
                    <div
                      className={`rounded-xl px-3 py-2 text-sm leading-relaxed ${
                        m.role === 'player'
                          ? 'rounded-br-sm bg-accent text-accent-ink'
                          : `rounded-bl-sm border-2 bg-sheet ${m.meta?.contradiction_detected ? 'border-bad' : 'border-line'}`
                      }`}
                    >
                      {m.text}
                    </div>
                    {m.role === 'npc' && (
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                        {m.emotion && <EmotionBadge emotion={m.emotion} />}
                        {m.meta?.contradiction_detected && (
                          <span className="font-bold text-bad">⚠ 증거와 모순</span>
                        )}
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
              {busy === '심문' && !messages[messages.length - 1]?.text && (
                <p className="self-start text-sm text-muted">{suspect?.name}이(가) 생각하는 중…</p>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => send(s)}
                  disabled={locked}
                  className="rounded-full border border-line bg-sheet px-3 py-1 text-xs text-muted hover:border-accent hover:text-ink disabled:opacity-40"
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
          </div>
        </section>

        <Panel className="flex flex-col gap-3">
          <h2 className="font-title font-bold">
            증거 내밀기 <span className="text-sm font-normal text-muted">— 사진을 누르면 {suspect?.name}에게 보여 준다</span>
          </h2>
          {session.evidence.length === 0 && <Empty>아직 보여 줄 증거가 없다. 현장을 먼저 조사하자.</Empty>}
          <ul className="flex flex-wrap gap-4" aria-label="증거 제시">
            {session.evidence.map((e, i) => {
              const shown = state?.presented.includes(e.evidence_id) ?? false
              return (
                <li key={e.evidence_id}>
                  <button
                    type="button"
                    disabled={locked || shown}
                    onClick={() => void present(npcId, e.evidence_id)}
                    aria-label={`${e.name} 보여 주기${shown ? ' (보여 줌)' : ''}`}
                    title={e.description}
                    className="relative flex flex-col items-center gap-1 transition-transform hover:-translate-y-1 disabled:opacity-50 disabled:hover:translate-y-0"
                  >
                    <Polaroid name={e.name} tilt={i % 2 ? 3 : -3} size={56} />
                    <span className="max-w-24 truncate text-xs">{e.name}</span>
                    {shown && (
                      <span className="stamp absolute top-4 rounded bg-sheet/80 px-1 text-[10px] font-bold">
                        제시함
                      </span>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
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
        <Panel className="flex flex-col gap-2 border-tag">
          <h2 className="font-hand text-2xl leading-none">저장한 진술</h2>
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
