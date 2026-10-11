/** 수사 보드의 카드 배치와 연결선. 플레이어 개인 메모라 브라우저에만 저장한다. */

export const CARD_W = 180
export const CARD_H = 92

export interface Point {
  x: number
  y: number
}

export interface BoardLayout {
  positions: Record<string, Point>
  links: [string, string][]
}

const key = (sessionId: string) => `caseforge.board.${sessionId}`

export function loadLayout(sessionId: string): BoardLayout {
  try {
    const raw = localStorage.getItem(key(sessionId))
    if (raw) return JSON.parse(raw) as BoardLayout
  } catch {
    /* 저장된 배치를 못 읽으면 기본 배치를 쓴다 */
  }
  return { positions: {}, links: [] }
}

export function saveLayout(sessionId: string, layout: BoardLayout) {
  try {
    localStorage.setItem(key(sessionId), JSON.stringify(layout))
  } catch {
    /* 저장하지 못해도 화면 배치는 유지된다 */
  }
}

/** 카드 종류별로 줄을 나눠 기본 위치를 정한다. */
export function defaultPosition(row: number, index: number): Point {
  return { x: 24 + index * (CARD_W + 20), y: 28 + row * (CARD_H + 36) }
}

export function sameLink(a: [string, string], b: [string, string]) {
  return (a[0] === b[0] && a[1] === b[1]) || (a[0] === b[1] && a[1] === b[0])
}

/** "HH:MM"을 분으로. */
export function minutes(clock: string): number {
  const [h, m] = clock.split(':').map(Number)
  return h * 60 + m
}
