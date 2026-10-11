# Decision Log

형식: `D-번호 | 날짜 | 결정 | 대안 | 근거 | 상태`

| ID | 날짜 | 결정 | 대안 | 근거 | 상태 |
|---|---|---|---|---|---|
| D-001 | 2026-10-11 | 상태관리: **Zustand** | React Context | 화면 6개가 세션 상태를 공유하므로 리렌더 제어와 보일러플레이트 면에서 유리 | 제안 |
| D-002 | 2026-10-11 | 스타일: **Tailwind CSS** | CSS Modules | 7인 병렬 작업에서 디자인 토큰 일관성과 속도 확보 | 제안 |
| D-003 | 2026-10-11 | 현장 표현: **2D 포인트앤클릭** | Three.js 방 1개 | MVP 핵심은 AI 수사이며 3D는 위험만 늘림 | 제안 |
| D-004 | 2026-10-11 | 로컬 LLM 런타임: **Ollama** (기본), llama.cpp는 비교 실험용 | llama.cpp 단독 | 설치 용이, JSON 스키마 `format` 지원. 성능 비교는 OSS 실험으로 기록 | 제안 |
| D-005 | 2026-10-11 | 벡터 검색: **FAISS, NPC별 독립 인덱스** | Chroma + 메타데이터 필터 | 비밀 분리를 필터가 아닌 물리적 분리로 보장. 데이터가 작아 FAISS로 충분 | 제안 |
| D-006 | 2026-10-11 | 임베딩: **BAAI/bge-m3** | bge-small-en 등 | 한국어 성능 | 제안 |
| D-007 | 2026-10-11 | 사건 데이터 포맷: **YAML** | JSON | 사람이 작성/리뷰하기 쉬움. 로드 후 Pydantic 검증 | 제안 |
| D-008 | 2026-10-11 | 통신: **상태 변경은 REST, 심문 스트리밍은 WebSocket** | 전부 WebSocket | 테스트 용이성, 권위 상태의 명확성 | 제안 |
| D-009 | 2026-10-11 | 개발 순서: **LLM 없이 완주 가능한 게임 → LLM 연결** | AI 우선 | 결정론적 테스트 기반 확보, 위험 분리 | 제안 |
| D-010 | 2026-10-11 | 첫 사건: **수작업 작성** (생성기는 P8 선택) | 생성기 우선 | 검증기와 평가 기준선이 먼저 필요 | 제안 |
| D-011 | 2026-10-11 | 심문 1턴당 **LLM 호출 1회** 원칙 | 다단계 LLM 체인 | 로컬 8B 지연. 검색·가드·규칙 모순은 비-LLM | 제안 |
| D-012 | 2026-10-11 | 누설 판정: **규칙(카나리·fact_id) 1차, LLM judge 보조** | LLM judge 단독 | "LLM 검증 결과만 신뢰하지 않는다" 원칙 | 제안 |
| D-013 | 2026-10-11 | 파이썬 패키지 관리: **uv**, `case-validator`는 `packages/` 아래 독립 패키지 | pip + requirements.txt | 빠른 설치와 잠금 파일, 독립 OSS 배포 준비 | 제안 |
| D-014 | 2026-10-11 | API 타입 공유: **OpenAPI → `openapi-typescript`**, E2E는 **Playwright** | 수동 TS 타입, Cypress | 백엔드와 프론트의 계약 불일치 방지 | 제안 |
| D-015 | 2026-10-11 | 구현을 **프롬프트 4개**로 묶어 진행 (`docs/build-prompts/`) | 9단계 개별 진행 | 사용자 요청. 단계 사이 검증은 각 프롬프트의 완료 기준으로 대신 | 제안 |
| D-016 | 2026-10-11 | Condition DSL에 **`always` 원자** 추가 (항상 발견 가능한 증거용) | `{all: []}`로 표현 | YAML 가독성. `all: []`도 계속 참으로 평가된다 | 적용 |
| D-017 | 2026-10-11 | 스키마 확장: `Fact.implicates/leak_forbidden/canary_keywords`, `Suspect.capabilities`, `Evidence.attests`, `Puzzle.items/constraints`, `Solution.crime/required_means/motive_keywords`, `Briefing.motive_options` | 제안서 2절 필드만 사용 | U01(기회·수단·체인), T02, V04를 사람 판단 없이 데이터로 판정하려면 필요. 누설 가드(P5)의 카나리 원천 | 적용 |
| D-018 | 2026-10-11 | U01 판정 정의: 기회 = 진실 시간선 + 이동 시간, 수단 = `required_means ⊆ capabilities`, 체인 = 그 용의자를 가리키는 truth/record fact 전부 증명 가능. U02 = 도달 가능 증거에서 key 하나를 빼면 체인이 깨짐 | 증언(testimony) 포함, key 집합 안에서만 제거 | 증언·거짓말은 체인 근거가 될 수 없다. 대체 증명 경로가 있으면 key가 아니므로 전체 증거에서 뺀다 | 적용 |
| D-019 | 2026-10-11 | 시간 겹침: T01/U01은 **반열린 구간**(순간 = 30초), T02는 **닫힌 구간** | 한 가지 규칙 | 연속된 사건(21:18 종료/21:18 시작)은 동시 존재가 아니지만, 21:07 영수증은 21:04–21:07 사건과 일치해야 한다 | 적용 |
| D-020 | 2026-10-11 | Bible 해시 = `model_dump` **정규화 JSON(키 정렬) SHA-256** | 원본 YAML 바이트 해시 | 주석·서식·파일 분할과 무관하게 내용이 같으면 같은 해시 | 적용 |
| D-021 | 2026-10-11 | 망가뜨린 fixture는 **museum-001 + `patch.yaml` 오버레이**, 테스트는 실패 규칙 집합이 `expect`와 정확히 같은지 확인 | 사건 디렉터리 전체 복사 | 12개 × 7파일 중복 제거, 각 fixture가 무엇을 망가뜨리는지 한눈에 보임. museum-001 변경이 자동 반영 | 적용 |
| D-022 | 2026-10-11 | 루트 **uv 가상 워크스페이스**(backend, case-validator), CI 외부 액션은 **커밋 SHA 고정** | 패키지별 독립 venv, 태그 고정 | 루트에서 `uv run case-validator` 실행, 잠금 파일 하나. SHA 고정이 태그 이동 공격에 안전 | 적용 |
| D-023 | 2026-10-11 | 프론트 버전: **Vite 8, TypeScript 6, Tailwind v4**(`@tailwindcss/vite`, CSS `@theme` 설정) | Tailwind v3 + `tailwind.config.js` | 2026-10 기준 create-vite 기본 템플릿과 최신 안정판 | 적용 |
| D-024 | 2026-10-11 | 백엔드 테스트 HTTP 클라이언트 **httpx2** | httpx | Starlette TestClient가 httpx 사용을 deprecated 경고로 알림 | 적용 |
| D-025 | 2026-10-11 | 스키마 추가: `Briefing.method_options`, `Solution.method_id`, `Lie.contradiction_type`, `Evidence/Puzzle.hotspot`, `Dialogue.reaction_lines` | 수법을 자유 서술로만 받기, 화면 좌표를 프론트에 하드코딩 | 수법 채점을 구조 비교로 하려면 선택지가 필요. 좌표·반응 대사는 사건 데이터이므로 Bible에 둔다 (정답 정보 아님) | 적용 |
| D-026 | 2026-10-11 | 증거 제시 반응은 **규칙 + 대본 대사**(LLM 미사용), 신뢰도는 거짓말을 무너뜨리는 증거 제시 +1, 심문 1턴 `trust_delta`는 −1..+1로 클램프 (초기값 1, 상한 5) | 제시 반응도 LLM 생성 | 비밀 공개 조건(`trust_gte`)이 플레이어 문장으로 조작되지 않게 한다 | 적용 |
| D-027 | 2026-10-11 | 누설 가드 카나리 예외: 스코프 안 fact의 카나리, 그 NPC에게 제시한 증거 문구에 있는 단어는 허용 | 모든 금지 카나리 일괄 차단 | 플레이어가 보여 준 메모의 "사물함"을 되읽는 것은 누설이 아니다. 과차단은 회피 대사 남발로 이어진다 | 적용 |
| D-028 | 2026-10-11 | 퍼즐 조각은 세션마다 섞어서 내려주고 정답 순서와 같으면 회전한다. 메모 조각 ID를 `mp-a..d`로 바꿈 | 정렬된 ID | ID나 순서로 정답이 새지 않게 한다 | 적용 |
| D-029 | 2026-10-11 | `openapi-typescript`의 `typescript ^5` peer를 npm `overrides`로 TS 6에 연결, CI에서 생성물 최신 여부를 `git diff`로 검사 | TS 5로 내리기 | 생성기는 타입 출력에만 TS API를 쓰고, 생성 결과는 TS 6 `tsc`로 검증된다 | 적용 |
| D-030 | 2026-10-11 | Mock 대본 경로는 프롬프트대로 `backend/tests/fixtures/mock_npc.yaml`이며 `MOCK_SCRIPT_PATH`로 바꿀 수 있다 | `app/` 아래 | Mock 모드는 CI·E2E·오프라인 데모 전용 | 적용 |
