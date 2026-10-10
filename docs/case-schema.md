# 사건 스키마 (Case Bible)

코드: `packages/case-validator/src/case_validator/schema.py`
사건 데이터: `cases/<case_id>/`

모든 모델은 `frozen`이고 목록은 tuple이다. 정의되지 않은 필드는 거부한다(`extra="forbid"`).
로더는 정규화한 JSON의 SHA-256을 계산해 사건 버전을 식별한다.

## 파일 구성

| 파일 | 최상위 키 |
|---|---|
| `case.yaml` | `case_id`, `title`, `briefing`, `locations`, `deduction_options`, `facts` |
| `timeline.yaml` | `timeline` |
| `suspects.yaml` | `suspects`, `lies`, `secrets` |
| `evidence.yaml` | `evidence` |
| `puzzles.yaml` | `puzzles` |
| `solution.yaml` | `solution` (서버 전용) |
| `dialogues/*.yaml` | 용의자별 캐릭터 시트 1개씩 |

같은 최상위 키가 두 파일에 나오면 로드 오류다.

## 주요 모델

| 모델 | 필드 | 설명 |
|---|---|---|
| `Location` | `location_id`, `name`, `adjacent[{to, minutes}]` | 인접 정보는 무방향. T03 이동 시간 검사에 쓴다. |
| `Fact` | `fact_id`, `content`, `kind`(truth/testimony/lie/record), `source`, `time`, `location_id`, `subjects`, `known_by`, `available_to_player`, `unlock_condition`, `forbidden`, `canary_keywords` | `known_by`에 있는 NPC만 이 사실을 안다. `forbidden`이면 어떤 NPC도 직접 진술하지 않는다. 누설 가드는 `canary_keywords`를 답변에서 찾는다. |
| `Suspect` | `suspect_id`, `name`, `role`, `public_profile`, `capabilities` | `capabilities`는 U01의 수단 판정에 쓴다. |
| `Lie` | `lie_id`, `npc_id`, `contradicts_fact_id`, `claim`, `breaks_on` | NPC가 할 수 있는 거짓말은 여기 정의된 것뿐이다. `breaks_on` 증거를 제시하면 무너진다. |
| `Secret` | `secret_id`, `npc_id`, `fact_ids`, `reveal_when` | 조건이 충족되면 해당 NPC가 그 사실을 말할 수 있다. |
| `Evidence` | `evidence_id`, `name`, `description`, `location_id`, `source`(scene/puzzle), `discoverable`, `proves_fact_ids`, `role`(key/supporting/red_herring), `attests`, `implicates` | `attests`는 증거가 기록한 순간(시간선 이벤트·시각·장소). `implicates`는 이 증거가 어느 용의자의 기회·수단·동기를 입증하는지. |
| `Puzzle` | `puzzle_id`, `title`, `prompt`, `input_type`(sequence/code/arrangement), `options`, `order_clues`, `code_length`, `code_clues`, `answer`, `hints`, `requires`, `unlocks_evidence` | 정답 판정과 유일해 검사는 단서(`order_clues`, `code_clues`)로 코드가 한다. |
| `TimelineEvent` | `event_id`, `time`, `actor_id`, `location_id`, `action`, `fact_ids`, `is_crime` | 진짜 시간선. |
| `Solution` | `culprit_id`, `motive_id`, `method_id`, `method_steps`, `key_evidence`, `acceptable_evidence`, `crime{location_id, time}`, `required_means` | 추리 채점의 기준. |
| `Dialogue` | `suspect_id`, `personality`, `speech_style`, `sample_lines`(5개 이상), `evasions`(3개 이상) | LLM 캐릭터 프롬프트 재료. |

## 조건 DSL

```yaml
{evidence_collected: ev-01}
{evidence_presented: {evidence_id: ev-02, npc_id: suspect-02}}
{puzzle_solved: pz-01}
{trust_gte: {npc_id: suspect-01, value: 1}}
{all: [<조건>, <조건>]}
{any: [<조건>, <조건>]}
```

- `evaluate(condition, PlayState)`: 게임 중 실제 판정
- `satisfiable(condition, collected, solved)`: 검증기의 낙관적 도달 가능성 판정 (증거를 얻을 수 있으면 제시 가능, 신뢰도는 최대 3까지)

## 검증 규칙

| ID | 검사 | 심각도 |
|---|---|---|
| V01 | 모든 참조 ID 존재, 정답 동기·수법이 선택지에 있음 | error (대사 파일 누락은 warning). 오류가 있으면 이후 검사 생략 |
| V02 | 핵심 증거에 도달 가능 | error (그 외 증거는 warning) |
| V03 | 퍼즐 선행조건 순환 없음, 모든 퍼즐 도달 가능 | error |
| V04 | 퍼즐 단서를 만족하는 답이 정확히 하나이고 정답과 같음 | error |
| V05 | 퍼즐 없이 얻는 증거로 범인의 기회·수단·동기가 모두 입증되지 않음, 브리핑에 정답 사실 없음 | error |
| V06 | 모든 거짓말에 도달 가능한 반박 증거가 있음 | error |
| V07 | 모든 비밀의 공개 조건이 충족 가능 | error |
| T01 | 한 인물이 겹치는 시간에 두 장소에 있지 않음 | error |
| T02 | 증거가 기록한 시각·장소가 연결된 이벤트와 일치 | error |
| T03 | 연속 이벤트 사이 이동 시간이 충분함 (최단 경로) | error |
| U01 | 기회 ∧ 수단 ∧ 증거 체인을 모두 만족하는 용의자는 범인 하나뿐 | error (다른 용의자가 기회와 수단만 있으면 warning) |
| U02 | 핵심 증거를 모두 빼면 범인을 입증할 수 없음 | error (아무것도 입증하지 않는 핵심 증거는 warning) |
| L01 | LLM 비평 (인터페이스만 존재) | warning만 가능 |

**기회** 판정: 범행 시간 중 어느 1분이라도, 다른 장소 이벤트 중이 아니고 직전·다음 이벤트 장소와의 이동 시간이 맞으면 기회가 있다. 시간선에 기록이 없는 인물은 기회가 있다고 본다.

## 사용법

```bash
uv run case-validator check cases/museum-001          # 사람이 읽는 출력
uv run case-validator check cases/museum-001 --json   # JSON 출력
```

오류가 있으면 종료 코드 1을 반환한다.
