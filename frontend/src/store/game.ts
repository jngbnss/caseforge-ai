import { create } from 'zustand'

import {
  ApiError,
  api,
  type AskResponse,
  type BoardView,
  type DebriefView,
  type DeductionSubmission,
  type EvidenceView,
  type SessionView,
} from '../services/api'

export type Screen = 'briefing' | 'scene' | 'puzzles' | 'interrogation' | 'board' | 'deduction'

export interface ChatMessage {
  role: 'player' | 'npc' | 'system'
  text: string
  emotion?: string
  meta?: Pick<AskResponse, 'revealed_fact_ids' | 'contradiction_detected' | 'trust_delta' | 'turn'>
  pinned?: boolean
}

export interface DevEntry {
  at: string
  action: string
  detail: string
}

const SESSION_KEY = 'caseforge.session'

/** 진행 중인 start 호출. StrictMode의 이중 실행 등으로 세션이 두 번 만들어지지 않게 한다. */
let starting: Promise<void> | null = null

function readStoredSession(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY)
  } catch {
    return null
  }
}

function storeSession(id: string | null) {
  try {
    if (id) localStorage.setItem(SESSION_KEY, id)
    else localStorage.removeItem(SESSION_KEY)
  } catch {
    /* 저장소를 못 쓰면 새로고침 시 새 세션이 된다 */
  }
}

interface GameStore {
  sessionId: string | null
  session: SessionView | null
  board: BoardView | null
  debrief: DebriefView | null
  chats: Record<string, ChatMessage[]>
  screen: Screen
  busy: string | null
  error: string | null
  notice: string | null
  devLog: DevEntry[]

  goTo: (screen: Screen) => void
  clearError: () => void
  clearNotice: () => void
  start: (fresh?: boolean) => Promise<void>
  refresh: () => Promise<void>
  collect: (evidenceId: string) => Promise<EvidenceView | null>
  attemptPuzzle: (puzzleId: string, answer: string | string[]) => Promise<boolean>
  hint: (puzzleId: string) => Promise<void>
  present: (npcId: string, evidenceId: string) => Promise<void>
  ask: (npcId: string, question: string) => Promise<void>
  togglePin: (npcId: string, index: number) => void
  loadBoard: () => Promise<void>
  deduce: (submission: DeductionSubmission) => Promise<void>
}

export const useGame = create<GameStore>((set, get) => {
  /** API 호출을 감싸 로딩 상태, 오류 메시지, 개발자 로그를 처리한다. */
  async function run<T>(label: string, fn: (id: string) => Promise<T>): Promise<T | null> {
    const id = get().sessionId
    if (!id) return null
    set({ busy: label, error: null })
    try {
      const result = await fn(id)
      log(label, result)
      return result
    } catch (err) {
      const message = err instanceof ApiError ? err.message : String(err)
      set({ error: message })
      log(label, { error: message })
      return null
    } finally {
      set({ busy: null })
    }
  }

  function log(action: string, detail: unknown) {
    const entry = {
      at: new Date().toLocaleTimeString('ko-KR'),
      action,
      detail: JSON.stringify(detail),
    }
    set((s) => ({ devLog: [entry, ...s.devLog].slice(0, 50) }))
  }

  /** 저장된 세션을 이어 하거나 새 세션을 만든다. */
  async function startSession(fresh: boolean) {
    set({ busy: '세션 준비', error: null })
    try {
      const stored = fresh ? null : readStoredSession()
      let session: SessionView | null = null
      if (stored) {
        session = await api.getSession(stored).catch(() => null)
      }
      if (!session) {
        session = await api.createSession()
      }
      storeSession(session.session_id)
      set({
        sessionId: session.session_id,
        session,
        board: null,
        debrief: null,
        chats: fresh || session.session_id !== stored ? {} : get().chats,
        screen: session.deduction ? 'deduction' : 'briefing',
      })
      if (session.deduction) {
        set({ debrief: await api.debrief(session.session_id) })
      }
    } catch (err) {
      set({ error: err instanceof ApiError ? err.message : String(err) })
    } finally {
      set({ busy: null })
    }
  }

  return {
    sessionId: null,
    session: null,
    board: null,
    debrief: null,
    chats: {},
    screen: 'briefing',
    busy: null,
    error: null,
    notice: null,
    devLog: [],

    goTo: (screen) => set({ screen }),
    clearError: () => set({ error: null }),
    clearNotice: () => set({ notice: null }),

    start: (fresh = false) => {
      if (starting) return starting
      starting = startSession(fresh).finally(() => {
        starting = null
      })
      return starting
    },

    refresh: async () => {
      const session = await run('세션 조회', (id) => api.getSession(id))
      if (session) set({ session })
    },

    collect: async (evidenceId) => {
      const result = await run('증거 수집', (id) => api.collect(id, evidenceId))
      if (!result) return null
      await get().refresh()
      const opened = result.puzzles.filter((p) => p.available && !p.solved).length
      set({ notice: `증거 확보: ${result.evidence.name}${opened ? ' · 풀 수 있는 퍼즐이 있다' : ''}` })
      return result.evidence
    },

    attemptPuzzle: async (puzzleId, answer) => {
      const result = await run('퍼즐 시도', (id) => api.attemptPuzzle(id, puzzleId, answer))
      if (!result) return false
      await get().refresh()
      if (result.correct) {
        set({ notice: `퍼즐 해결 · ${result.unlocked.map((e) => e.name).join(', ')} 확보` })
      }
      return result.correct
    },

    hint: async (puzzleId) => {
      if (await run('힌트', (id) => api.hint(id, puzzleId))) await get().refresh()
    },

    present: async (npcId, evidenceId) => {
      const result = await run('증거 제시', (id) => api.present(id, npcId, evidenceId))
      if (!result) return
      const name = get().session?.evidence.find((e) => e.evidence_id === evidenceId)?.name
      const system: ChatMessage = {
        role: 'system',
        text:
          result.reaction === 'shaken'
            ? `${name}을(를) 내밀자 표정이 굳는다. 다시 물어보자.`
            : `${name}을(를) 보여 주었다.`,
      }
      set((s) => ({ chats: { ...s.chats, [npcId]: [...(s.chats[npcId] ?? []), system] } }))
      await get().refresh()
    },

    ask: async (npcId, question) => {
      const player: ChatMessage = { role: 'player', text: question }
      set((s) => ({ chats: { ...s.chats, [npcId]: [...(s.chats[npcId] ?? []), player] } }))
      const reply = await run('심문', (id) => api.ask(id, npcId, question))
      if (!reply) return
      const npc: ChatMessage = {
        role: 'npc',
        text: reply.answer,
        emotion: reply.emotion,
        meta: {
          revealed_fact_ids: reply.revealed_fact_ids,
          contradiction_detected: reply.contradiction_detected,
          trust_delta: reply.trust_delta,
          turn: reply.turn,
        },
      }
      set((s) => ({ chats: { ...s.chats, [npcId]: [...(s.chats[npcId] ?? []), npc] } }))
      if (reply.contradiction_detected) {
        set({ notice: '진술이 확보한 증거와 맞지 않는다. 수사 보드에 기록했다.' })
      }
      await get().refresh()
    },

    togglePin: (npcId, index) =>
      set((s) => ({
        chats: {
          ...s.chats,
          [npcId]: (s.chats[npcId] ?? []).map((m, i) =>
            i === index ? { ...m, pinned: !m.pinned } : m,
          ),
        },
      })),

    loadBoard: async () => {
      const board = await run('수사 보드', (id) => api.board(id))
      if (board) set({ board })
    },

    deduce: async (submission) => {
      const result = await run('추리 제출', (id) => api.deduce(id, submission))
      if (!result) return
      const debrief = await run('해설', (id) => api.debrief(id))
      await get().refresh()
      if (debrief) set({ debrief })
    },
  }
})
