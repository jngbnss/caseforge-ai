/**
 * '지금 할 일' 안내. 플레이어가 이미 받은 공개 상태(조사 수, 퍼즐, 제시한 증거)로만 계산한다.
 * 어느 증거를 누구에게 보여 줄지 같은 정답 정보는 넣지 않는다.
 */
import type { SessionView } from './api'
import type { Screen } from '../store/game'

export interface Objective {
  text: string
  screen: Screen
  action: string
}

export interface Progress {
  label: string
  done: number
  total: number
}

export function objective(session: SessionView, questioned: string[]): Objective {
  const left = session.scene.filter((o) => !o.collected).length
  const openPuzzles = session.puzzles.filter((p) => p.available && !p.solved).length
  const shown = session.npcs.reduce((n, s) => n + s.presented.length, 0)
  const notAsked = session.suspects.filter((s) => !questioned.includes(s.suspect_id))

  if (session.deduction) {
    return { text: '사건이 끝났다. 해설에서 진상을 확인하자.', screen: 'deduction', action: '해설 보기' }
  }
  if (session.evidence.length === 0) {
    return { text: '현장에 가서 반짝이는 조사 지점을 눌러 첫 증거를 찾자.', screen: 'scene', action: '현장으로' }
  }
  if (left > 0) {
    return { text: `현장에 아직 조사하지 않은 곳이 ${left}곳 있다.`, screen: 'scene', action: '현장으로' }
  }
  if (openPuzzles > 0) {
    return { text: `풀 수 있는 퍼즐이 ${openPuzzles}개 있다. 풀면 새 기록을 얻는다.`, screen: 'puzzles', action: '퍼즐로' }
  }
  if (notAsked.length > 0) {
    return {
      text: `${notAsked.map((s) => s.name).join(', ')}에게 그날 밤 어디 있었는지 물어보자.`,
      screen: 'interrogation',
      action: '심문하러',
    }
  }
  if (shown === 0) {
    return {
      text: '진술과 맞지 않는 증거가 있으면 그 사람에게 직접 보여 주자. 반응이 달라진다.',
      screen: 'interrogation',
      action: '심문하러',
    }
  }
  return {
    text: '수사 보드에서 모순을 정리하고, 확신이 서면 최종 추리를 제출하자.',
    screen: 'board',
    action: '보드 보기',
  }
}

export function progress(session: SessionView, questioned: string[]): Progress[] {
  return [
    {
      label: '현장 조사',
      done: session.scene.filter((o) => o.collected).length,
      total: session.scene.length,
    },
    {
      label: '퍼즐',
      done: session.puzzles.filter((p) => p.solved).length,
      total: session.puzzles.length,
    },
    {
      label: '심문',
      done: session.suspects.filter((s) => questioned.includes(s.suspect_id)).length,
      total: session.suspects.length,
    },
  ]
}
