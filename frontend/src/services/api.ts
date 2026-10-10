import type { components } from '../types/api'

type S = components['schemas']

export type SessionView = S['SessionView']
export type EvidenceView = S['EvidenceView']
export type PuzzleView = S['PuzzleView']
export type NpcStateView = S['NpcStateView']
export type SuspectView = S['SuspectView']
export type SceneObjectView = S['SceneObjectView']
export type AskResponse = S['AskResponse']
export type BoardView = S['BoardView']
export type CollectResponse = S['CollectResponse']
export type PuzzleAttemptResponse = S['PuzzleAttemptResponse']
export type HintResponse = S['HintResponse']
export type PresentResponse = S['PresentResponse']
export type DeductionSubmission = S['DeductionSubmission']
export type DeductionResultView = S['DeductionResultView']
export type DebriefView = S['DebriefView']

const BASE = '/api'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function describe(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return '입력값이 올바르지 않다.'
  return '알 수 없는 오류가 났다.'
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(BASE + path, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, '서버에 연결할 수 없다. 백엔드가 실행 중인지 확인하라.')
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(response.status, describe(data?.detail))
  }
  return data as T
}

const s = (id: string) => `/sessions/${encodeURIComponent(id)}`

/**
 * 심문 답변을 WebSocket으로 받는다. 글자 조각마다 onDelta를 부르고, 최종 응답으로 끝난다.
 * WebSocket을 쓸 수 없으면 null을 돌려준다 (호출한 쪽이 REST로 다시 묻는다).
 */
export function askStream(
  id: string,
  npcId: string,
  question: string,
  onDelta: (text: string) => void,
): Promise<AskResponse | null> {
  if (typeof WebSocket !== 'function') return Promise.resolve(null)
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const url = `${scheme}://${window.location.host}${BASE}/ws/interrogation/${encodeURIComponent(id)}/${npcId}`
  return new Promise((resolve, reject) => {
    let opened = false
    let settled = false
    const ws = new WebSocket(url)
    const finish = (fn: () => void) => {
      if (settled) return
      settled = true
      fn()
      ws.close()
    }
    ws.onopen = () => {
      opened = true
      ws.send(JSON.stringify({ question }))
    }
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data as string)
      if (msg.type === 'delta') onDelta(msg.text)
      else if (msg.type === 'final') {
        const { type: _type, ...rest } = msg
        void _type
        finish(() => resolve(rest as AskResponse))
      } else if (msg.type === 'error') finish(() => reject(new ApiError(400, msg.detail)))
    }
    ws.onerror = () => finish(() => (opened ? reject(new ApiError(0, '연결이 끊겼다.')) : resolve(null)))
    ws.onclose = () => finish(() => (opened ? reject(new ApiError(0, '연결이 끊겼다.')) : resolve(null)))
  })
}

export const api = {
  createSession: (caseId = 'museum-001') =>
    request<SessionView>('POST', '/sessions', { case_id: caseId }),
  getSession: (id: string) => request<SessionView>('GET', s(id)),
  collect: (id: string, evidenceId: string) =>
    request<CollectResponse>('POST', `${s(id)}/evidence/${evidenceId}/collect`),
  attemptPuzzle: (id: string, puzzleId: string, answer: string | string[]) =>
    request<PuzzleAttemptResponse>('POST', `${s(id)}/puzzles/${puzzleId}/attempt`, { answer }),
  hint: (id: string, puzzleId: string) =>
    request<HintResponse>('GET', `${s(id)}/puzzles/${puzzleId}/hint`),
  present: (id: string, npcId: string, evidenceId: string) =>
    request<PresentResponse>('POST', `${s(id)}/npcs/${npcId}/present`, {
      evidence_id: evidenceId,
    }),
  ask: (id: string, npcId: string, question: string) =>
    request<AskResponse>('POST', `${s(id)}/npcs/${npcId}/ask`, { question }),
  board: (id: string) => request<BoardView>('GET', `${s(id)}/board`),
  deduce: (id: string, submission: DeductionSubmission) =>
    request<DeductionResultView>('POST', `${s(id)}/deduction`, submission),
  debrief: (id: string) => request<DebriefView>('GET', `${s(id)}/debrief`),
}
