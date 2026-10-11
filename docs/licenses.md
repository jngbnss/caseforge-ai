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

## AI 런타임 · 라이브러리 (4단계)

설치된 패키지 메타데이터의 `License-Expression`으로 확인했다 (2026-10-11). Ollama는 저장소의 LICENSE 파일로 확인했다.

| 패키지 / 도구 | 버전 | 라이선스 | 용도 |
|---|---|---|---|
| langgraph | 1.2.14 | MIT | 심문 그래프 (5노드) |
| langchain-core | 1.6.9 | MIT | langgraph 의존성 |
| faiss-cpu | 1.15.1 | MIT | NPC별 벡터 인덱스 |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 벡터 연산 |
| Ollama | 0.40.2 | MIT | 로컬 LLM·임베딩 서버 (별도 설치, 저장소에 포함하지 않음) |

## 모델

`ollama show <모델>`이 표시하는 라이선스로 확인했다. 가중치는 저장소에 넣지 않고 각자 `ollama pull`로 받는다.

| 모델 | 태그 · 양자화 | 크기 | 라이선스 | 용도 |
|---|---|---|---|---|
| Qwen3-8B | `qwen3:8b` · Q4_K_M · 8.2B 파라미터 · 문맥 40,960 | 5.2 GB | Apache-2.0 | NPC 심문, 모순 판정, 추리 피드백, 평가 judge |
| BAAI/bge-m3 | `bge-m3` · F16 · 567M 파라미터 · 1024차원 | 1.2 GB | MIT | NPC별 사실 검색 임베딩 |

## 글꼴 · 그림

글꼴은 Google Fonts에서 불러오며 저장소에 넣지 않는다. 화면 그림(용의자 초상화, 증거 아이콘, 평면도 가구, 코르크 보드)은
`frontend/src/components/art.tsx`·`SceneScreen.tsx`에서 SVG·CSS로 직접 그려 외부 이미지가 없다.

| 글꼴 | 라이선스 | 용도 |
|---|---|---|
| IBM Plex Sans KR · IBM Plex Mono | SIL OFL 1.1 | 본문 · 고정폭 |
| Nanum Myeongjo | SIL OFL 1.1 | 제목 |
| Nanum Pen Script | SIL OFL 1.1 | 손글씨 (쪽지 · 메모) |
