# 아키텍처

> 템플릿. 각 단계가 끝날 때 채운다. 설계 근거는 `mvp-proposal.md`, 기술 선택은 `decision-log.md`.

## 구성 요소

| 디렉터리 | 역할 | 상태 |
|---|---|---|
| `packages/case-validator/` | Case Bible 스키마, 로더, 규칙·그래프 검증기 (독립 패키지) | P1–P2 완료 |
| `cases/` | 사건 데이터 (YAML) | museum-001 |
| `backend/` | FastAPI 게임 서버 | P0 골격 (`GET /health`) |
| `frontend/` | React + Vite 클라이언트 | P0 골격 |
| `evals/` | 평가셋과 러너 | P7 예정 |

## 데이터 흐름

TODO(P3): 세션 생성 → Bible 로드·해시 기록 → 공개 직렬화 → 상태 변경 REST.

## 지식 분리

TODO(P5): NPC별 FAISS 인덱스, KnowledgeScope, 출력 가드.

## 배포·실행

TODO: 로컬 실행, Ollama 의존성, GitHub Pages(소개 페이지).
