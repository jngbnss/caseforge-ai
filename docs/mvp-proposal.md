# CaseForge AI — MVP 제안서

> 상태: 제안 (승인 대기) · 작성일 2026-10-11
> 선택지가 있는 항목은 모두 권장안을 택했다. 근거는 `decision-log.md`에 있다.

## 0. 저장소 현황

- `main` 브랜치, 커밋 없음, 파일 없음 → 처음부터 시작한다.

---

## 1. MVP 구현 단계

원칙: **LLM 없이 끝까지 플레이할 수 있는 게임을 먼저 만들고**, 그다음 LLM을 붙인다.
이렇게 하면 단계마다 결정론적인 테스트가 가능하다.

| 단계 | 내용 | 완료 기준 |
|---|---|---|
| **P0** 기반 | 모노레포 골격, Ruff/pytest/tsc/vite build CI, `docs/` 템플릿, `.env.example`, LICENSE | 빈 앱으로 CI 통과 |
| **P1** 사건 데이터 | Case Bible Pydantic 스키마, `cases/museum-001/*.yaml`, 로더 | 스키마 검증 테스트 통과 |
| **P2** 검증기 | 규칙 기반 + NetworkX 시간선 검증, 퍼즐 유일해 검사 (`case-validator` 패키지) | museum-001 통과, 망가뜨린 fixture는 실패 |
| **P3** 게임 엔진 | 세션 상태, 증거 수집, 퍼즐 판정, 잠금 해제, 구조화된 추리 채점 (REST) | 대본 NPC로 API만 사용해 E2E 클리어 |
| **P4** 프론트엔드 | 6개 화면, 2D 포인트앤클릭, 수사 보드 | 브라우저에서 처음부터 끝까지 플레이 |
| **P5** 심문 AI | LLM/임베딩 어댑터, NPC별 검색, LangGraph 심문 그래프, 누설 가드, WebSocket 스트리밍 | Mock으로 CI 통과, Ollama로 로컬 플레이 |
| **P6** 모순·추리 AI | 모순 탐지(규칙/LLM 분리 저장), 추리 LLM 의미 평가 | 평가셋 기준선 측정 |
| **P7** 평가·실험 | `evals/*.jsonl`, 평가 러너, `experiments.md` 개선 사이클 1회 이상 | 완료 조건 10번 충족 |
| **P8** (선택) 생성기 | Case Generator → 검증기 → 재시도 → 실패 시 museum-001로 대체 | 생성 성공률 측정 |

---

## 2. Case Bible 스키마 (Pydantic 개요)

```python
class Fact(BaseModel):
    fact_id: str                      # "fact-014"
    content: str
    kind: Literal["truth", "testimony", "lie", "record"]
    source: str                       # "security-log", "suspect-02" ...
    time: TimeRange | None
    location_id: str | None
    subjects: list[str]               # 관련 인물/증거 ID
    known_by: list[str]               # NPC ID 목록
    available_to_player: bool = False
    unlock_condition: Condition | None

class Lie(BaseModel):                 # 거짓말도 Bible 안에서 정의한다
    lie_id: str
    npc_id: str
    contradicts_fact_id: str          # 어떤 진실을 숨기는지
    claim: str                        # NPC가 주장하는 내용
    breaks_on: list[str]              # 제시되면 거짓말이 무너지는 evidence_id

class Secret(BaseModel):
    secret_id: str
    npc_id: str
    fact_ids: list[str]
    reveal_when: Condition            # 예: evidence 제시 AND trust >= 2

class Evidence(BaseModel):
    evidence_id: str
    name: str
    location_id: str
    discoverable: Condition           # 항상 / puzzle-02 완료 후
    proves_fact_ids: list[str]
    role: Literal["key", "supporting", "red_herring"]

class Puzzle(BaseModel):
    puzzle_id: str
    prompt: str
    input_type: Literal["sequence", "code", "arrangement"]
    answer: str | list[str]           # 서버 전용, 클라이언트로 보내지 않는다
    hints: list[str]
    requires: Condition | None
    unlocks_evidence: list[str]

class TimelineEvent(BaseModel):
    event_id: str
    time: TimeRange
    actor_id: str
    location_id: str
    action: str
    fact_ids: list[str]

class Solution(BaseModel):
    culprit_id: str
    motive_id: str                    # 선택지 ID + 핵심 키워드
    method_steps: list[str]           # fact_id 순서
    key_evidence: list[str]           # 최소 증명 집합
    acceptable_evidence: list[str]    # 부분 점수

class CaseBible(BaseModel):
    model_config = ConfigDict(frozen=True)  # 게임 중 변경 불가
    case_id: str
    title: str
    briefing: Briefing
    locations: list[Location]
    suspects: list[Suspect]
    facts: list[Fact]
    lies: list[Lie]
    secrets: list[Secret]
    evidence: list[Evidence]
    puzzles: list[Puzzle]
    timeline: list[TimelineEvent]
    solution: Solution
```

- `Condition`은 작은 DSL로 만든다: `{"all": [{"evidence_presented": "ev-03"}, {"trust_gte": 2}]}`. 코드로 평가하며 LLM은 관여하지 않는다.
- 세션을 시작할 때 Bible을 로드한 뒤 SHA-256 해시를 세션에 기록한다. 평가 로그에도 해시를 남긴다.

---

## 3. NPC별 지식 분리

**물리적 분리 + 요청 단위 스코프 + 출력 가드**의 3중 구조로 만든다.

1. **빌드 시 분리**: 사건을 로드하면 NPC마다 별도의 FAISS 인덱스를 만든다.
   `index[npc_id]`에는 `npc_id ∈ known_by`인 fact만 들어간다. 다른 NPC의 비밀은 해당 인덱스에 **존재하지 않는다**.
   메타데이터 필터에 의존하지 않는다.
2. **요청 시 스코프** (`KnowledgeScope.build(session, npc_id)`)
   - = 자기 인덱스 중 unlock 조건을 충족한 fact
   - ∪ 플레이어가 **이 NPC에게** 제시한 증거
   - ∪ 이 NPC와의 대화 기록
   - ∪ `reveal_when`을 충족한 자기 secret
   - npc_id는 서버 세션에서 정하며 사용자 입력에서 받지 않는다.
3. **프롬프트 구성**: 시스템 프롬프트는 서버 템플릿으로 만든다. 플레이어 질문은 `<player_question>` 데이터 블록에 넣는다. 검색된 근거는 `[fact-xxx]` 태그와 함께 전달한다.
4. **출력 가드** (생성 후, 규칙 기반)
   - `revealed_fact_ids ⊆ scope` 검사
   - 금지 fact의 **카나리 키워드**(예: "9시 12분", "사물함", "채무") 문자열/정규식 매칭
   - 위반 시 1회 재생성 → 그래도 실패하면 캐릭터별 회피 대사로 대체 → 위반을 로그에 남긴다 (누설률 지표)

---

## 4. Case Validator 규칙

| ID | 단계 | 검사 |
|---|---|---|
| V01 | 규칙 | 모든 참조 ID(fact/evidence/location/suspect)가 존재한다 |
| V02 | 규칙 | `solution.key_evidence`는 전부 발견 가능하다 (조건 체인이 시작 상태에서 도달 가능) |
| V03 | 규칙 | 퍼즐 선행조건 그래프에 순환이 없고 모든 퍼즐에 도달할 수 있다 |
| V04 | 규칙 | 퍼즐 정답이 유일하다 (sequence/code 입력 공간을 전수 또는 제약 탐색) |
| V05 | 규칙 | 시작 시 공개된 정보만으로는 범인을 특정할 수 없다 (퍼즐/심문이 필요) |
| V06 | 규칙 | 각 Lie에 `breaks_on` 증거가 1개 이상 있으며 그 증거는 발견 가능하다 |
| V07 | 규칙 | 모든 Secret의 `reveal_when`은 충족될 수 있다 |
| T01 | 그래프 | 한 인물이 겹치는 시간에 두 장소에 존재하지 않는다 |
| T02 | 그래프 | 증거의 `time/location`이 연결된 timeline 이벤트와 일치한다 |
| T03 | 그래프 | 이동이 가능하다 (장소 간 최소 이동시간 adjacency) |
| U01 | 그래프 | **유일 범인**: 기회(범행 시간에 현장 접근 가능) ∧ 수단 ∧ 증거 체인을 동시에 만족하는 용의자는 culprit 하나뿐이다 |
| U02 | 그래프 | key_evidence를 제거하면 U01이 깨진다 (증거가 실제로 필요함) |
| L01 | LLM | 동기·서사의 개연성, 힌트 공정성에 대한 비평. **경고만 하며 통과/실패 판정에는 쓰지 않는다** |

산출물은 `ValidationReport{errors, warnings, metrics}`이다. CLI 예: `case-validator check cases/museum-001`.

---

## 5. 첫 사건: `museum-001` 「사라진 푸른 다이아몬드」

**상황**: 한빛시립박물관. 개장 전 감정에서 전시 중이던 "푸른 별" 다이아몬드가 정교한 모조품으로 확인됐다. 전날 밤 20:30 폐관 후 관내에 있던 사람은 3명이다.

| ID | 인물 | 겉으로 보이는 혐의 | 비밀 (진실) |
|---|---|---|---|
| suspect-01 | 한서윤 (수석 큐레이터) | 20:50~21:25 행방 불명 | 경쟁 경매사와 몰래 이직 면접 통화를 했다 (주차장) |
| suspect-02 | 박도현 (야간 경비원) | **21:12 그의 카드로 수장고 출입** | 21:05~21:20 근무지를 이탈해 흡연했다. 카드는 휴게실 사물함에 두었다 |
| **suspect-03** | **윤재민 (보존 복원가)** — 범인 | 복원실에서 야근 중이었다고 주장 | 도박 빚 → 개인 수집가의 제안. 복원 작업 중 본뜬 모조품으로 바꿔치기했다 |

**진짜 시간선 (요약)**
- 20:30 폐관 · 20:50 한서윤 주차장으로 이동 · 21:00 박도현 마지막 순찰
- 21:05 박도현 흡연 구역으로 이동 (카드는 사물함에 둠)
- 21:08 윤재민이 복원실 단말로 CCTV를 "점검 모드"로 전환 (21:08~21:16 녹화 공백)
- 21:10 윤재민이 휴게실 사물함에서 카드를 가져감 → 21:12 수장고/전시실 출입 → 21:14 바꿔치기
- 21:18 카드 반납 · 21:20 박도현 복귀 · 21:25 한서윤 복귀

**물리적 증거 5개**
1. `ev-01` 출입 로그: 21:12 박도현 카드 — *red herring*
2. `ev-02` 흡연 구역의 꽁초 + 휴게실 자판기 영수증 21:07 — 경비원 알리바이 보강
3. `ev-03` 복원실 쓰레기통의 실리콘 몰드 조각 — *key* (모조품 제작)
4. `ev-04` 진열장 받침의 연마 가루 + 복원용 니트릴 장갑 섬유 — *key*
5. `ev-05` 진열장 속 모조품 (분광 감정서 포함) — 사건의 출발점

**퍼즐 3개 (각각 추가 기록 공개)**
- `pz-01` CCTV 프레임 시간 순서 맞추기 → `rec-01`: 21:08~21:16 공백과 공백 직전 복원실 단말 로그인 화면
- `pz-02` 복원실 금고 암호 (전시 카드의 연도 3개로 추론) → `rec-02`: 채무 독촉장 (동기)
- `pz-03` 찢어진 메모 조합 → `rec-03`: 윤재민 필체의 "21:10 휴게실 — 사물함 3번"

**정답**: 범인 suspect-03 · 동기 도박 빚 · 수법 CCTV 공백 → 경비 카드 도용 → 몰드로 만든 모조품과 바꿔치기 · 핵심 증거 `ev-03, ev-04, rec-01, rec-03`

**거짓말 설계 예시**
- 윤재민: "21시엔 복원실에서 한 번도 안 나갔다" → `rec-03`, `ev-04`를 제시하면 무너진다
- 박도현: "21시부터 계속 경비실에 있었다" → `ev-02`를 제시하면 무너진다 (단, 범인은 아니다)
- 한서윤: "사무실에서 도록 교정을 했다" → 출입 로그상 사무실 문이 열리지 않았다는 사실로 무너진다 → 이직 통화를 자백한다

---

## 6. 프론트엔드 / 백엔드 책임

| 영역 | 백엔드 (권위) | 프론트엔드 (표현) |
|---|---|---|
| 사건 데이터 | Bible 전체 보관, 공개된 부분만 직렬화 | 받은 공개 데이터만 렌더링 |
| 증거·잠금 | 수집/잠금 해제 판정 | 클릭 이벤트 전송, 결과 표시 |
| 퍼즐 | 정답 검증 (정답은 클라이언트로 보내지 않음) | 입력 UI, 힌트 요청 |
| 심문 | 스코프, 검색, LLM, 가드, 감정/신뢰 상태 | 채팅 UI, 증거 제시, 스트리밍 표시 |
| 수사 보드 | 모순 탐지 결과 제공 | 카드 배치, 연결선 (배치는 로컬 상태) |
| 추리 | 채점 (구조 + LLM) | 제출 폼, 해설 화면 |
| 통신 | REST (상태 변경), WebSocket `/ws/interrogation/{session}` | Zustand 스토어, API 클라이언트 |

**핵심 규칙**: 프론트 번들과 API 응답에 `solution`, 잠긴 fact, 퍼즐 정답이 **절대 포함되지 않는다**. 응답 스키마 테스트로 강제한다.

---

## 7. AI 모델 어댑터 구조

```
backend/app/core/llm/
  ports.py        # Protocol 정의
  ollama.py       # OllamaAdapter  (format=JSON schema 강제, think 비활성)
  llamacpp.py     # LlamaCppAdapter (GBNF grammar) — 비교 실험용
  mock.py         # MockLLM: fixture 기반 결정론적 응답 (CI)
backend/app/core/embedding/
  ports.py
  bge.py          # BAAI/bge-m3 (한국어 지원)
  mock.py         # 해시 기반 결정론 벡터
```

```python
class LLMPort(Protocol):
    async def generate(self, messages: list[Message], schema: type[T],
                       *, temperature: float = 0.3, max_tokens: int = 512) -> LLMResult[T]: ...
    async def stream(self, messages: list[Message]) -> AsyncIterator[str]: ...
# LLMResult = parsed + raw_text + usage(tokens) + latency_ms + model_id
```

- 선택은 `.env`의 `LLM_BACKEND=ollama|llamacpp|mock`, `LLM_MODEL=qwen3:8b-q4_K_M`로 한다.
- 모든 호출은 `generate()`를 거친다 → Pydantic 검증 → 실패 시 오류 메시지를 붙여 1회 재요청 → 그래도 실패하면 안전 기본값을 쓰고 로그를 남긴다.
- 호출마다 토큰/지연/검증 실패를 계측한다 → `experiments.md` 지표의 원천

---

## 8. 평가 데이터 제작 방법

| 파일 | 한 줄 형식 | 제작 |
|---|---|---|
| `secret-leak-cases.jsonl` | `{id, npc_id, state, question, forbidden_fact_ids, attack_type}` | 공격 유형 8종 × NPC 3명 × 변형 5개 ≈ 120개. 유형: 직접 질문, 다른 NPC 비밀, 시스템 프롬프트 요구, 역할 탈취, 가정법("만약 범인이라면"), 증거 미제시 상태의 유도, 다국어/인코딩, 반복 압박 |
| `evidence-grounding.jsonl` | `{id, npc_id, state, question, allowed_fact_ids, must_cite?}` | 정상 질문 60개. 답의 `revealed_fact_ids ⊆ allowed` 여부와 새로운 사실 생성 여부 |
| `contradiction-cases.jsonl` | `{id, statements[], evidence[], expected: [{type, pair}]}` | Bible의 Lie에서 자동 생성 + 수작업 음성 사례 (모순 없음) 동수 |
| `deduction-cases.jsonl` | `{id, submission, expected_scores{culprit,motive,method,evidence,leaps}}` | 정답/부분정답/오답/증거 없는 정답 4개 층 × 10개. **팀원 2명이 독립 채점**하고 Cohen's κ를 보고 → 사람-AI 일치율의 기준 |

- 판정: 누설은 **규칙(카나리, fact_id)이 1차**, LLM judge는 보조로 쓰며 결과를 별도 컬럼에 저장한다.
- 러너: `python -m evals.run --suite secret-leak --backend ollama` → `evals/results/<date>-<model>.json`
- CI에서는 Mock 백엔드로 러너와 스키마만 검사하고, 실제 수치는 로컬 GPU에서 측정한다.

---

## 9. 7인 팀 역할 분담

| # | 역할 | 주요 산출물 |
|---|---|---|
| 1 | **PM / 사건 디자이너** | museum-001 Bible, 대사 톤, 플레이테스트, decision-log 관리 |
| 2 | **백엔드 리드** | FastAPI, 세션/게임 엔진, Condition DSL, 퍼즐 판정, 응답 스키마 |
| 3 | **AI — 심문 에이전트** | LangGraph 심문 그래프, 프롬프트, 감정/신뢰 상태, 누설 가드 |
| 4 | **AI — 검색·평가** | 임베딩/FAISS, KnowledgeScope, evals 러너, experiments.md |
| 5 | **검증기 / OSS / CI** | `case-validator` 독립 패키지, NetworkX 시간선, GitHub Actions, licenses.md |
| 6 | **프론트엔드 A** | 브리핑·현장 조사·퍼즐 화면, 2D 씬 |
| 7 | **프론트엔드 B** | 심문 채팅(WebSocket)·수사 보드·추리·해설 화면 |

- 인터페이스 계약(Pydantic → OpenAPI → TS 타입 자동 생성)을 P1 말에 확정해 병렬로 작업한다.
- 1번과 5번이 사건 데이터와 검증기를 페어로 맞춘다. 3번과 4번이 매주 평가 수치를 공유한다.

---

## 10. 가장 큰 기술적 위험

| 순위 | 위험 | 완화책 |
|---|---|---|
| 1 | **Qwen3-8B 4bit의 한국어 NPC 품질**: 캐릭터 이탈, 근거 없는 사실 생성, 비밀 누설 | 작은 스코프 컨텍스트, fact 태그 기반 답변, 규칙 기반 출력 가드, 평가셋으로 반복 측정. 기준 미달이면 어댑터만 교체 (예: 더 큰 모델이나 API) |
| 2 | **구조화 출력 실패** (JSON 깨짐, thinking 토큰 혼입) | Ollama `format` 스키마 강제, think 비활성, 재요청 1회, 안전 기본값 |
| 3 | **응답 지연** (로컬 GPU 1회 호출 수 초 × 그래프 노드 수) | 심문 1턴 = LLM 1회 원칙 (검색·가드·모순 규칙은 비-LLM), 스트리밍, 모순 LLM 판정은 비동기 후처리 |
| 4 | **사건 설계의 유일해·공정성** | 검증기 U01/U02/V05를 먼저 만들고 사건을 그 위에서 작성. 외부 플레이테스트 3회 |
| 5 | **자유서술 추리 채점의 주관성** | 구조 비교가 점수의 주축, LLM은 "논리 비약/근거 없는 주장" 플래그만. κ로 사람 기준 검증 |
| 6 | **LangGraph 과설계** | MVP 그래프는 노드 5개 이하 (scope → retrieve → generate → guard → update_state) |

---

## 승인 요청

승인되면 **P0 (저장소 골격 + CI + docs 템플릿)** 부터 작은 PR 단위로 진행한다.
