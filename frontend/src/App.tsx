import { useEffect } from 'react'

import { DevPanel } from './components/DevPanel'
import { Button } from './components/ui'
import { BoardScreen } from './features/evidence-board/BoardScreen'
import { BriefingScreen } from './features/briefing/BriefingScreen'
import { DeductionScreen } from './features/deduction/DeductionScreen'
import { InterrogationScreen } from './features/interrogation/InterrogationScreen'
import { SceneScreen } from './features/investigation/SceneScreen'
import { PuzzleScreen } from './features/puzzles/PuzzleScreen'
import { isDevMode } from './services/dev'
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

export default function App() {
  const { session, screen, goTo, start, busy } = useGame()
  const dev = isDevMode()

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
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-5 px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-xs tracking-widest text-muted uppercase">
            CaseForge AI · {session?.case_id ?? '…'}
          </p>
          <h1 className="text-2xl font-bold">{session?.briefing.title ?? '사건 파일을 여는 중'}</h1>
        </div>
        <div className="flex items-center gap-3 text-sm text-muted">
          {busy && <span aria-live="polite">{busy}…</span>}
          <Button variant="ghost" onClick={() => void start(true)} disabled={Boolean(busy)}>
            새 수사 시작
          </Button>
        </div>
      </header>

      <nav aria-label="수사 단계" className="flex flex-wrap gap-1 border-b border-line">
        {SCREENS.map((s, i) => (
          <button
            key={s.key}
            type="button"
            aria-current={screen === s.key ? 'page' : undefined}
            onClick={() => goTo(s.key)}
            disabled={!session}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
              screen === s.key ? 'border-accent text-ink' : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <span className="mr-1 font-mono text-xs opacity-60">{i + 1}</span>
            {s.key === 'deduction' && finished ? '사건 해설' : s.label}
          </button>
        ))}
      </nav>

      <Banner />

      <div className={dev ? 'grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]' : ''}>
        <main key={session?.session_id} className="min-w-0">
          {session ? screens[screen] : null}
        </main>
        {dev && <DevPanel />}
      </div>
    </div>
  )
}
