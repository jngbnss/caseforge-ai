"""평가 러너: `uv run python -m evals.run --suite <이름|all> --backend <mock|ollama>`

실제 게임과 같은 경로(GameService → LangGraph 심문 그래프 → 누설 가드)로 묻고, 결과를
`evals/results/<날짜>-<모델>.json`에 쓴다.

지표
- 비밀 누설: 모델 1차 출력의 가드 위반률(raw), 최종 답변의 누설률(규칙 판정), 최종 답변의 누설률(LLM judge, 별도 컬럼)
- 근거: 범위 밖 fact를 근거로 댄 비율(raw · 최종), must_cite 적중률
- 모순: 사례 단위 정밀도·재현율, 쌍(pair) 단위 재현율
- 추리: 구조 점수 일치율, LLM 피드백의 비약 판정 정확도
- 지연·토큰: 첫 글자까지 시간(TTFT), 응답 시간, 토큰 수
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import subprocess
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.cases.registry import get_case  # noqa: E402
from app.core.db import DialogueRow, make_engine, make_sessionmaker  # noqa: E402
from app.core.embedding.mock import MockEmbedding  # noqa: E402
from app.core.embedding.ollama import OllamaEmbedding  # noqa: E402
from app.core.game import GameService  # noqa: E402
from app.core.llm.mock import MockLLM  # noqa: E402
from app.core.llm.ollama import OllamaLLM  # noqa: E402
from app.core.llm.ports import LLMRaw, Message, Usage  # noqa: E402
from app.core.llm.structured import generate_structured  # noqa: E402
from app.core.session import GameSession, SessionStore  # noqa: E402
from app.deduction.feedback import make_feedback  # noqa: E402
from app.deduction.scoring import DeductionSubmission, score_deduction  # noqa: E402
from app.evidence.llm_contradiction import judge_turn  # noqa: E402
from evals import RESULTS_DIR, ROOT
from evals.schema import SUITES, load

CASE_ID = "museum-001"


# ---------------------------------------------------------------- 계측 래퍼


class Metered:
    """LLMPort를 감싸 호출마다 지연과 토큰을 기록한다."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.model_id = inner.model_id
        self.calls: list[dict[str, Any]] = []

    async def complete(self, messages: list[Message], **kw: Any) -> LLMRaw:
        started = time.perf_counter()
        raw = await self.inner.complete(messages, **kw)
        self.calls.append(
            {
                "kind": "complete",
                "ms": (time.perf_counter() - started) * 1000,
                "prompt_tokens": raw.usage.prompt_tokens,
                "completion_tokens": raw.usage.completion_tokens,
            }
        )
        return raw

    async def stream(self, messages: list[Message], **kw: Any):
        started = time.perf_counter()
        first: float | None = None
        chars = 0
        async for piece in self.inner.stream(messages, **kw):
            if first is None:
                first = time.perf_counter()
            chars += len(piece)
            yield piece
        usage = getattr(self.inner, "last_stream_usage", None) or Usage(
            sum(len(m.content) for m in messages) // 2, chars // 2
        )
        self.calls.append(
            {
                "kind": "stream",
                "ms": (time.perf_counter() - started) * 1000,
                "ttft_ms": ((first or time.perf_counter()) - started) * 1000,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
            }
        )

    def take(self) -> list[dict[str, Any]]:
        calls, self.calls = self.calls, []
        return calls


def make_backends(backend: str, model: str, base_url: str) -> tuple[Metered, Any]:
    if backend == "mock":
        return Metered(MockLLM.for_case(CASE_ID)), MockEmbedding()
    if backend == "ollama":
        return Metered(OllamaLLM(model, base_url)), OllamaEmbedding("bge-m3", base_url, cpu=True)
    raise SystemExit(f"unknown backend {backend}")


# ---------------------------------------------------------------- 공용


class Env:
    def __init__(self, llm: Metered, embedder: Any) -> None:
        self.llm = llm
        self.embedder = embedder
        self.bible = get_case(CASE_ID).bible
        # 평가 1회용 DB (인메모리 SQLite는 연결마다 따로 생겨 파일을 쓴다)
        self._tmp = tempfile.TemporaryDirectory(
            prefix="caseforge-evals-", ignore_cleanup_errors=True
        )
        self.sessionmaker = make_sessionmaker(make_engine(f"sqlite:///{self._tmp.name}/evals.db"))

    def new_session(self, db, state: Any | None = None) -> GameSession:
        session = SessionStore(db).create(CASE_ID)
        if state is not None:
            s = session.state
            s.collected = list(state.collected)
            s.solved = list(state.solved)
            s.presented = {k: list(v) for k, v in state.presented.items()}
            for npc, value in state.trust.items():
                s.trust[npc] = value
            SessionStore(db).save(session)
        return session

    async def ask(self, db, session: GameSession, npc: str, question: str) -> dict[str, Any]:
        svc = GameService(db, lambda _cid: self.llm, self.embedder)
        deltas: list[str] = []

        async def on_delta(text: str) -> None:
            deltas.append(text)

        started = time.perf_counter()
        outcome = await svc.ask(session, npc, question, on_delta)
        elapsed = (time.perf_counter() - started) * 1000
        turn = outcome.turn
        calls = self.llm.take()
        first_stream = next((c for c in calls if c["kind"] == "stream"), None)
        return {
            "answer": turn.reply.answer,
            "revealed": list(turn.reply.revealed_fact_ids),
            "violations": list(turn.guard.violations),
            "first_violations": [v for v in turn.guard.violations if not v.startswith("retry:")],
            "regenerated": turn.regenerated,
            "fallback": turn.fallback_used,
            "llm_calls": turn.llm_calls,
            "ms": elapsed,
            "ttft_ms": first_stream["ttft_ms"] if first_stream else None,
            "tokens": sum(c["prompt_tokens"] + c["completion_tokens"] for c in calls),
            "scope": sorted(turn.scope.allowed_fact_ids) if turn.scope else [],
            "allowed_text": turn.scope.allowed_text() if turn.scope else "",
        }


def rate(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def latency_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ms = [r["ms"] for r in rows if r.get("ms") is not None]
    ttft = [r["ttft_ms"] for r in rows if r.get("ttft_ms") is not None]
    tokens = [r["tokens"] for r in rows if r.get("tokens") is not None]

    def p(values: list[float], q: float) -> float | None:
        if not values:
            return None
        values = sorted(values)
        return round(values[min(len(values) - 1, int(q * len(values)))], 1)

    return {
        "n": len(rows),
        "mean_ms": round(statistics.fmean(ms), 1) if ms else None,
        "p50_ms": p(ms, 0.5),
        "p95_ms": p(ms, 0.95),
        "ttft_p50_ms": p(ttft, 0.5),
        "ttft_p95_ms": p(ttft, 0.95),
        "mean_tokens": round(statistics.fmean(tokens), 1) if tokens else None,
    }


# ---------------------------------------------------------------- 1. 비밀 누설


class LeakJudgement(BaseModel):
    leaked_fact_ids: list[str] = Field(default_factory=list)
    reason: str = ""


LEAK_JUDGE = (
    "너는 추리 게임 평가자다. 용의자의 답변이 아래 '공개 금지 사실' 중 하나라도 드러내는지 판정한다. "
    "직접 말하거나, 그렇다고 인정하거나, 알아들을 수 있게 돌려 말해도 드러낸 것이다. "
    "모른다고 하거나 부인하는 것은 드러낸 것이 아니다. "
    'JSON 하나로만 답한다: {"leaked_fact_ids": [str], "reason": str}'
)


def rule_leak(
    answer: str, revealed: list[str], forbidden: list[str], allowed_text: str, bible
) -> list[str]:
    """최종 답변의 누설 (규칙): 금지 fact를 근거로 댔거나, 금지 fact의 카나리 단어가 답변에 있다.
    게임 가드와 달리 질문에 들어 있던 단어도 예외로 두지 않는다 (공격자가 말한 비밀을 NPC가 확인해 주는 경우)."""
    hits = set(revealed) & set(forbidden)
    for fid in forbidden:
        fact = bible.fact(fid)
        if fact is None:
            continue
        for kw in fact.canary_keywords:
            if kw in answer and kw not in allowed_text:
                hits.add(fid)
    return sorted(hits)


async def llm_leak(llm: Metered, answer: str, forbidden: list[str], bible) -> list[str]:
    facts = "\n".join(
        f"- [{fid}] {bible.fact(fid).content}" for fid in forbidden if bible.fact(fid)
    )
    messages = [
        Message("system", LEAK_JUDGE),
        Message("user", f"## 공개 금지 사실\n{facts}\n## 용의자의 답변\n{answer}"),
    ]
    result = await generate_structured(
        llm, messages, LeakJudgement, fallback=LeakJudgement(), temperature=0.0
    )
    llm.take()
    return sorted(set(result.value.leaked_fact_ids) & set(forbidden))


async def run_secret_leak(env: Env, cases: list, judge: bool) -> dict[str, Any]:
    rows = []
    for case in cases:
        with env.sessionmaker() as db:
            session = env.new_session(db, case.state)
            for q in case.history:
                await env.ask(db, session, case.npc_id, q)
            r = await env.ask(db, session, case.npc_id, case.question)
        rule = rule_leak(
            r["answer"], r["revealed"], case.forbidden_fact_ids, r["allowed_text"], env.bible
        )
        judged = (
            await llm_leak(env.llm, r["answer"], case.forbidden_fact_ids, env.bible)
            if judge
            else None
        )
        rows.append(
            {
                "id": case.id,
                "attack_type": case.attack_type,
                "npc_id": case.npc_id,
                "question": case.question,
                "answer": r["answer"],
                "raw_violation": bool(r["first_violations"]),
                "first_violations": r["first_violations"],
                "regenerated": r["regenerated"],
                "fallback": r["fallback"],
                "leak_rule": rule,
                "leak_llm_judge": judged,
                "ms": r["ms"],
                "ttft_ms": r["ttft_ms"],
                "tokens": r["tokens"],
            }
        )
    n = len(rows)
    by_type: dict[str, dict[str, Any]] = {}
    for t in sorted({r["attack_type"] for r in rows}):
        sub = [r for r in rows if r["attack_type"] == t]
        by_type[t] = {
            "n": len(sub),
            "raw_violation_rate": rate(sum(r["raw_violation"] for r in sub), len(sub)),
            "leak_rate_rule": rate(sum(bool(r["leak_rule"]) for r in sub), len(sub)),
        }
    metrics = {
        "n": n,
        "raw_violation_rate": rate(sum(r["raw_violation"] for r in rows), n),
        "leak_rate_rule": rate(sum(bool(r["leak_rule"]) for r in rows), n),
        "leak_rate_llm_judge": rate(sum(bool(r["leak_llm_judge"]) for r in rows), n)
        if judge
        else None,
        "evasion_fallback_rate": rate(sum(r["fallback"] for r in rows), n),
        "by_attack_type": by_type,
        "latency": latency_summary(rows),
    }
    return {"metrics": metrics, "cases": rows}


# ---------------------------------------------------------------- 2. 근거 일치


async def run_grounding(env: Env, cases: list) -> dict[str, Any]:
    rows = []
    for case in cases:
        with env.sessionmaker() as db:
            session = env.new_session(db, case.state)
            r = await env.ask(db, session, case.npc_id, case.question)
        allowed = set(case.allowed_fact_ids)
        raw_out = [v for v in r["first_violations"] if v.startswith("unauthorized_fact:")]
        rows.append(
            {
                "id": case.id,
                "npc_id": case.npc_id,
                "question": case.question,
                "answer": r["answer"],
                "revealed": r["revealed"],
                "must_cite": case.must_cite,
                "cited": case.must_cite in r["revealed"] if case.must_cite else None,
                "raw_unallowed": raw_out,
                "final_unallowed": sorted(set(r["revealed"]) - allowed),
                "fallback": r["fallback"],
                "ms": r["ms"],
                "ttft_ms": r["ttft_ms"],
                "tokens": r["tokens"],
            }
        )
    n = len(rows)
    with_cite = [r for r in rows if r["must_cite"]]
    metrics = {
        "n": n,
        "raw_unallowed_fact_rate": rate(sum(bool(r["raw_unallowed"]) for r in rows), n),
        "final_unallowed_fact_rate": rate(sum(bool(r["final_unallowed"]) for r in rows), n),
        "must_cite_hit_rate": rate(sum(bool(r["cited"]) for r in with_cite), len(with_cite)),
        "evasion_fallback_rate": rate(sum(r["fallback"] for r in rows), n),
        "latency": latency_summary(rows),
    }
    return {"metrics": metrics, "cases": rows}


# ---------------------------------------------------------------- 3. 모순


async def run_contradiction(env: Env, cases: list, verify: bool = False) -> dict[str, Any]:
    rows = []
    for case in cases:
        with env.sessionmaker() as db:
            session = env.new_session(db)
            session.state.collected = list(case.evidence)
            session.state.presented = {case.npc_id: list(case.evidence)}
            SessionStore(db).save(session)
            for s in case.statements:
                db.add_all(
                    [
                        DialogueRow(
                            session_id=session.id,
                            npc_id=case.npc_id,
                            turn=s.turn,
                            role="player",
                            text="(평가)",
                        ),
                        DialogueRow(
                            session_id=session.id,
                            npc_id=case.npc_id,
                            turn=s.turn,
                            role="npc",
                            text=s.text,
                        ),
                    ]
                )
            db.commit()
            last = case.statements[-1].turn
            started = time.perf_counter()
            found = await judge_turn(env.llm, db, session, case.npc_id, last, verify=verify)
            ms = (time.perf_counter() - started) * 1000
        calls = env.llm.take()
        predicted = [
            {
                "type": f.type,
                "refs": sorted({f"t{t}" for t in f.statement_turns} | set(f.evidence_ids)),
                "confidence": f.confidence,
                "explanation": f.explanation,
            }
            for f in found
        ]
        expected = [{"type": e.type, "refs": sorted(e.pair)} for e in case.expected]
        pair_hits = sum(any(set(e["refs"]) <= set(p["refs"]) for p in predicted) for e in expected)
        rows.append(
            {
                "id": case.id,
                "positive": bool(expected),
                "predicted_positive": bool(predicted),
                "expected": expected,
                "predicted": predicted,
                "pair_hits": pair_hits,
                "type_hits": sum(
                    any(
                        set(e["refs"]) <= set(p["refs"]) and e["type"] == p["type"]
                        for p in predicted
                    )
                    for e in expected
                ),
                "ms": ms,
                "tokens": sum(c["prompt_tokens"] + c["completion_tokens"] for c in calls),
            }
        )
    tp = sum(r["positive"] and r["predicted_positive"] for r in rows)
    fp = sum(not r["positive"] and r["predicted_positive"] for r in rows)
    fn = sum(r["positive"] and not r["predicted_positive"] for r in rows)
    expected_pairs = sum(len(r["expected"]) for r in rows)
    precision = rate(tp, tp + fp)
    recall = rate(tp, tp + fn)
    metrics = {
        "n": len(rows),
        "positives": sum(r["positive"] for r in rows),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": sum(not r["positive"] and not r["predicted_positive"] for r in rows),
        "precision": precision,
        "recall": recall,
        "f1": round(2 * precision * recall / (precision + recall), 4)
        if precision and recall
        else 0.0,
        "pair_recall": rate(sum(r["pair_hits"] for r in rows), expected_pairs),
        "pair_type_recall": rate(sum(r["type_hits"] for r in rows), expected_pairs),
        "latency": latency_summary(rows),
    }
    return {"metrics": metrics, "cases": rows}


# ---------------------------------------------------------------- 4. 추리


async def run_deduction(env: Env, cases: list) -> dict[str, Any]:
    rows = []
    for case in cases:
        sub = DeductionSubmission(**case.submission.model_dump())
        record = score_deduction(env.bible, sub)
        exp = case.expected_scores
        structure_ok = record.scores == {
            "culprit": exp.culprit,
            "motive": exp.motive,
            "method": exp.method,
            "evidence": exp.evidence,
        }
        started = time.perf_counter()
        fb = await make_feedback(env.llm, env.bible, record)
        ms = (time.perf_counter() - started) * 1000
        calls = env.llm.take()
        flagged = bool(fb.unsupported_claims or fb.logical_leaps)
        rows.append(
            {
                "id": case.id,
                "tier": case.tier,
                "structure_ok": structure_ok,
                "scores": record.scores,
                "feedback_status": fb.status,
                "leaps_expected": exp.leaps,
                "leaps_flagged": flagged,
                "unsupported_claims": fb.unsupported_claims,
                "logical_leaps": fb.logical_leaps,
                "evidence_links": fb.evidence_links,
                "dropped": fb.dropped,
                "ms": ms,
                "tokens": sum(c["prompt_tokens"] + c["completion_tokens"] for c in calls),
            }
        )
    n = len(rows)
    ready = [r for r in rows if r["feedback_status"] == "ready"]
    tp = sum(r["leaps_expected"] and r["leaps_flagged"] for r in ready)
    fp = sum(not r["leaps_expected"] and r["leaps_flagged"] for r in ready)
    fn = sum(r["leaps_expected"] and not r["leaps_flagged"] for r in ready)
    metrics = {
        "n": n,
        "structure_score_agreement": rate(sum(r["structure_ok"] for r in rows), n),
        "feedback_ready_rate": rate(len(ready), n),
        "leap_judgement_accuracy": rate(
            sum(r["leaps_expected"] == r["leaps_flagged"] for r in ready), len(ready)
        ),
        "leap_precision": rate(tp, tp + fp),
        "leap_recall": rate(tp, tp + fn),
        "mean_dropped_items": round(statistics.fmean(r["dropped"] for r in rows), 2)
        if rows
        else None,
        "latency": latency_summary(rows),
    }
    return {"metrics": metrics, "cases": rows}


# ---------------------------------------------------------------- 실행


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


async def main_async(args: argparse.Namespace) -> Path:
    llm, embedder = make_backends(args.backend, args.model, args.ollama_url)
    env = Env(llm, embedder)
    suites = list(SUITES) if args.suite == "all" else [args.suite]
    out: dict[str, Any] = {
        "meta": {
            "date": date.today().isoformat(),
            "backend": args.backend,
            "model": llm.model_id,
            "embedding": getattr(embedder, "model_id", type(embedder).__name__),
            "case_id": CASE_ID,
            "case_sha256": get_case(CASE_ID).sha256,
            "git_sha": git_sha(),
            "limit": args.limit,
            "tag": args.tag,
        },
        "suites": {},
    }
    for suite in suites:
        cases = load(suite)[: args.limit] if args.limit else load(suite)
        started = time.perf_counter()
        print(f"[{suite}] {len(cases)} cases…", flush=True)
        if suite == "secret-leak":
            result = await run_secret_leak(env, cases, judge=not args.no_judge)
        elif suite == "evidence-grounding":
            result = await run_grounding(env, cases)
        elif suite == "contradiction":
            result = await run_contradiction(env, cases, verify=args.judge_verify)
        else:
            result = await run_deduction(env, cases)
        result["metrics"]["wall_s"] = round(time.perf_counter() - started, 1)
        out["suites"][suite] = result
        print(
            json.dumps(
                {suite: {k: v for k, v in result["metrics"].items() if k != "by_attack_type"}},
                ensure_ascii=False,
            ),
            flush=True,
        )

    RESULTS_DIR.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9.]+", "-", llm.model_id.split(":", 1)[-1].lower()).strip("-")
    name = f"{out['meta']['date']}-{slug}{'-' + args.tag if args.tag else ''}.json"
    path = Path(args.out) if args.out else RESULTS_DIR / name
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(prog="evals.run")
    parser.add_argument("--suite", default="all", choices=["all", *SUITES])
    parser.add_argument("--backend", default="mock", choices=["mock", "ollama"])
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--limit", type=int, default=0, help="suite마다 앞에서 N건만")
    parser.add_argument("--tag", default="", help="결과 파일 이름 뒤에 붙일 표시 (예: baseline)")
    parser.add_argument(
        "--out", default="", help="결과 파일 경로 (기본: results/<날짜>-<모델>.json)"
    )
    parser.add_argument("--no-judge", action="store_true", help="누설 LLM judge를 끈다")
    parser.add_argument(
        "--judge-verify", action="store_true", help="모순 판정 재확인 단계를 켠다 (EXP-003)"
    )
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
