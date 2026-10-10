/** 현장 평면도 배치. 사건 데이터의 장소 이름을 도면 위 방 위치로 옮긴다. 정답 정보는 없다. */

export interface Room {
  name: string
  x: number
  y: number
  w: number
  h: number
  outdoor?: boolean
}

export const VIEWBOX = { w: 800, h: 460 }

export const MUSEUM_ROOMS: Room[] = [
  { name: '전시실', x: 260, y: 110, w: 280, h: 230 },
  { name: '보안실', x: 120, y: 110, w: 130, h: 105 },
  { name: '큐레이터 사무실', x: 120, y: 225, w: 130, h: 115 },
  { name: '직원 휴게실', x: 550, y: 110, w: 130, h: 105 },
  { name: '복원실', x: 550, y: 225, w: 130, h: 115 },
  { name: '옥외 흡연 구역', x: 610, y: 8, w: 180, h: 92, outdoor: true },
  { name: '직원 주차장', x: 20, y: 360, w: 230, h: 80, outdoor: true },
]

/** 방 안에 조사 지점을 고르게 놓는다. */
export function spotPosition(room: Room, index: number, count: number) {
  const step = room.w / (count + 1)
  return { cx: room.x + step * (index + 1), cy: room.y + room.h * 0.58 }
}
