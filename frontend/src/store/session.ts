import { create } from 'zustand'

type Screen = 'briefing' | 'investigation' | 'interrogation' | 'board' | 'deduction' | 'debrief'

interface SessionState {
  screen: Screen
  goTo: (screen: Screen) => void
}

export const useSession = create<SessionState>((set) => ({
  screen: 'briefing',
  goTo: (screen) => set({ screen }),
}))
