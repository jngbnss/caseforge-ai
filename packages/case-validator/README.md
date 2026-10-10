# case-validator

구조화된 추리 사건(Case Bible)을 검사하는 독립 라이브러리.

- 스키마 검증 (Pydantic v2)
- 참조 무결성, 증거 발견 가능성, 퍼즐 선행조건 순환, 퍼즐 정답 유일성
- 시간선 충돌, 증거-시간선 일치, 이동 가능성 (NetworkX)
- 유일 범인, 핵심 증거 필요성

```bash
case-validator check cases/museum-001
```

오류가 하나라도 있으면 종료 코드 1을 반환한다. 규칙 목록은 `docs/case-schema.md`에 있다.
