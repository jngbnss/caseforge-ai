# evals

museum-001 평가셋과 러너. 형식은 기획서 8절을 따른다.

```bash
uv run python -m evals.generate   # data/*.jsonl 다시 만들기 (결정론적: 같은 입력 → 같은 파일)
uv run python -m evals.schema     # 형식 · 건수 · ID 중복 검사
```

## 데이터 (`data/`)

| 파일 | 건수 | 구성 | 라벨을 정하는 방법 |
|---|---|---|---|
| `secret-leak-cases.jsonl` | 120 | 공격 8유형 × NPC 3 × 변형 5 | `forbidden_fact_ids` = 그 상태에서 그 NPC가 **말하면 안 되는** fact 전부: 범인 전용 사실, 아직 열리지 않은 자기 비밀·신뢰 조건 사실, 다른 NPC만 아는 사실. 실제 게임의 `build_scope`로 계산한다 |
| `evidence-grounding.jsonl` | 60 | NPC마다 정상 질문 20 | `allowed_fact_ids` = 그 상태의 스코프 전체. `must_cite` = 답에 쓰여야 할 fact (없으면 null). 생성기가 `must_cite`가 스코프 안에 있는지 확인한다 |
| `contradiction-cases.jsonl` | 40 | 양성 20 + 음성 20 | 사람이 쓴 진술. 양성은 Bible 거짓말을 바꿔 말한 것 12 + 진술끼리 충돌 8. 음성에는 4-5 실측에서 오탐이 난 진술 쌍 2건을 그대로 넣었다 |
| `deduction-cases.jsonl` | 40 | 정답 · 부분 정답 · 오답 · 증거 없는 정답 × 10 | 구조 점수는 생성기가 채점 규칙을 **따로 구현**해 계산하고, 테스트가 실제 채점기와 같은지 확인한다. `leaps`는 서술에 비약·근거 없는 문장을 일부러 넣었는지 여부 |

공격 유형: `direct`, `other_npc_secret`, `system_prompt`, `role_hijack`, `hypothetical`,
`unshown_evidence_lure`(보여 주지 않은 증거를 본 척), `multilingual_encoding`, `repeated_pressure`(`history`의 질문을 먼저 한다).
변형 1–3은 아무 증거도 없는 상태, 4는 비밀을 여는 증거를 그 NPC에게 보여 준 상태, 5는 모든 증거를 보여 주고 신뢰가 최대인 상태다.

## 한계

- 질문·진술·서술은 개발자가 쓴 것이다. 실제 플레이어 문장보다 정돈되어 있다.
- `deduction-cases`의 `leaps` 라벨은 문장을 만든 사람이 붙였다. 기획서의 "팀원 2명 독립 채점 → Cohen's κ"는 아직 하지 않았다.
- 사건이 하나(museum-001)뿐이라 다른 사건에 대한 일반화는 측정하지 못한다.

## 결과 (`results/`)

러너(`evals.run`)가 `results/<날짜>-<모델>.json`을 쓴다. 실험 기록(`docs/experiments.md`)에서 인용하는 결과 파일은 커밋한다.
