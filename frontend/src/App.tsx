import { useEffect, useState } from 'react'

import { useSession } from './store/session'

type Health = 'checking' | 'ok' | 'offline'

export default function App() {
  const screen = useSession((s) => s.screen)
  const [health, setHealth] = useState<Health>('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => setHealth(r.ok ? 'ok' : 'offline'))
      .catch(() => setHealth('offline'))
  }, [])

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-4 px-4 py-12">
      <p className="font-mono text-xs uppercase tracking-widest text-slate-500">CaseForge AI</p>
      <h1 className="text-3xl font-bold">사라진 푸른 다이아몬드</h1>
      <p className="text-slate-600">
        게임 화면은 3단계에서 만든다. 현재 화면: <code>{screen}</code>
      </p>
      <p className="text-sm">
        백엔드 연결:{' '}
        <span className={health === 'ok' ? 'text-emerald-600' : 'text-rose-600'}>{health}</span>
      </p>
    </main>
  )
}
