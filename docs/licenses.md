# 사용 오픈소스와 라이선스

버전은 `uv.lock`과 `frontend/package-lock.json`에 고정된 값을 기준으로 한다.
라이선스는 설치된 패키지 메타데이터(`License-Expression` / `package.json`의 `license`)에서 확인했다 (2026-10-11).

## 백엔드 · 검증기 (Python)

| 패키지 | 버전 | 라이선스 | 용도 |
|---|---|---|---|
| fastapi | 0.143.0 | MIT | API 서버 |
| uvicorn | 0.54.0 | BSD-3-Clause | ASGI 서버 |
| pydantic | 2.14.0 | MIT | 스키마 검증 |
| pydantic-settings | 2.15.0 | MIT | 설정 |
| sqlalchemy | 2.1.4 | MIT | DB |
| networkx | 3.7 | BSD-3-Clause | 사건 관계 그래프 |
| pyyaml | 6.0.3 | MIT | 사건 데이터 로드 |
| pytest | 9.1.1 | MIT | 테스트 (개발) |
| ruff | 0.17.0 | MIT | 린트 (개발) |
| httpx | 0.28.1 | BSD-3-Clause | 테스트 클라이언트 (개발) |

## 프론트엔드

| 패키지 | 버전 | 라이선스 | 용도 |
|---|---|---|---|
| react / react-dom | 19.3.0 | MIT | UI |
| zustand | 5.0.15 | MIT | 상태 관리 |
| vite | 6.4.4 | MIT | 빌드 |
| tailwindcss | 4.3.3 | MIT | 스타일 |
| typescript | 5.8.3 | Apache-2.0 | 타입 검사 |

## 모델 (4단계에서 도입 예정, 도입 시 확인 후 기록)

| 모델 | 버전 | 라이선스 | 비고 |
|---|---|---|---|
| Qwen3-8B (4bit) | 미정 | 도입 시 공식 모델 카드에서 확인 | |
| BAAI/bge-m3 | 미정 | 도입 시 공식 모델 카드에서 확인 | |
| LangGraph, FAISS, Ollama | 미정 | 도입 시 확인 | |
