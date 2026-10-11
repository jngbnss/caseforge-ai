import { expect, it } from 'vitest'

import type { SessionView } from '../src/services/api'
import { objective, progress } from '../src/services/objective'

const suspects = [
  { suspect_id: 's1', name: '가', role: '큐레이터', public_profile: '' },
  { suspect_id: 's2', name: '나', role: '경비원', public_profile: '' },
]

function make(over: Partial<SessionView> = {}): SessionView {
  return {
    session_id: 'x',
    case_id: 'c',
    briefing: { title: 't', summary: '', damage: '', objective: '', public_facts: [] },
    suspects,
    scene: [
      { evidence_id: 'e1', spot: 'a', location_name: 'r', collected: true },
      { evidence_id: 'e2', spot: 'b', location_name: 'r', collected: false },
    ],
    evidence: [{ evidence_id: 'e1', name: '자판기 영수증', description: 'd', spot: 'a', location_name: 'r', facts: [] }],
    puzzles: [],
    npcs: suspects.map((s) => ({ npc_id: s.suspect_id, emotion: 'calm', trust: 0, presented: [] })),
    deduction_options: { motives: [], methods: [] },
    deduction: null,
    ...over,
  } as SessionView
}

it('남은 조사 지점이 있으면 현장으로 보낸다', () => {
  expect(objective(make(), [])).toMatchObject({ screen: 'scene', text: expect.stringContaining('1곳') })
})

it('조사가 끝나면 풀 수 있는 퍼즐 → 심문하지 않은 사람 → 증거 제시 순으로 안내한다', () => {
  const scene = make().scene.map((o) => ({ ...o, collected: true }))
  const puzzle = { puzzle_id: 'p', title: 'p', available: true, solved: false, attempts: 0 }
  expect(objective(make({ scene, puzzles: [puzzle] }), []).screen).toBe('puzzles')
  expect(objective(make({ scene }), ['s1']).text).toContain('나')
  expect(objective(make({ scene }), ['s1', 's2']).text).toContain('보여 주자')
})

it('안내 문구에는 증거 이름이나 정답 단서를 넣지 않는다', () => {
  const scene = make().scene.map((o) => ({ ...o, collected: true }))
  const s = make({ scene })
  for (const q of [[], ['s1'], ['s1', 's2']]) {
    const text = objective(s, q).text
    expect(text).not.toContain('영수증')
    expect(text).not.toContain('e1')
  }
})

it('진행도는 조사·퍼즐·심문을 센다', () => {
  expect(progress(make(), ['s2'])).toEqual([
    { label: '현장 조사', done: 1, total: 2 },
    { label: '퍼즐', done: 0, total: 0 },
    { label: '심문', done: 1, total: 2 },
  ])
})
