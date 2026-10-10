import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useGame } from '../src/store/game'

const session = {
  session_id: 'sid-1',
  case_id: 'museum-001',
  briefing: { title: 't', summary: '', damage: '', objective: '', public_facts: [] },
  suspects: [{ suspect_id: 'suspect-02', name: '박도현', role: '경비원', public_profile: '' }],
  scene: [],
  evidence: [],
  puzzles: [],
  npcs: [{ npc_id: 'suspect-02', emotion: 'calm', trust: 0, presented: [] }],
  deduction_options: { motives: [], methods: [] },
  deduction: null,
}

function mockFetch(routes: Record<string, unknown>) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const key = `${init?.method ?? 'GET'} ${url}`
      calls.push(key)
      const body = routes[key]
      if (body === undefined) {
        return new Response(JSON.stringify({ detail: '없음' }), { status: 404 })
      }
      return new Response(JSON.stringify(body), { status: 200 })
    }),
  )
  return calls
}

describe('game store', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', undefined) // 스토어 테스트는 REST 경로를 쓴다
    localStorage.clear()
    useGame.setState({ sessionId: null, session: null, chats: {}, error: null, notice: null, devLog: [] })
  })

  it('저장된 세션이 없으면 한 번만 새로 만들고 ID를 기억한다', async () => {
    const calls = mockFetch({ 'POST /api/sessions': session })
    await Promise.all([useGame.getState().start(), useGame.getState().start()])
    expect(calls.filter((c) => c === 'POST /api/sessions')).toHaveLength(1)
    expect(useGame.getState().session?.session_id).toBe('sid-1')
    expect(localStorage.getItem('caseforge.session')).toBe('sid-1')
  })

  it('심문하면 질문과 답변이 대화에 쌓이고 모순 안내가 뜬다', async () => {
    mockFetch({
      'POST /api/sessions': session,
      'GET /api/sessions/sid-1': session,
      'POST /api/sessions/sid-1/npcs/suspect-02/ask': {
        answer: '계속 보안실에 있었습니다.',
        emotion: 'calm',
        revealed_fact_ids: ['fact-023'],
        contradiction_detected: true,
        trust_delta: 0,
        turn: 1,
      },
    })
    await useGame.getState().start()
    await useGame.getState().ask('suspect-02', '어디 있었어요?')
    const chat = useGame.getState().chats['suspect-02']
    expect(chat.map((m) => m.role)).toEqual(['player', 'npc'])
    expect(chat[1].meta?.contradiction_detected).toBe(true)
    expect(useGame.getState().notice).toContain('수사 보드')
  })

  it('API 오류는 사용자에게 보여 줄 메시지로 남는다', async () => {
    mockFetch({ 'POST /api/sessions': session })
    await useGame.getState().start()
    await useGame.getState().collect('ev-99')
    expect(useGame.getState().error).toBe('없음')
  })
})
