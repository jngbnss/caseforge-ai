# CaseForge AI

고정된 사건 진실(Case Bible) 위에서 용의자를 자유 심문하고, 증거를 모아 모순 없이 범인을 추리하는 AI 수사 게임.
SSAFY AI × OSS 프로젝트 P2. 설계는 [`docs/mvp-proposal.md`](docs/mvp-proposal.md), 기술 결정은 [`docs/decision-log.md`](docs/decision-log.md).

## 현재 상태

| 단계 | 내용 | 상태 |
|---|---|---|
| P0 | 모노레포 골격, CI | 완료 |
| P1 | Case Bible 스키마, `museum-001` | 완료 |
| P2 | `case-validator` (규칙 + NetworkX 시간선) | 완료 |
| P3–P7 | 게임 엔진, 프론트, 심문 AI, 평가 | 예정 (`docs/build-prompts/`) |

## 구조

```
backend/                  FastAPI 게임 서버 (uv)
frontend/                 React + TypeScript + Vite, Tailwind, Zustand
packages/case-validator/  사건 스키마·로더·검증기 (독립 파이썬 패키지)
cases/museum-001/         첫 사건 「사라진 푸른 다이아몬드」
evals/                    평가셋과 러너 (P7)
docs/                     제안서, 결정 로그, 스키마 문서
pages/                    GitHub Pages 소개 페이지
```

## 실행

필요한 도구: [uv](https://docs.astral.sh/uv/) (Python 3.12는 uv가 받는다), Node.js 24.

```bash
# Python 워크스페이스 (backend + case-validator)
uv sync --all-packages

# 사건 검증 (오류가 있으면 종료 코드 1)
uv run case-validator check cases/museum-001

# 백엔드
cd backend
uv run ruff check . && uv run pytest
uv run uvicorn app.main:app --reload        # http://localhost:8000/health

# case-validator 테스트
cd packages/case-validator
uv run pytest

# 프론트엔드
cd frontend
npm install
npm run typecheck && npm run build
npm run dev                                   # http://localhost:5173 (/api → :8000)
```

설정은 `.env.example`을 `.env`로 복사해 바꾼다. 기본 LLM 백엔드는 `mock`이라 모델 없이 동작한다.

## 라이선스

MIT. 서드파티 라이선스는 [`docs/licenses.md`](docs/licenses.md).
