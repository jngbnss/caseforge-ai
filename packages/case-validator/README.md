# case-validator

CaseForge AI 사건 데이터(Case Bible)의 Pydantic 스키마, YAML 로더, 규칙·그래프 검증기.
LLM을 쓰지 않는 결정론적 검사만 수행한다.

```bash
uv run case-validator check cases/museum-001          # 사람이 읽는 리포트
uv run case-validator check cases/museum-001 --json   # ValidationReport JSON
```

오류가 하나라도 있으면 종료 코드 1을 반환한다. 규칙 목록과 필드 설명은 `docs/case-schema.md`를 본다.

```python
from case_validator import load_case, validate

loaded = load_case("cases/museum-001")
report = validate(loaded.bible)
print(loaded.sha256, report.ok)
```
