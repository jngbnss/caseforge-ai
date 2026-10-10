# 구현 계획

> 이 문서는 **설계**와 **단계별 진행 상태**를 함께 관리한다.
> 기획 배경은 [mvp-proposal.md](mvp-proposal.md), 기술 선택 근거는 [decision-log.md](decision-log.md)를 본다.

## 진행 규칙

상태는 `대기` → `진행중` → `완료` 순서로 바뀐다.

1. 작업을 시작하기 전에 해당 행을 `진행중`으로 바꾸고 커밋한 뒤 GitHub에 푸시한다.
2. 작업을 구현하고 테스트를 작성한다.
3. 행에 적힌 **스모크 테스트**를 실제로 실행한다.
4. 문제가 없으면 `완료`로 바꾸고 결과 요약을 "기록" 칸에 적은 뒤 커밋하고 푸시한다.
5. 스모크 테스트가 실패하면 `진행중`을 유지하고 실패 내용을 "기록" 칸에 적는다.

브랜치는 단계마다 하나씩 만든다 (`feat/stage-0N-<요약>`).

---

## 1. 전체 설계

### 1.1 구성도

```
┌──────────── frontend (React + Vite) ────────────┐
│ 브리핑 · 현장 · 퍼즐 · 심문 · 수사 보드 · 추리/해설 │
│ Zustand 스토어 ── services/api.ts (생성된 TS 타입) │
└───────────────┬──────────────────┬──────────────┘
          REST (상태 변경)     WebSocket (심문 스트리밍, 4단계)
┌───────────────┴──────────────────┴──────────────┐
│ backend (FastAPI)                                │
│  api/  ─ 라우터, 응답 스키마 (정답 필드 없음)        │
│  core/ ─ 세션 · 설정 · DB · llm/ · embedding/ 어댑터 │
│  agents/ ─ KnowledgeScope → Retrieve → Generate     │
│            → LeakGuard → UpdateState (심문 그래프)   │
│  evidence/ ─ 증거 수집 · 모순 탐지                   │
│  deduction/ ─ 구조 채점 + LLM 피드백                │
│  cases/ ─ 사건 레지스트리 (load + hash, 캐시)        │
└───────────────┬─────────────────────────────────┘
                │ import
┌───────────────┴──────────────┐   ┌──────────────────┐
│ packages/case-validator       │◀──│ cases/<id>/*.yaml │
│ 스키마 · 조건 DSL · 로더 · 규칙  │   └──────────────────┘
└──────────────────────────────┘
```

### 1.2 디렉터리별 설계

| 경로 | 책임 | 핵심 설계 |
|---|---|---|
| `packages/case-validator/` | Case Bible 스키마, 조건 DSL, YAML 로더, 검증 규칙, CLI | 백엔드에 의존하지 않는 독립 패키지. 모든 모델은 frozen + tuple이라 로드 후 변경할 수 없다. 규칙은 `rules/basic.py`(V01–V07)와 `rules/timeline.py`(T01–T03, U01–U02). |
| `cases/<case_id>/` | 사건 데이터 | `case.yaml`(브리핑·장소·사실·추리 선택지), `timeline.yaml`, `suspects.yaml`(용의자·거짓말·비밀), `evidence.yaml`, `puzzles.yaml`, `solution.yaml`(서버 전용), `dialogues/` |
| `backend/app/cases/` | 사건 레지스트리 | `get_case(id)`가 load + SHA-256을 캐시한다. 세션은 해시를 기록한다. |
| `backend/app/core/` | 설정, 세션 상태, DB, 모델 어댑터 | `llm/ports.py`의 `LLMPort`와 `embedding/ports.py`의 `EmbeddingPort`. 구현은 `mock`, `ollama`, `bge`. `.env`로 선택한다. |
| `backend/app/agents/` | 심문 | `knowledge_scope.py`: NPC별 허용 fact 계산. `leak_guard.py`: fact_id 부분집합 + 카나리 검사. `interrogation.py`: 5개 노드 파이프라인 (4단계에서 LangGraph로 이전). |
| `backend/app/evidence/` | 증거, 모순 | 수집·잠금 해제 판정은 조건 DSL로 처리한다. 모순은 `source: rule \| llm`을 분리해 저장한다. |
| `backend/app/deduction/` | 추리 채점 | 범인 40 · 동기 20 · 수법 20 · 증거 20. red_herring 연결은 감점. LLM은 피드백 문장만 만든다. |
| `backend/app/api/` | REST/WebSocket | 응답은 Pydantic 공개 모델로만 직렬화한다. `solution`, 잠긴 fact, 퍼즐 정답은 공개 모델에 필드가 없다. |
| `frontend/src/services/` | API 클라이언트 | OpenAPI에서 생성한 `types/api.ts`를 쓴다. |
| `frontend/src/store/` | Zustand 스토어 | 서버 상태 캐시 + 수사 보드 배치(로컬). |
| `frontend/src/features/*` | 화면별 기능 | investigation, puzzles, interrogation, evidence-board, deduction |
| `evals/` | 평가 데이터, 러너, 결과 | jsonl 데이터 4종, `evals.run`, `results/` |
| `.github/workflows/ci.yml` | CI | Ruff, pytest, 사건 검증, 프론트 lint·typecheck·build. 모델은 다운로드하지 않는다. 액션은 커밋 SHA로 고정한다. |

### 1.3 심문 요청의 데이터 흐름

1. 클라이언트가 `npc_id`와 질문을 보낸다.
2. **KnowledgeScope**: 서버 세션 상태와 Bible에서 이 NPC가 지금 쓸 수 있는 fact를 계산한다. 다른 NPC의 fact는 인덱스에 없다.
3. **Retrieve**: 스코프 안에서만 검색하고, 결과에 `fact_id`와 출처를 붙인다.
4. **Generate**: 캐릭터 시트 + 근거 fact + `<player_question>` 데이터 블록으로 LLM을 1회 호출하고 Pydantic으로 검증한다.
5. **LeakGuard**: `revealed_fact_ids ⊆ scope`인지, 금지 fact의 카나리 키워드가 없는지 검사한다. 위반하면 1회 재생성하고, 그래도 실패하면 회피 대사로 대체하고 로그를 남긴다.
6. **UpdateState**: 감정·신뢰도·대화 기록·근거를 저장하고, 규칙 기반 모순을 검사한다.

### 1.4 보안 경계

- 정답 데이터는 `solution.yaml`과 `forbidden` fact에만 있으며, 백엔드 밖으로 나가는 경로는 추리 제출 후의 `/debrief`뿐이다.
- npc_id는 경로에서 받지만, 스코프 계산은 서버 상태로만 한다. 사용자 입력은 시스템 프롬프트에 이어 붙이지 않는다.
- `.env`는 커밋하지 않는다. CI 권한은 `contents: read`이다.

---

## 2. 단계별 계획과 상태

### 1단계 — 기반 · 사건 데이터 · 검증기 (P0 P1 P2)

브랜치 `feat/stage-01-foundation` · 프롬프트 [01](build-prompts/01-foundation-case-validator.md)

| ID | 작업 | 산출물 | 스모크 테스트 | 상태 | 기록 |
|---|---|---|---|---|---|
| 1-1 | 저장소 골격 | uv 워크스페이스, FastAPI `/health`, Vite+React+TS+Tailwind+Zustand, `.env.example`, LICENSE, README | `uvicorn` 실행 후 `/health` 200, `npm run build` | 완료 | uvicorn `/health` 200, `/docs` 200. Vite 개발 서버 + `/api` 프록시로 백엔드 응답 확인, build 성공. 로컬 8000 포트를 다른 앱이 쓰고 있어 프록시 대상을 `API_TARGET`으로 바꿀 수 있게 함 |
| 1-2 | Case Bible 스키마 · 조건 DSL · 로더 | `schema.py`, `conditions.py`, `loader.py` | `load_case(museum-001)` 성공, 해시 64자 | 완료 | `load_case(museum-001)` 성공, sha256 `0e0afff3d526…`. 스키마·조건 DSL 테스트 통과 |
| 1-3 | museum-001 사건 데이터 | `cases/museum-001/*.yaml` | 검증기 오류 0, 경고 0 | 완료 | 검증기 오류 0 · 경고 0, 증거 8/8 도달, 퍼즐 3/3 해결 가능 |
| 1-4 | 사건 검증기 | 규칙 V01–V07, T01–T03, U01–U02, CLI | 망가뜨린 사건 16종이 각각 기대 규칙에서 실패 | 완료 | pytest 33개 통과 (망가뜨린 사건 16종이 각각 기대 규칙에서 실패, CLI 종료 코드 확인) |
| 1-5 | CI · 문서 | `ci.yml`, `case-schema.md`, `licenses.md` 등 문서 템플릿 | 로컬에서 CI와 같은 명령 전부 통과 | 완료 | 로컬에서 CI 명령 전부 통과 (Ruff, pytest, 사건 검증, lint, typecheck, build) |

### 2단계 — 게임 엔진 · API · Mock 심문 (P3)

브랜치 `feat/stage-02-game-engine` · 프롬프트 [02](build-prompts/02-game-engine-api.md)

| ID | 작업 | 산출물 | 스모크 테스트 | 상태 | 기록 |
|---|---|---|---|---|---|
| 2-1 | 세션 · 저장소 | 세션 상태 모델, SQLAlchemy + SQLite | 세션 생성 후 재조회 시 상태 유지 | 완료 | SQLite 파일 DB에 세션 생성 후 별도 프로세스에서 재조회 시 수집 증거·해시 유지. 사건 해시가 바뀌면 재조회 거부(CaseChangedError). pytest 6개 통과 |
| 2-2 | REST API | 세션, 증거, 퍼즐, 제시, 질문, 보드, 추리, 해설 | `/docs`에서 각 엔드포인트 호출 | 완료 | uvicorn을 띄우고 curl로 엔드포인트 10종 호출: 정상 200/201, 중복 수집 409, 퍼즐 기록 직접 수집 400, 잠긴 퍼즐 409, 없는 NPC·세션 404, 제출 전 해설 409, 미수집 증거 제출 400, 제출 후 심문 409, 잘못된 case_id 422. 증거 조사 지점 이름(spot) 필드를 스키마에 추가 |
| 2-3 | 모델 어댑터 포트 · Mock | `LLMPort`, `EmbeddingPort`, Mock 구현 | Mock으로 같은 입력 → 같은 출력 | 완료 | 별도 프로세스 2회 실행에서 Mock LLM 응답과 Mock 임베딩 해시 동일(e9c7d629…). 잘못된 JSON 1회 → 재요청 성공, 2회 실패 → 기본값. 대본은 앱 안(app/core/llm/scripts)에 둠: 프론트 개발 때도 Mock으로 플레이해야 해서 |
| 2-4 | KnowledgeScope · LeakGuard | NPC별 스코프, 누설 가드 | 공격 질문 3종 차단 | 완료 | 누설 응답 3종(시스템 프롬프트 노출, 다른 NPC 비밀, 범인 전용 사실) 모두 차단. 모든 증거를 모두에게 제시한 최악 상태에서도 스코프에 금지·타 NPC 사실 없음. pytest 27개 통과 |
| 2-5 | 심문 파이프라인 (Mock) | 5노드 함수 파이프라인, 대본 fixture | 박도현 + ev-02 제시 → 진술 변화 | 완료 | 박도현 심문: 제시 전 거짓말(lie-02) → 출입 로그 제시 시 동요 → 영수증 제시 후 흡연·사물함 자백. 스모크 중 '카드는 어디' 질문이 알리바이로 분류되는 문제 발견해 Mock 의도 순서 수정. 누설 1회 → 재생성, 지속 → 회피 대사. pytest 34개 통과 |
| 2-6 | 모순(규칙) · 추리 채점(구조) | `contradiction.py`, `scoring.py` | 정답 제출 100점, red_herring 연결 감점 | 완료 | 정답 제출 100점, 함정 증거(ev-01) 추가 시 95점, 경비원 지목 20점. 거짓말 진술 후 반박 증거 확보 시 규칙 모순 1회만 기록(source=rule). pytest 40개 통과 |
| 2-7 | E2E · 누출 테스트 | API만으로 사건 클리어, 응답 정답 필드 검사 | `pytest` E2E 통과 | 완료 | API만으로 브리핑 → 증거 5개 → 퍼즐 3개(오답·힌트 포함) → 3명 심문·증거 제시로 진술 변화 → 공격 질문 3건 → 수사 보드 모순 3건 → 정답 제출 100점 → 해설까지 완주. 제출 전 모든 응답에서 금지 사실·퍼즐 정답·증거 역할·정답 키 없음, 선택지가 정답 순서로 나오지 않음. pytest 43개 통과 |
| 2-8 | OpenAPI → TS 타입 | `frontend/src/types/api.ts` 생성 스크립트 | 생성 후 `npm run typecheck` | 완료 | OpenAPI 내보내기 → openapi-typescript로 src/types/api.ts 생성 → typecheck·lint 통과. 두 번 재생성해도 차이 없음(LF 고정). CI에 최신 여부 검사 단계 추가 |

### 3단계 — 프론트엔드 (P4)

브랜치 `feat/stage-03-frontend` · 프롬프트 [03](build-prompts/03-frontend.md)

| ID | 작업 | 산출물 | 스모크 테스트 | 상태 | 기록 |
|---|---|---|---|---|---|
| 3-1 | API 클라이언트 · 스토어 | `services/api.ts`, `store/` | 세션 생성 → 브리핑 데이터 표시 | 완료 | 백엔드+Vite를 dev-all 스크립트로 띄우고 headless Chromium으로 접속: 세션 자동 생성, 제목·브리핑·용의자 3명 표시, 개발자 모드 패널 표시, 콘솔 오류 0. 이 PC의 8000 포트 충돌 때문에 BACKEND_PORT로 포트 지정 가능하게 함 |
| 3-2 | 브리핑 · 현장 조사 | 2D 현장, 증거 수집 | 5곳 클릭 → 증거 5개 | 대기 | |
| 3-3 | 퍼즐 | 순서·코드·조합 입력, 힌트 | 퍼즐 3개 해결 → 기록 3개 해제 | 대기 | |
| 3-4 | 심문 | 채팅, 감정, 증거 제시, 진술 핀 | 증거 제시 후 답변 변화 | 대기 | |
| 3-5 | 수사 보드 | 카드, 연결선, 시간선, 모순 표시 | 수집 증거와 모순이 보드에 표시 | 대기 | |
| 3-6 | 최종 추리 · 해설 | 제출 폼, 점수, 시간선, 놓친 단서 | 정답 제출 → 해설 화면 | 대기 | |
| 3-7 | 개발자 모드 | `?dev=1` 내부 패널 | fact_id · 가드 결과 표시 | 대기 | |
| 3-8 | 프론트 테스트 | Vitest, Playwright E2E, CI 추가 | 브라우저 완주 E2E 통과 | 대기 | |

### 4단계 — 실제 AI · 평가 (P5 P6 P7)

브랜치 `feat/stage-04-ai-evals` · 프롬프트 [04](build-prompts/04-ai-and-evals.md)

| ID | 작업 | 산출물 | 스모크 테스트 | 상태 | 기록 |
|---|---|---|---|---|---|
| 4-1 | Ollama 어댑터 | JSON 스키마 강제, 스트리밍, 계측 | `qwen3:8b`로 질문 1회 → 검증 통과 | 대기 | |
| 4-2 | bge-m3 · NPC별 FAISS | 인덱스 빌드, 스코프 필터 | 다른 NPC fact 검색 불가 | 대기 | |
| 4-3 | LangGraph 심문 그래프 | 5노드 그래프 | Mock과 Ollama 양쪽 동작 | 대기 | |
| 4-4 | WebSocket 스트리밍 | `/ws/interrogation/...`, 프론트 전환 | 화면에 토큰 단위 표시, 가드 교체 | 대기 | |
| 4-5 | LLM 모순 탐지 | `source: llm` 판정, 비동기 처리 | 보드에 rule/llm 구분 표시 | 대기 | |
| 4-6 | LLM 추리 피드백 | 근거 없는 주장 · 논리 비약 표시 | 해설 화면 피드백 문장 | 대기 | |
| 4-7 | 평가 데이터 | jsonl 4종 (120 / 60 / 40 / 40건) | 스키마 검사 통과 | 대기 | |
| 4-8 | 평가 러너 | `evals.run`, 결과 JSON | mock과 ollama로 각각 실행 | 대기 | |
| 4-9 | 실험 기록 · 문서 | `experiments.md` 개선 사이클 1회, 모델·라이선스 문서 | 완료 조건 1–10 점검표 | 대기 | |

### 5단계 — 사건 생성기 (P8, 선택)

| ID | 작업 | 산출물 | 스모크 테스트 | 상태 | 기록 |
|---|---|---|---|---|---|
| 5-1 | Case Generator | 생성 → 검증 → 재시도 → museum-001 대체 | 생성 10회 중 유효 사건 수 측정 | 대기 | |
