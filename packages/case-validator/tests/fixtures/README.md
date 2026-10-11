# 망가뜨린 사건 fixture

각 `broken-*/patch.yaml`은 `cases/museum-001`을 복사한 뒤 적용할 변경만 담는다.
테스트(`conftest.materialize_fixture`)가 임시 디렉터리에 사건을 만들어 검증기를 돌리고,
실패한 규칙 ID 집합이 `expect`와 **정확히** 같은지 확인한다.

- `path`: `/`로 구분한다. 매핑은 키, 리스트는 정수 인덱스 또는 항목의 `*_id` 값으로 찾는다.
- `expect`에 둘 이상의 규칙이 있으면 의도한 연쇄 실패다 (주석으로 이유를 적는다).

CLI로 직접 보고 싶으면 `uv run python tests/materialize.py broken-t01 <출력 디렉터리>`.
