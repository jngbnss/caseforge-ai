import { type ReactNode, useEffect, useRef, useState } from 'react'

import { Polaroid, Portrait, StepIcon } from './art'
import { Button } from './ui'
import { markSeen } from '../services/tutorial'

interface Step {
  title: string
  body: string
  art: ReactNode
}

const STEPS: Step[] = [
  {
    title: '당신은 탐정이다',
    body: '사건 파일이 도착했다. 그날 밤 현장에 남아 있던 용의자 중 누가, 왜, 어떻게 했는지 밝혀내자.',
    art: (
      <div className="flex items-end gap-2">
        <Portrait role="큐레이터" index={0} size={64} />
        <Portrait role="경비" index={1} size={72} />
        <Portrait role="복원" index={2} size={64} />
      </div>
    ),
  },
  {
    title: '① 현장을 뒤진다',
    body: '지도에서 반짝이는 돋보기를 누르면 증거를 줍는다. 주운 증거는 사진으로 사건 노트에 붙는다.',
    art: (
      <div className="flex gap-3">
        <Polaroid name="영수증" caption="증거" tilt={-6} />
        <Polaroid name="출입 로그" caption="증거" tilt={4} />
      </div>
    ),
  },
  {
    title: '② 퍼즐을 푼다',
    body: '잠긴 금고, 뒤섞인 CCTV 화면, 찢어진 메모. 풀면 숨은 기록이 증거로 들어온다.',
    art: (
      <div className="flex gap-3">
        <Polaroid name="CCTV" caption="기록" tilt={-3} />
        <Polaroid name="메모" caption="기록" tilt={5} />
      </div>
    ),
  },
  {
    title: '③ 용의자를 심문한다',
    body: '하고 싶은 말을 자유롭게 입력한다. 처음엔 다들 거짓말을 한다. 말과 맞지 않는 증거를 그 사람에게 내밀면 표정과 말이 바뀐다.',
    art: (
      <div className="flex items-center gap-3">
        <Portrait role="경비" index={1} emotion="calm" size={64} />
        <span className="text-2xl" aria-hidden>
          →
        </span>
        <Portrait role="경비" index={1} emotion="shaken" size={64} />
      </div>
    ),
  },
  {
    title: '④ 보드에 정리하고 지목한다',
    body: '코르크 보드에 증거와 진술을 붙이고 실로 이어 보자. 확신이 서면 범인·동기·수법을 골라 최종 추리를 제출한다.',
    art: (
      <div className="flex items-center gap-2 text-accent">
        <StepIcon step="board" />
        <StepIcon step="deduction" />
      </div>
    ),
  },
]

export function Tutorial({ onClose }: { onClose: () => void }) {
  const [i, setI] = useState(0)
  const dialog = useRef<HTMLDivElement>(null)
  const step = STEPS[i]
  const last = i === STEPS.length - 1

  const close = () => {
    markSeen()
    onClose()
  }

  useEffect(() => {
    dialog.current?.focus()
  }, [i])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4">
      <div
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tutorial-title"
        tabIndex={-1}
        onKeyDown={(e) => e.key === 'Escape' && close()}
        className="paper-sheet flex w-full max-w-md flex-col gap-4 rounded-lg p-6 shadow-2xl outline-none"
      >
        <p className="font-mono text-xs tracking-widest text-muted">
          수사 안내 {i + 1} / {STEPS.length}
        </p>
        <div className="flex min-h-24 items-center justify-center">{step.art}</div>
        <h2 id="tutorial-title" className="text-xl font-bold">
          {step.title}
        </h2>
        <p className="leading-relaxed">{step.body}</p>
        <div className="flex items-center justify-between gap-2">
          <button type="button" onClick={close} className="text-sm text-muted underline">
            건너뛰기
          </button>
          <div className="flex gap-2">
            {i > 0 && (
              <Button variant="ghost" onClick={() => setI(i - 1)}>
                이전
              </Button>
            )}
            <Button onClick={() => (last ? close() : setI(i + 1))}>{last ? '수사 시작' : '다음'}</Button>
          </div>
        </div>
      </div>
    </div>
  )
}
