import { create } from 'zustand'

export type BackendStatus = 'unknown' | 'ok' | 'offline'

interface SessionState {
  backend: BackendStatus
  checkBackend: () => Promise<void>
}

export const useSessionStore = create<SessionState>((set) => ({
  backend: 'unknown',
  checkBackend: async () => {
    try {
      const res = await fetch('/api/health')
      set({ backend: res.ok ? 'ok' : 'offline' })
    } catch {
      set({ backend: 'offline' })
    }
  },
}))
