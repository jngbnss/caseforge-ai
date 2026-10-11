"""심문 프롬프트의 구획 표시. 프롬프트 빌더와 Mock 어댑터가 같은 값을 쓴다."""

NPC_ID_PREFIX = "NPC_ID: "
SECTION_FACTS = "## 알고 있는 사실"
SECTION_LIES = "## 유지해야 할 거짓말"
SECTION_EVIDENCE = "## 플레이어가 이 인물에게 제시한 증거"
QUESTION_OPEN = "<player_question>"
QUESTION_CLOSE = "</player_question>"

# 모순 판정 프롬프트 (evidence/llm_contradiction.py)
JUDGE_NEW_STATEMENT = "## 새 진술"
JUDGE_PREVIOUS = "## 이전 진술"
JUDGE_EVIDENCE = "## 제시된 증거"
JUDGE_CHECK = "## 모순으로 판정된 내용"
