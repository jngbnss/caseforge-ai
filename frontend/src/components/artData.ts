/** 그림 고르기 규칙. 이름·직업 같은 공개 정보만 본다. */

export interface Look {
  skin: string
  hair: string
  coat: string
  style: 'bun' | 'short' | 'messy'
  extra: 'glasses' | 'cap' | 'loupe' | 'none'
}

const LOOKS: Look[] = [
  { skin: '#f1d3b8', hair: '#3b2a20', coat: '#5b4a7a', style: 'bun', extra: 'glasses' },
  { skin: '#e2b896', hair: '#1f1a17', coat: '#2f4a68', style: 'short', extra: 'cap' },
  { skin: '#edc9a6', hair: '#5a3b26', coat: '#4f6b4a', style: 'messy', extra: 'loupe' },
]

/** 직업 단어로 소품을 고르고, 없으면 순서대로 돌려 쓴다. */
export function lookFor(role: string, index: number): Look {
  if (/큐레이터|관장|학예/.test(role)) return LOOKS[0]
  if (/경비|보안|경찰/.test(role)) return LOOKS[1]
  if (/복원|보존|연구/.test(role)) return LOOKS[2]
  return LOOKS[index % LOOKS.length]
}

export type IconKind =
  | 'receipt'
  | 'log'
  | 'mold'
  | 'glove'
  | 'diamond'
  | 'camera'
  | 'letter'
  | 'memo'
  | 'search'

/** 증거 이름의 단어로 아이콘을 고른다. 모르는 증거는 돋보기. */
export function iconFor(name: string): IconKind {
  if (/영수증|꽁초/.test(name)) return 'receipt'
  if (/CCTV|카메라|영상/.test(name)) return 'camera'
  if (/로그|기록|단말/.test(name)) return 'log'
  if (/몰드|틀|실리콘/.test(name)) return 'mold'
  if (/장갑|섬유|가루/.test(name)) return 'glove'
  if (/다이아|보석|별/.test(name)) return 'diamond'
  if (/독촉|편지|우편|계약/.test(name)) return 'letter'
  if (/메모|쪽지/.test(name)) return 'memo'
  return 'search'
}

