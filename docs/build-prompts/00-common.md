# 공통 규칙 (모든 단계 프롬프트에 적용)

이 파일은 01~04 프롬프트가 참조한다. 구현 중 판단이 필요하면 아래 순서로 따른다.
1. 이 파일의 규칙
2. `docs/mvp-proposal.md` (스키마, 사건 내용, 검증 규칙, 어댑터 구조)
3. `docs/decision-log.md` (기술 선택)

## 기술 스택 (확정)
- 백엔드: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy + SQLite, pytest, Ruff, 패키지 관리는 `uv`
- 프론트: React + TypeScript + Vite, Zustand, Tailwind CSS, 2D 포인트앤클릭
- AI: Ollama(`qwen3:8b` 4bit 양자화), LangGraph, `BAAI/bge-m3`, FAISS(NPC별 독립 인덱스), NetworkX
- 사건 데이터: `cases/<case_id>/*.yaml`

## 절대 규칙
- 사건 정답(Case Bible)은 게임 시작 전에 고정한다. 로드 후 `frozen` 모델이며 SHA-256 해시를 세션에 기록한다.
- LLM에게 Case Bible 전체를 주지 않는다. NPC는 자기 인덱스 + 공개 조건 충족 fact + 그 NPC에게 제시된 증거 + 그 NPC와의 대화만 본다.
- 퍼즐 정답, 범인, 잠긴 fact, `solution`은 API 응답에 절대 포함하지 않는다. 응답 스키마 테스트로 강제한다.
- LLM 출력은 항상 Pydantic으로 검증한다. 실패하면 1회 재요청하고, 그래도 실패하면 안전 기본값을 쓰고 로그를 남긴다.
- 규칙으로 풀 수 있는 문제(퍼즐 판정, 조건 평가, 시간선 충돌)에 LLM을 쓰지 않는다.
- 모델 호출은 교체 가능한 어댑터(`LLMPort`, `EmbeddingPort`)로만 한다. CI와 테스트는 `mock` 어댑터를 쓰며 모델을 다운로드하지 않는다.
- 사용자 입력을 시스템 프롬프트 문자열에 직접 이어 붙이지 않는다. 데이터 블록으로 분리한다.
- API 키를 코드에 쓰지 않는다. `.env`는 커밋하지 않고 `.env.example`만 둔다. 로그에 비밀값을 남기지 않는다.
- GitHub Actions: `permissions: contents: read`, `pull_request_target` 금지, 외부 액션은 버전 고정

## 작업 방식
- 시작 전에 `git status`로 저장소 상태를 확인하고 `main`에서 작업 브랜치를 만든다 (`feat/stage-0N-<요약>`).
- 기능마다 테스트를 함께 작성한다. 테스트 없이 완료 처리하지 않는다.
- 작은 단위로 커밋한다. 커밋 메시지는 한국어나 영어 중 하나로 일관되게 쓴다.
- 기술 선택이나 범위 변경이 생기면 `docs/decision-log.md`에 D-번호를 이어서 기록한다.
- 끝나면 "완료 기준" 명령을 전부 실제로 실행하고 결과를 보고한다. 실패가 남아 있으면 숨기지 말고 보고한다.
- 이번 단계 범위 밖의 기능은 만들지 않는다. 필요하면 TODO로 남기고 보고서에 적는다.
- push와 PR 생성은 사용자가 요청할 때만 한다.
