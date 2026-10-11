import { useEffect } from 'react'
import { useSessionStore } from './store/session'

const statusLabel = {
  unknown: '서버 확인 중',
  ok: '서버 연결됨',
  offline: '서버 오프라인',
} as const

export default function App() {
  const backend = useSessionStore((s) => s.backend)
  const checkBackend = useSessionStore((s) => s.checkBackend)

  useEffect(() => {
    void checkBackend()
  }, [checkBackend])

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
      <p className="text-sm tracking-[0.2em] text-evidence">CASEFORGE AI</p>
      <h1 className="mt-4 text-5xl font-bold leading-tight">사라진 푸른 다이아몬드</h1>
      <p className="mt-6 text-lg leading-relaxed">
        사건 브리핑 화면은 다음 단계(P4)에서 구현됩니다.
      </p>
      <p className="mt-10 text-sm" data-testid="backend-status">
        {statusLabel[backend]}
      </p>
    </main>
  )
}
