# Case Bible 스키마

구현: `packages/case-validator/src/case_validator/schema.py` (Pydantic v2).
모든 모델은 `frozen=True, extra="forbid"`이고 컬렉션은 tuple이다. 로드 후에는 바꿀 수 없고, 모르는 필드가 있으면 로드에 실패한다.

## 파일 구성

`cases/<case_id>/` 아래 파일을 로더(`load_case`)가 하나로 합친다. 같은 최상위 키가 두 파일에 있으면 오류다.

| 파일 | 최상위 키 |
|---|---|
| `case.yaml` | `case_id`, `title`, `briefing`, `locations` |
| `timeline.yaml` | `facts`, `timeline` |
| `suspects.yaml` | `suspects`, `lies`, `secrets` |
| `evidence.yaml` | `evidence` |
| `puzzles.yaml` | `puzzles` |
| `solution.yaml` | `solution` |
| `dialogues/<suspect_id>.yaml` | `suspect_id` + `Dialogue` 필드 → 해당 용의자의 `dialogue`로 들어간다 |

`load_case(path)`는 `LoadedCase(bible, sha256)`를 반환한다. 해시는 YAML 서식과 무관하도록 `model_dump(mode="json")`을 키 정렬한 JSON으로 계산한다.

## 공통 타입

**TimeRange** — `"21:12"`(순간) 또는 `{start: "21:04", end: "21:07"}`. 하룻밤 안의 `HH:MM`만 쓴다.
- `overlaps()`: 반열린 구간. 순간은 `[t, t+0.5분)`으로 본다. T01(동시 존재)과 U01(현장 체류)에 쓴다. 21:18에 끝나는 일과 21:18에 시작하는 일은 겹치지 않는다.
- `touches()`: 닫힌 구간. T02(증거 시각이 사건 시각과 맞는가)에 쓴다. 21:07 영수증은 21:04–21:07 사건과 맞는다.

**Condition** (DSL, `conditions.evaluate(cond, state, npc=None)`로 평가)

| 형태 | 참이 되는 경우 |
|---|---|
| `{always: true}` | 항상 |
| `{all: [...]}` / `{any: [...]}` | 모두 / 하나 이상 (`all: []`은 참, `any: []`은 거짓) |
| `{evidence_collected: ev}` | 플레이어가 증거를 수집함 |
| `{evidence_presented: ev, npc?: id}` | 증거를 그 NPC에게 제시함. `npc`가 없으면 문맥 NPC, 문맥도 없으면 아무 NPC |
| `{puzzle_solved: pz}` | 퍼즐을 풂 |
| `{trust_gte: n, npc?: id}` | 그 NPC의 신뢰도 ≥ n (상한 `MAX_TRUST = 5`). `npc` 생략 규칙은 위와 같다 |

`Secret.reveal_when`은 문맥 NPC가 `secret.npc_id`로 평가된다.

## 모델

**Briefing** — `headline`, `summary`, `objective`, `opening_location_id`, `motive_options[{motive_id, label}]` (추리 제출 시 동기 선택지. 공개 정보).

**Location** — `location_id`, `name`, `description`, `adjacent[{to, minutes}]`. 무방향 인접 정보이며 최단 이동 시간은 NetworkX 최단 경로로 계산한다.

**Suspect** — `suspect_id`, `name`, `role`, `public_profile`, `apparent_suspicion`, `capabilities`(실제로 가진 수단, U01), `dialogue{personality, speech_style, sample_lines, evasion_lines}`.

**Fact**

| 필드 | 설명 |
|---|---|
| `fact_id` | `fact-NNN` |
| `content` | 사실 문장 |
| `kind` | `truth`(진실) / `testimony`(증언) / `lie` / `record`(기록) |
| `source` | 출처 (`security-log`, `suspect-02` …) |
| `time`, `location_id`, `subjects` | 시각, 장소, 관련 인물·증거·장소 ID |
| `known_by` | 이 사실을 아는 NPC. P5에서 NPC별 인덱스가 이 목록으로 만들어진다. 기록처럼 아무도 직접 모르는 사실은 빈 목록 |
| `available_to_player`, `unlock_condition` | 플레이어 공개 여부와 조건. 조건 없이 공개된 fact는 시작부터 알려진 사실이다 |
| `implicates` | 이 사실이 범인으로 가리키는 용의자 (U01 증거 체인) |
| `leak_forbidden` | NPC가 절대 말하면 안 되는 사실 (범인 전용 범행 사실) |
| `canary_keywords` | 출력 가드의 문자열 매칭용 키워드 |

**Lie** — `lie_id`, `npc_id`, `contradicts_fact_id`(숨기는 진실), `claim`(NPC의 주장), `breaks_on`(제시하면 무너지는 증거).

**Secret** — `secret_id`, `npc_id`, `fact_ids`, `reveal_when`.

**Evidence** — `evidence_id`, `name`, `description`, `location_id`(발견 장소), `discoverable`(Condition), `proves_fact_ids`, `role`(`key`/`supporting`/`red_herring`), `attests[{event_id, location_id, time?}]`(이 증거가 말해 주는 사건의 장소·시각, T02).
퍼즐 보상 기록(`rec-*`)도 Evidence이며 `discoverable: {puzzle_solved: pz-NN}`이다.

**Puzzle** — `puzzle_id`, `title`, `prompt`, `location_id`, `input_type`, `items[{item_id, label}]`(순서·배열형), `code_length`/`code_alphabet`(코드형), `constraints`, `answer`(서버 전용), `hints`, `requires`, `unlocks_evidence`.

`constraints`는 플레이어에게 보이는 단서를 규칙으로 옮긴 것이다. V04는 `answer`를 보지 않고 이 제약만으로 입력 공간을 전수 탐색한다.

| kind | 적용 | 의미 |
|---|---|---|
| `before {first, then}` | sequence, arrangement | first가 then보다 앞 |
| `immediately_before {first, then}` | sequence, arrangement | then이 first 바로 다음 |
| `segment_in {start, length, values}` | code | `code[start:start+length]`가 values 중 하나 |
| `segment_not_in {…}` | code | 위의 부정 |
| `segments_ascending {length}` | code | length 단위로 자른 조각이 엄격히 오름차순 |

**TimelineEvent** — `event_id`, `time`, `actor_id`(건물 전체 사건이면 `null`), `location_id`, `action`, `fact_ids`. 진실의 시간선이다.

**Solution** (서버 전용) — `culprit_id`, `motive_id`, `motive_keywords`, `method_steps`(fact 순서), `key_evidence`(최소 증명 집합), `acceptable_evidence`(부분 점수), `crime{location_id, time}`(범행 장소·시간대), `required_means`(범행에 필요한 수단).

## 검증 규칙 (`case-validator check`)

도달 가능성은 플레이어에게 가장 유리한 상태로 고정점을 계산한다: 수집한 증거를 모든 NPC에게 제시했고 신뢰도가 상한이라고 가정한다.

| ID | 검사 |
|---|---|
| V01 | ID 중복이 없고 모든 참조(조건 포함)가 존재한다 |
| V02 | `key_evidence`가 전부 도달 가능하다 |
| V03 | 퍼즐 선행조건 그래프(퍼즐 → 보상 증거 → 다음 퍼즐)에 순환이 없고 모든 퍼즐에 도달한다 |
| V04 | 단서 제약을 만족하는 답이 정확히 하나이고 `answer`와 같다 |
| V05 | 퍼즐과 심문 없이 얻을 수 있는 정보만으로는 범인의 증거 체인이 완성되지 않는다 |
| V06 | 각 Lie에 `breaks_on`이 있고 그중 하나 이상이 도달 가능하다 |
| V07 | 각 Secret의 `reveal_when`이 최선의 상태에서 참이 된다 |
| T01 | 한 인물이 겹치는 시간에 두 장소에 있지 않다 |
| T02 | 증거의 `attests`가 연결된 사건의 장소·시각과 맞는다 |
| T03 | 한 인물의 연속된 사건 사이 시간이 최단 이동 시간 이상이다 |
| U01 | 기회 ∧ 수단 ∧ 증거 체인을 모두 만족하는 용의자가 culprit 하나뿐이다 |
| U02 | `key_evidence`만으로 체인이 완성되고, 어느 하나라도 빼면 체인이 깨진다 |
| L01 | (인터페이스만) LLM 서사 비평. 경고만 추가한다 |

U01 정의:
- **기회**: 진실 시간선에서 범행 시간대에 현장에 있었거나, 비어 있는 시간에 이동 시간을 포함해 현장에 다녀올 수 있다.
- **수단**: `solution.required_means ⊆ suspect.capabilities`.
- **증거 체인**: 그 용의자를 `implicates`하는 truth/record fact가 하나 이상 있고, 전부 도달 가능한 증거(또는 시작 공개 fact)로 증명된다.

`load_case`가 실패하면 CLI는 `LOAD`(파일·YAML 문제) 또는 `SCHEMA`(Pydantic 검증 실패) 오류를 낸다.
