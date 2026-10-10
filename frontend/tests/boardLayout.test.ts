import { expect, it } from 'vitest'

import { defaultPosition, minutes, sameLink } from '../src/features/evidence-board/boardLayout'

it('연결은 방향과 무관하게 같은 것으로 본다', () => {
  expect(sameLink(['a', 'b'], ['b', 'a'])).toBe(true)
  expect(sameLink(['a', 'b'], ['a', 'c'])).toBe(false)
})

it('시각을 분으로 바꾼다', () => {
  expect(minutes('21:12') - minutes('20:30')).toBe(42)
})

it('기본 배치는 줄과 순서로 겹치지 않게 놓인다', () => {
  const a = defaultPosition(0, 0)
  const b = defaultPosition(0, 1)
  const c = defaultPosition(1, 0)
  expect(b.x).toBeGreaterThan(a.x)
  expect(c.y).toBeGreaterThan(a.y)
})
