import { useState } from 'react'

import { Button, EvidenceTag, Eyebrow, Panel } from '../../components/ui'
import type { PuzzleView } from '../../services/api'
import { useGame } from '../../store/game'
import { CodeInput, SequenceInput } from './inputs'

function PuzzleCard({ puzzle }: { puzzle: PuzzleView }) {
  const { attemptPuzzle, hint, busy, session } = useGame()
  const [wrong, setWrong] = useState(false)
  const finished = Boolean(session?.deduction)

  const submit = async (answer: string | string[]) => {
    const ok = await attemptPuzzle(puzzle.puzzle_id, answer)
    setWrong(!ok)
  }

  if (!puzzle.available) {
    return (
      <Panel className="flex flex-col gap-1 opacity-70">
        <h2 className="font-bold">{puzzle.title}</h2>
        <p className="text-sm text-muted">아직 단서가 부족하다. 현장을 더 조사하자.</p>
      </Panel>
    )
  }

  return (
    <Panel className={`flex flex-col gap-4 ${puzzle.solved ? 'border-ok' : ''}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-bold">{puzzle.title}</h2>
        <span className={`text-xs ${puzzle.solved ? 'text-ok' : 'text-muted'}`}>
          {puzzle.solved ? '해결' : `시도 ${puzzle.attempts}회`}
        </span>
      </div>
      <p className="max-w-[68ch] text-sm leading-relaxed">{puzzle.prompt}</p>

      {puzzle.solved ? (
        <p className="text-sm text-ok">풀었다. 새로 얻은 기록은 사건 노트에 있다.</p>
      ) : puzzle.input_type === 'code' ? (
        <CodeInput
          length={puzzle.code_length ?? 4}
          disabled={Boolean(busy) || finished}
          onSubmit={(code) => void submit(code)}
        />
      ) : (
        <SequenceInput
          options={puzzle.options ?? []}
          disabled={Boolean(busy) || finished}
          onSubmit={(order) => void submit(order)}
        />
      )}

      {wrong && !puzzle.solved && (
        <p role="status" className="text-sm text-bad">
          맞지 않는다. 단서를 다시 보자.
        </p>
      )}

      {!puzzle.solved && (
        <div className="flex flex-col gap-2 border-t border-line pt-3">
          {(puzzle.hints ?? []).map((h, i) => (
            <p key={h} className="text-sm text-muted">
              힌트 {i + 1}. {h}
            </p>
          ))}
          <div>
            <Button
              variant="ghost"
              onClick={() => void hint(puzzle.puzzle_id)}
              disabled={puzzle.hints_remaining === 0 || Boolean(busy)}
            >
              {puzzle.hints_remaining === 0 ? '힌트 없음' : `힌트 보기 (${puzzle.hints_remaining}개 남음)`}
            </Button>
          </div>
        </div>
      )}
    </Panel>
  )
}

export function PuzzleScreen() {
  const { session, goTo } = useGame()
  if (!session) return null
  const solved = session.puzzles.filter((p) => p.solved).length
  const records = session.evidence.filter((e) => e.evidence_id.startsWith('rec-'))
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="flex min-w-0 flex-col gap-4">
        <div className="flex items-baseline justify-between">
          <Eyebrow>퍼즐</Eyebrow>
          <p className="font-mono text-sm text-muted">
            해결 {solved} / {session.puzzles.length}
          </p>
        </div>
        {session.puzzles.map((p) => (
          <PuzzleCard key={p.puzzle_id} puzzle={p} />
        ))}
      </div>
      <aside className="flex flex-col gap-4">
        <Panel className="flex flex-col gap-3">
          <h2 className="font-bold">퍼즐로 얻은 기록</h2>
          {records.length === 0 && <p className="text-sm text-muted">아직 없다.</p>}
          {records.map((e) => (
            <div key={e.evidence_id} className="flex flex-col gap-1">
              <p className="flex items-baseline gap-2">
                <EvidenceTag id={e.evidence_id} />
                <span className="font-medium">{e.name}</span>
              </p>
              <p className="text-sm leading-relaxed text-muted">{e.description}</p>
            </div>
          ))}
          {records.length > 0 && (
            <Button variant="ghost" onClick={() => goTo('interrogation')}>
              이 기록으로 심문하기
            </Button>
          )}
        </Panel>
      </aside>
    </div>
  )
}
