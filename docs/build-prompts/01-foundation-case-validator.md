# 프롬프트 1/4 — 기반 · 사건 데이터 · 검증기 (P0 + P1 + P2)

아래를 그대로 Claude Code에 붙여 넣는다.

---

`docs/build-prompts/00-common.md`, `docs/mvp-proposal.md`, `docs/decision-log.md`를 먼저 읽고 그 규칙을 따라라.
이번 단계는 **LLM을 전혀 쓰지 않는다.** 저장소 골격, Case Bible 스키마, 첫 사건 데이터, 사건 검증기를 만든다.

## 1. 저장소 골격 (P0)
- 제안서 10절의 디렉터리 구조를 만든다: `frontend/`, `backend/`, `cases/`, `evals/`, `docs/`, `.github/workflows/`.
- `backend/`: uv 프로젝트, FastAPI 앱 진입점 `app/main.py`, `GET /health`, Ruff 설정, pytest 설정.
- `frontend/`: Vite React TS 템플릿, Tailwind, Zustand 설치, 빈 첫 화면. `npm run typecheck`, `npm run build` 스크립트를 둔다.
- `packages/case-validator/`: 독립 파이썬 패키지 (자체 `pyproject.toml`). 백엔드가 이 패키지를 의존성으로 쓴다.
- 루트: `README.md` (실행 방법), `.env.example`, `.gitignore`, `LICENSE` (MIT), `docs/` 빈 문서 템플릿(`architecture.md`, `case-schema.md`, `model-selection.md`, `experiments.md`, `licenses.md`).
- `.github/workflows/ci.yml`: 백엔드 Ruff + pytest, case-validator pytest, 프론트 typecheck + build, `case-validator check cases/museum-001`. 공통 규칙의 보안 조건을 지킨다.

## 2. Case Bible 스키마 (P1)
- 제안서 2절의 모델을 `packages/case-validator/src/case_validator/schema.py`에 Pydantic v2로 구현한다: `Fact`, `Lie`, `Secret`, `Evidence`, `Puzzle`, `TimelineEvent`, `Solution`, `Suspect`, `Location`, `Briefing`, `CaseBible`(frozen).
- `Condition` DSL: `all`, `any`, `evidence_collected`, `evidence_presented`(+npc), `puzzle_solved`, `trust_gte`(+npc). `evaluate(condition, state) -> bool` 순수 함수로 만든다.
- 로더: `load_case(path) -> CaseBible`가 `case.yaml`, `timeline.yaml`, `suspects.yaml`, `evidence.yaml`, `puzzles.yaml`, `solution.yaml`, `dialogues/*.yaml`을 합쳐 검증하고, 결과와 함께 SHA-256 해시를 반환한다.
- `docs/case-schema.md`에 필드 설명을 쓴다.

## 3. museum-001 사건 데이터 (P1)
- 제안서 5절 내용을 그대로 YAML로 옮긴다: 용의자 3명, 물리적 증거 `ev-01`~`ev-05`, 퍼즐 보상 `rec-01`~`rec-03`, 퍼즐 `pz-01`~`pz-03`, 시간선, Lie 3개, Secret, Solution.
- 퍼즐 정답: `pz-01` CCTV 4프레임 순서, `pz-02` 금고 `0784` (1907 → 07, 1984 → 84), `pz-03` 메모 "21:10 휴게실 — 사물함 3번".
- 모든 fact에 `fact_id`, `known_by`, `source`를 넣는다. 범인 전용 fact(21:12 출입, 21:14 바꿔치기)는 `known_by: [suspect-03]`이고 누설 금지 표시를 단다.
- 장소 인접 정보와 최소 이동 시간(분)을 넣는다 (T03 검사용).
- `dialogues/suspect-0N.yaml`: 캐릭터 말투, 성격, 대표 대사 5개, 회피 대사 3개.

## 4. 사건 검증기 (P2)
- 제안서 4절 규칙을 구현한다: V01–V07, T01–T03, U01–U02. L01(LLM 비평)은 인터페이스만 두고 구현하지 않는다.
- 시간선 그래프는 NetworkX로 만든다 (인물·장소·시간·증거 노드).
- V04 퍼즐 유일해: 순서형은 순열을 전수 검사하고, 코드형은 퍼즐에 정의된 단서 제약으로 후보를 전수 검사한다.
- U01: 각 용의자에 대해 기회(범행 시간에 현장 접근 가능), 수단, 증거 체인을 평가해 셋을 모두 만족하는 사람이 culprit 하나뿐인지 검사한다.
- 출력: `ValidationReport{errors, warnings, metrics}` + CLI `case-validator check <dir>` (오류가 있으면 종료 코드 1).
- 테스트: museum-001은 통과해야 한다. `tests/fixtures/broken-*`에 규칙마다 일부러 망가뜨린 사건을 두고 정확히 해당 규칙이 실패하는지 확인한다 (예: 한 인물이 21:10에 두 장소, 발견 불가능한 key evidence, 정답이 두 개인 퍼즐, 범행 가능한 용의자가 두 명).

## 완료 기준 (전부 실행해서 보고)
- `cd backend && uv run ruff check . && uv run pytest`
- `cd packages/case-validator && uv run pytest`
- `uv run case-validator check cases/museum-001` → 오류 0
- `cd frontend && npm run typecheck && npm run build`
- 망가뜨린 fixture마다 기대한 규칙 ID가 리포트에 나온다.

끝나면 무엇을 만들었는지, 테스트 결과, 남은 TODO, 결정 로그에 추가한 항목을 보고하고 멈춰라.
