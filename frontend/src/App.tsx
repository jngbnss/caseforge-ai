import { useEffect, useState } from 'react'

import { StepIcon } from './components/art'
import { DevPanel } from './components/DevPanel'
import { Tutorial } from './components/Tutorial'
import { BoardScreen } from './features/evidence-board/BoardScreen'
import { BriefingScreen } from './features/briefing/BriefingScreen'
import { DeductionScreen } from './features/deduction/DeductionScreen'
import { InterrogationScreen } from './features/interrogation/InterrogationScreen'
import { SceneScreen } from './features/investigation/SceneScreen'
import { PuzzleScreen } from './features/puzzles/PuzzleScreen'
import { isDevMode } from './services/dev'
import { objective, progress } from './services/objective'
import { tutorialSeen } from './services/tutorial'
import { type Screen, useGame } from './store/game'

const SCREENS: { key: Screen; label: string }[] = [
  { key: 'briefing', label: '브리핑' },
  { key: 'scene', label: '현장 조사' },
  { key: 'puzzles', label: '퍼즐' },
  { key: 'interrogation', label: '심문' },
  { key: 'board', label: '수사 보드' },
  { key: 'deduction', label: '최종 추리' },
]

function Banner() {
  const { error, notice, clearError, clearNotice } = useGame()
  useEffect(() => {
    if (!notice) return
    const t = setTimeout(clearNotice, 4000)
    return () => clearTimeout(t)
  }, [notice, clearNotice])
  if (error) {
    return (
      <div role="alert" className="flex items-start justify-between gap-4 rounded-md bg-bad/10 px-4 py-3 text-sm text-bad">
        <span>{error}</span>
        <button type="button" onClick={clearError} className="shrink-0 underline">
          닫기
        </button>
      </div>
    )
  }
  if (notice) {
    return (
      <div role="status" className="rounded-md bg-tag-soft px-4 py-3 text-sm text-tag">
        {notice}
      </div>
    )
  }
  return null
}

function ObjectiveBar() {
  const { session, chats, goTo, screen } = useGame()
  if (!session) return null
  const questioned = Object.entries(chats)
    .filter(([, list]) => list.some((m) => m.role === 'player'))
    .map(([id]) => id)
  const goal = objective(session, questioned)
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-3 rounded-md border border-dashed border-tag bg-tag-soft/60 px-4 py-3">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <span className="font-hand text-2xl leading-none text-accent" aria-hidden>
          ✎
        </span>
        <p className="min-w-0 text-sm">
          <span className="mr-2 font-bold text-accent">지금 할 일</span>
          <span data-testid="objective">{goal.text}</span>
        </p>
        {goal.screen !== screen && (
          <button
            type="button"
            onClick={() => goTo(goal.screen)}
            className="shrink-0 rounded-full border border-accent px-3 py-1 text-xs font-medium text-accent hover:bg-accent hover:text-accent-ink"
          >
            {goal.action} →
          </button>
        )}
      </div>
      <ul className="flex flex-wrap gap-4" aria-label="진행도">
        {progress(session, questioned).map((p) => (
          <li key={p.label} className="flex items-center gap-2 text-xs text-muted">
            {p.label}
            <span className="flex gap-0.5" aria-label={`${p.label} ${p.done}/${p.total}`}>
              {Array.from({ length: p.total }, (_, i) => (
                <span
                  key={i}
                  className={`h-2.5 w-2.5 rounded-sm border ${i < p.done ? 'border-accent bg-accent' : 'border-line bg-sheet'}`}
                />
              ))}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function App() {
  const { session, screen, goTo, start, busy } = useGame()
  const dev = isDevMode()
  const [help, setHelp] = useState(() => !tutorialSeen())

  useEffect(() => {
    void start()
  }, [start])

  const finished = Boolean(session?.deduction)
  const screens = {
    briefing: <BriefingScreen />,
    scene: <SceneScreen />,
    puzzles: <PuzzleScreen />,
    interrogation: <InterrogationScreen />,
    board: <BoardScreen />,
    deduction: <DeductionScreen />,
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-6">
      <header className="mb-4 flex flex-wrap items-end justify-between gap-3 text-desk-ink">
        <div>
          <p className="font-mono text-xs tracking-widest uppercase opacity-70">
            CaseForge AI · 사건 파일 {session?.case_id ?? '…'}
          </p>
          <h1 className="font-title text-3xl font-extrabold">{session?.briefing.title ?? '사건 파일을 여는 중'}</h1>
        </div>
        <div className="flex items-center gap-3 text-sm">
          {busy && (
            <span aria-live="polite" className="opacity-80">
              {busy}…
            </span>
          )}
          <button
            type="button"
            onClick={() => setHelp(true)}
            className="rounded-md border border-desk-ink/50 px-3 py-2 hover:bg-desk-ink/10"
          >
            도움말
          </button>
          <button
            type="button"
            onClick={() => void start(true)}
            disabled={Boolean(busy)}
            className="rounded-md border border-desk-ink/50 px-3 py-2 hover:bg-desk-ink/10 disabled:opacity-40"
          >
            새 수사 시작
          </button>
        </div>
      </header>

      <nav aria-label="수사 단계" className="flex flex-wrap items-end gap-1 px-2">
        {SCREENS.map((s, i) => {
          const active = screen === s.key
          return (
            <button
              key={s.key}
              type="button"
              aria-current={active ? 'page' : undefined}
              onClick={() => goTo(s.key)}
              disabled={!session}
              className={`flex items-center gap-1.5 rounded-t-lg px-3 text-sm font-medium transition-all ${
                active
                  ? 'bg-paper py-2.5 text-ink'
                  : 'bg-[color-mix(in_srgb,var(--paper)_70%,var(--desk))] py-2 text-muted hover:py-2.5 hover:text-ink'
              }`}
            >
              <span className="font-mono text-xs opacity-60">{i + 1}</span>
              <StepIcon step={s.key} />
              {s.key === 'deduction' && finished ? '사건 해설' : s.label}
            </button>
          )
        })}
      </nav>

      <div className="folder flex flex-col gap-4 rounded-lg rounded-tl-none p-4 sm:p-5">
        {session && <ObjectiveBar />}
        <Banner />

        <div className={dev ? 'grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]' : ''}>
          <main key={session?.session_id} className="min-w-0">
            {session ? screens[screen] : null}
          </main>
          {dev && <DevPanel />}
        </div>
      </div>

      {help && <Tutorial onClose={() => setHelp(false)} />}
    </div>
  )
}
