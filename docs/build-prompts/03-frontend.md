# 프롬프트 3/4 — 프론트엔드 6개 화면 (P4)

아래를 그대로 Claude Code에 붙여 넣는다. 프롬프트 2가 끝난 상태여야 한다.

---

`docs/build-prompts/00-common.md`, `docs/mvp-proposal.md` 6절(프론트/백엔드 책임)을 읽고 따라라.
목표: **브라우저에서 museum-001을 처음부터 끝까지 플레이할 수 있다.** 백엔드는 프롬프트 2의 API(Mock NPC)를 그대로 쓴다.
UX 참고: 팀 데모 페이지 https://claude.ai/artifact/WqCuQGE65jHeXZtDstth73 의 "플레이 데모" 흐름 (단, 오른쪽 "시스템 내부" 패널은 개발자 모드에서만 보인다).

## 구조
- `frontend/src/services/api.ts`: 생성된 `types/api.ts`를 쓰는 타입 안전 클라이언트. 심문은 지금은 REST로 호출하고, 응답 스트리밍 자리를 인터페이스로 열어 둔다 (WebSocket은 프롬프트 4).
- `frontend/src/store/`: Zustand 스토어 (세션, 수집 증거, NPC별 대화, 보드 상태). 수사 보드의 카드 배치만 로컬 상태로 둔다.
- 기능 폴더: `features/investigation`, `features/puzzles`, `features/interrogation`, `features/evidence-board`, `features/deduction` (+ 브리핑·해설)

## 화면
1. **브리핑**: 사건 제목, 피해 상황, 수사 목표, 용의자 카드 3장
2. **현장 조사**: 전시실 2D 일러스트(SVG 또는 CSS 도형) 위 클릭 영역 5곳 → 증거 수집 애니메이션, 사건 노트
3. **퍼즐**: 순서 맞추기(드래그 또는 클릭), 4자리 코드 입력, 메모 조각 조합. 힌트 버튼. 판정은 서버 응답만 믿는다.
4. **심문**: NPC 초상(이니셜 아바타 가능), 감정 표시, 자유 질문 입력, 대화 기록, 증거 제시 드롭다운, 중요 진술 저장(핀)
5. **수사 보드**: 인물·증거·진술 카드, 드래그 배치, 카드 사이 연결선, 시간선 막대, 서버가 준 모순 표시
6. **최종 추리 → 해설**: 범인/동기/수법 선택, 핵심 증거 체크, 자유 서술 → 점수 막대, 전체 시간선, 놓친 단서, 잘못 연결한 증거

## 요구사항
- 데스크톱 우선, 768px 이상에서 깨지지 않는다.
- 로딩/오류 상태를 모든 API 호출에 표시한다.
- 개발자 모드 토글(`?dev=1`): 응답의 `revealed_fact_ids`, 감정, 가드 차단 여부, 모순 판정 출처를 패널로 보여준다.
- 프론트 코드와 번들에 사건 정답 데이터가 없다. API가 주는 데이터만 렌더링한다.

## 테스트
- Vitest + Testing Library: 스토어 리듀서, 퍼즐 입력 컴포넌트, 추리 폼 검증
- Playwright E2E 1개: 백엔드를 Mock 모드로 띄우고 브리핑 → 해설까지 클릭으로 완주. CI에 추가한다 (Chromium만).

## 완료 기준
- `npm run typecheck && npm run test && npm run build`
- Playwright E2E 통과
- 로컬에서 `backend` + `frontend` 동시 실행 방법을 README에 쓴다 (한 줄 명령 권장: `make dev` 또는 `npm run dev:all`)
- 각 화면 스크린샷을 `docs/screenshots/`에 저장한다

보고 후 멈춰라.
