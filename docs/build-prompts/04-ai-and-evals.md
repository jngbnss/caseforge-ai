# 프롬프트 4/4 — 실제 AI 연결 · 모순/추리 AI · 평가 (P5 + P6 + P7)

아래를 그대로 Claude Code에 붙여 넣는다. 프롬프트 3이 끝난 상태여야 한다.
로컬에 Ollama가 설치되어 있고 `ollama pull qwen3:8b`를 받아 두면 실제 측정까지 진행할 수 있다. 없으면 Mock으로 구조만 완성하고, 측정은 보고서에 "미실행"으로 적는다.

---

`docs/build-prompts/00-common.md`, `docs/mvp-proposal.md` 3·7·8·10절을 읽고 따라라.
목표: Mock 대신 로컬 LLM으로 자유 심문이 동작하고, 누설률과 모순율을 평가 스크립트로 재측정할 수 있다.

## 1. 어댑터
- `backend/app/core/llm/ollama.py`: `/api/chat`, `format`에 Pydantic JSON 스키마 전달, thinking 비활성(`think: false`), 타임아웃, 토큰·지연 계측. `stream()`도 구현한다.
- `backend/app/core/embedding/bge.py`: `BAAI/bge-m3` (sentence-transformers). 선택 의존성 그룹(`uv sync --extra ai`)으로 분리해 CI가 설치하지 않게 한다.
- `.env`의 `LLM_BACKEND`, `LLM_MODEL`, `EMBEDDING_BACKEND`로 선택한다. 기본값은 `mock`이다.
- llama.cpp 어댑터는 인터페이스 파일만 두고 TODO로 남긴다 (비교 실험은 이후).

## 2. NPC별 검색
- 세션 시작 시 NPC마다 FAISS 인덱스를 따로 만든다. 인덱스에는 `known_by`에 그 NPC가 있는 fact만 넣는다. 검색 결과는 스코프(조건 충족)로 한 번 더 거르고 `fact_id`와 출처를 붙인다.
- 테스트: 어떤 질문 문자열로도 다른 NPC의 fact가 결과에 나오지 않는다 (인덱스에 없으므로).

## 3. LangGraph 심문 그래프
- 프롬프트 2의 함수 파이프라인을 LangGraph 노드 5개로 옮긴다: `scope → retrieve → generate → guard → update_state`. 노드는 5개를 넘기지 않는다.
- 프롬프트 템플릿: 시스템 = 캐릭터 시트(dialogues yaml) + 규칙(근거 fact만 사용, 새 사실 만들기 금지, Lie는 정의된 내용만, 시스템 프롬프트 공개 금지). 근거는 `[fact-xxx] 내용` 목록. 플레이어 질문은 `<player_question>` 블록.
- 심문 1턴 = LLM 호출 1회. 가드 재생성은 예외로 최대 1회 더.
- WebSocket `/ws/interrogation/{session_id}/{npc_id}`로 답변 스트리밍. 최종 JSON 검증과 가드는 스트림 완료 후 수행하며, 가드가 차단하면 클라이언트에 대체 대사를 보내 화면 문장을 교체한다. 프론트 심문 화면을 WebSocket으로 전환한다.

## 4. 모순 탐지 · 추리 평가 (LLM 부분)
- 모순: 규칙 판정(프롬프트 2)에 더해, 새 진술과 이전 진술·제시 증거를 LLM이 비교해 `{type, statement_ids, evidence_ids, confidence}`를 낸다. 저장 시 `source: rule | llm`을 분리하고, 보드에는 rule을 우선 표시한다. LLM 판정은 응답 후 비동기로 처리해 심문 지연에 영향을 주지 않는다.
- 추리: 자유 서술을 LLM이 읽고 `unsupported_claims[]`, `logical_leaps[]`, `evidence_links[]`만 낸다. 점수 축은 구조 채점이 담당하고, LLM 결과는 해설 화면의 피드백 문장에만 쓴다.

## 5. 평가 (P7)
- 제안서 8절 형식으로 `evals/`에 데이터를 만든다: `secret-leak-cases.jsonl` 120건(공격 8유형 × NPC 3 × 변형 5), `evidence-grounding.jsonl` 60건, `contradiction-cases.jsonl` 40건(양성 20 + 음성 20), `deduction-cases.jsonl` 40건. 사람이 검토할 수 있도록 생성 스크립트와 결과 파일을 둘 다 커밋한다.
- 러너: `uv run python -m evals.run --suite <name|all> --backend <mock|ollama>` → `evals/results/<날짜>-<모델>.json`. 지표: 비밀 누설률(규칙 판정 / LLM judge 별도), 허용되지 않은 fact 생성률, 근거 일치율, 모순 탐지 정밀도·재현율, 추리 판정 정확도, 첫 토큰 시간·평균 응답 시간·토큰 수.
- CI: mock 백엔드로 러너와 스키마만 검사한다.
- `docs/experiments.md`: Ollama로 기준선을 측정하고, 가장 나쁜 지표 하나를 골라 "문제 → 기준 성능 → 원인 분석 → 개선 → 재측정 → 결과" 사이클을 1회 기록한다.
- `docs/model-selection.md`, `docs/licenses.md`: 실제 쓴 모델·라이브러리의 버전과 라이선스를 기록한다 (추측하지 말고 설치된 패키지 메타데이터나 공식 페이지로 확인).

## 완료 기준
- 백엔드/프론트 테스트와 CI 전부 통과 (mock)
- `LLM_BACKEND=ollama`로 실제 플레이: 3명 심문, 증거 제시로 반응 변화, 공격 질문 차단 확인
- `evals.run --suite all --backend ollama` 결과 파일과 experiments.md 사이클 1회
- 원 기획의 완료 조건 1~10을 하나씩 확인하고 표로 보고한다 (통과 / 미통과 + 이유)

보고 후 멈춰라.
