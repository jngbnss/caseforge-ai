/** 처음 한 번 보여 주는 수사 안내의 '봤음' 표시. 브라우저에만 저장한다. */

const DONE_KEY = 'caseforge.tutorial.done'

export function tutorialSeen(): boolean {
  try {
    return localStorage.getItem(DONE_KEY) === '1'
  } catch {
    return false
  }
}

export function markSeen() {
  try {
    localStorage.setItem(DONE_KEY, '1')
  } catch {
    /* 저장하지 못하면 다음에도 안내가 뜬다 */
  }
}

