# 진행 현황과 남은 일

2026-10-11 기준, 브랜치 `feat/stage-04-ai-evals`. 작업별 상세 기록은 [implementation-plan.md](implementation-plan.md), 실험 수치는 [experiments.md](experiments.md)에 있다.

## 1. 지금까지 한 것

| 단계 | 내용 | 상태 |
|---|---|---|
| 1단계 | Case Bible 스키마·로더·해시, 사건 검증기(망가뜨린 사건 16종), museum-001 사건 | 완료 |
| 2단계 | 게임 엔진·API: 세션, 현장 조사, 퍼즐, 증거 제시, 규칙 모순, 추리 채점, 대본 NPC로 API 완주 테스트 | 완료 |
| 3단계 | 프론트엔드(React): 브리핑·현장·퍼즐·심문·보드·추리·해설 화면, Playwright 완주 테스트 | 완료 |
| 4-1~4-4 | 로컬 LLM 심문(qwen3:8b), NPC별 지식 분리(bge-m3 인덱스+스코프+출력 가드), LangGraph 5노드, WebSocket 스트리밍 | 완료 |
| 4-5 | LLM 모순 탐지(비동기, 보드에 규칙/AI 구분 표시) | 완료 |
| 4-6 | LLM 추리 피드백(근거 없는 주장·논리 비약, 점수는 그대로) | 완료 |
| 4-7~4-8 | 평가셋 4종(누설 120·근거 60·모순 40·추리 40)과 평가 러너, Ollama 기준선 측정 | 완료 |
| 4-9 | 실험 기록, 모델·라이선스 문서, 완료 조건 점검표 | 완료 |
| 4-10 | EXP-002: 질문에 정답을 넣으면 범인이 시인하던 누설 차단(시각+장소 조합 규칙) | 완료, 채택 |
| 4-11 | EXP-003: 모순 판정 재확인 | 완료, **채택 안 함**(F1 0.72→0.70, 기본 끔) |
| 4-13 | 게임 화면 개편(탐정 사무소 테마, SVG 초상화·증거 사진·코르크 보드, 수사 안내, 지금 할 일 막대) | 완료 |

주요 수치 (Ollama qwen3:8b, RTX 4060):

- 누설(규칙 판정) 2/120. 남은 2건은 부인 답변을 평가 규칙이 누설로 센 오탐, 시인형 누설은 0건
- 범위 밖 사실 근거 0%, must_cite 85.4%
- 모순 탐지 P 0.63 / R 0.85 / F1 0.72 (EXP-001 반영)
- 추리 구조 점수 일치 100%, 비약 판정 75%
- 심문 응답 p50 2.0초, 첫 글자 p50 0.23초

로컬 검사: Ruff, 백엔드 pytest 87개, 사건 검증기 33개, 평가 mock 러너, 프론트 lint·typecheck·Vitest 15개·build, Playwright E2E 모두 통과.

## 2. 남은 일

### 사용자 결정 필요
- [ ] **PR 열기 → GitHub CI 첫 실행 (4-12)**: CI는 `main` push와 PR에서만 돈다. https://github.com/jngbnss/caseforge-ai/compare/main...feat/stage-04-ai-evals
- [ ] **중복 브랜치 정리**: 원격 `feat/stage-01-foundation-validator`, `feat/stage-02-game-engine-api`, 로컬 `rebuild/stage-03-frontend` 삭제 여부

### 화면 (다음 우선순위)
- [ ] **게임 화면 재검토**: 4-13 개편 결과가 사용자 확인에서 "별로"라는 평가. 무엇이 문제인지(그림 품질, 정보량, 흐름, 조작감 등) 구체적인 피드백을 받아 방향을 다시 정한다
- [ ] 심문 응답 대기(첫 호출 최대 20초 안팎) 동안 보이는 표시 개선

### AI · 평가
- [ ] EXP-004: 모순 정밀도 개선(시각 앞뒤 오독 오탐)
- [ ] EXP-005: 평가 누설 규칙이 부인 답변을 누설로 세는 문제 수정
- [ ] EXP-006: 판정용으로 더 큰 모델 비교
- [ ] 추리 서술 라벨을 팀원 2명이 독립 채점해 Cohen's κ 계산 (사람 작업)
- [ ] 다른 모델·llama.cpp 비교 (인터페이스 파일만 있음)

### 선택
- [ ] 5-1 Case Generator: 사건 생성 → 검증 → 재시도, 10회 중 유효 사건 수 측정

## 3. 직접 실행하기

```powershell
cd frontend
$env:LLM_BACKEND="ollama"; $env:EMBEDDING_BACKEND="ollama"; npm run dev:all   # 실제 모델 (Ollama에 qwen3:8b, bge-m3 필요)
npm run dev:all                                                              # mock 모드
```

브라우저에서 http://localhost:5173 (개발자 정보 표시는 `?dev=1`).
