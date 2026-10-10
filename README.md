# CaseForge AI

AI 용의자를 심문하고, 현장 증거를 모으고, 퍼즐을 풀어 범인을 추리하는 수사 게임.
사건의 진실은 게임 시작 전에 고정되며, AI NPC는 자신에게 허용된 정보만으로 답한다.

- 기획과 설계: [docs/mvp-proposal.md](docs/mvp-proposal.md)
- 결정 기록: [docs/decision-log.md](docs/decision-log.md)
- 사건 스키마와 검증 규칙: [docs/case-schema.md](docs/case-schema.md)
- 단계별 구현 프롬프트: [docs/build-prompts/](docs/build-prompts/README.md)

## 구성

| 경로 | 내용 |
|---|---|
| `backend/` | FastAPI 게임 서버 |
| `frontend/` | React + TypeScript + Vite 클라이언트 |
| `packages/case-validator/` | 사건 검증 독립 라이브러리 (OSS로 분리 예정) |
| `cases/` | 사건 데이터 (YAML) |
| `evals/` | AI 평가 데이터셋 |

## 준비

- Python 3.12와 [uv](https://docs.astral.sh/uv/)
- Node.js 24

```bash
uv sync --all-packages        # 파이썬 의존성 (루트에서)
cd frontend && npm install    # 프론트 의존성
cp .env.example .env          # 필요하면 값 수정
```

## 실행

백엔드와 프론트를 한 번에 띄운다 (LLM은 Mock 대본).

```bash
cd frontend && npm run dev:all
# → http://localhost:5173   (개발자 모드: http://localhost:5173/?dev=1)
```

- 8000 포트를 다른 프로그램이 쓰고 있으면 `BACKEND_PORT=8100 npm run dev:all`
- 따로 띄우려면: `cd backend && uv run uvicorn app.main:app --reload` 와 `cd frontend && npm run dev`
  (백엔드가 8000이 아니면 `API_TARGET=http://127.0.0.1:<포트> npm run dev`)
- 개발자 모드의 근거·가드 정보는 백엔드 `DEBUG_API=true`일 때만 응답에 포함된다 (dev:all은 기본으로 켬)

## API 타입 갱신

백엔드 응답 모델을 바꾸면 프론트 타입을 다시 만든다. CI가 최신 여부를 검사한다.

```bash
cd backend && uv run python -m scripts.export_openapi
cd frontend && npm run gen:api
```

## 검사

```bash
uv run ruff check . && uv run ruff format --check .
cd packages/case-validator && uv run pytest
cd backend && uv run pytest
uv run case-validator check cases/museum-001
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
cd frontend && npx playwright install chromium && npm run e2e   # 브라우저 완주 테스트
```

## 라이선스

MIT. 사용하는 모델과 오픈소스의 라이선스는 [docs/licenses.md](docs/licenses.md)에 기록한다.
