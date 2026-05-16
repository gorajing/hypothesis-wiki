from __future__ import annotations

import difflib
import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from critic import lint_claims, score_answer
from demo import DemoGraphState, compose_answer
from distillation_policy import should_distill
from distiller import distill, propose_skill_revision


ROOT = Path(__file__).resolve().parents[1]
DEMO_CARDS_PATH = ROOT / "data" / "demo_mlperf_cards.json"
AUDIT_DB_PATH = ROOT / "data" / "benchmark_claim_audit_db.json"
MLPERF_CARDS_PATH = ROOT / "data" / "mlperf_v5_1_cards.json"
SKILL_DIR = ROOT / "my_skills" / "hypothesis_distiller"
V1_PATH = SKILL_DIR / "SKILL.md"
PROPOSED_PATH = SKILL_DIR / "SKILL.proposed.md"

SCORE_KEYS = [
    ("retrieval_score", "Retrieval score", "higher"),
    ("hypothesis_hygiene", "Hypothesis hygiene", "higher"),
    ("scope_errors", "Scope errors", "lower"),
    ("contradictions_caught", "Contradictions caught", "higher"),
    ("retired_claims", "Retired claims", "higher"),
]


def build_observability_state() -> dict[str, Any]:
    """Build the complete read-only state projection consumed by the UI.

    The browser receives precomputed scores, deltas, decisions, and source-span
    previews. It should not derive science metrics or provenance matches.
    """
    demo_cards = _read_json(DEMO_CARDS_PATH)
    v1_skill = V1_PATH.read_text()

    graph1 = DemoGraphState()
    run1_candidates = _run_distillation_pass(demo_cards, v1_skill, graph1, "run_001")
    run1_answer = compose_answer(graph1)
    run1_score = score_answer(run1_answer, graph1)
    run1_lint = lint_claims([entry["candidate"] for entry in run1_candidates])

    feedback = _rejection_feedback(run1_candidates) + list(run1_score.notes)
    proposed_skill = propose_skill_revision(feedback)

    graph2 = DemoGraphState()
    run2_candidates = _run_distillation_pass(demo_cards, proposed_skill, graph2, "run_002")
    _retire_broad_claims(graph2)
    run2_answer = compose_answer(graph2)
    run2_score = score_answer(run2_answer, graph2)
    run2_lint = lint_claims([entry["candidate"] for entry in run2_candidates])

    score_rows = _score_rows(run1_score, run2_score)
    provenance = _provenance_state()

    return {
        "meta": {
            "project": "Benchmark Claim Wiki",
            "state_source": "read-only backend projection",
            "served_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "api_endpoint": "/api/state",
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "session_backend": "RedisSessionStore",
            "cognee_dataset": os.getenv("COGNEE_DATASET", "benchmark-claim-wiki-trusted"),
            "graph_backend": "CogneeTrustedGraphStore",
        },
        "research_question": (
            "Can the top MLPerf Offline Llama2 result be generalized to all serving workloads?"
        ),
        "runs": {
            "run_001": _run_state(
                run_id="run_001",
                label="Run 1",
                skill_name="SKILL.md / v1",
                skill_text=v1_skill,
                graph=graph1,
                candidates=run1_candidates,
                answer=run1_answer,
                score=run1_score,
                lint_issues=run1_lint,
                score_rows=score_rows,
            ),
            "run_002": _run_state(
                run_id="run_002",
                label="Run 2",
                skill_name="SKILL.proposed.md / applied",
                skill_text=proposed_skill,
                graph=graph2,
                candidates=run2_candidates,
                answer=run2_answer,
                score=run2_score,
                lint_issues=run2_lint,
                score_rows=score_rows,
            ),
        },
        "self_improvement": {
            "feedback_count": len(feedback),
            "feedback": feedback,
            "proposed_skill_path": str(PROPOSED_PATH.relative_to(ROOT)),
            "proposed_rules": _numbered_rules(proposed_skill),
            "skill_diff": _skill_diff(v1_skill, proposed_skill),
        },
        "before_after": score_rows,
        "provenance": provenance,
    }


def _run_distillation_pass(
    cards: list[dict[str, Any]],
    skill_text: str,
    graph: DemoGraphState,
    session_id: str,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for card in cards:
        graph.remember(card, session_id=session_id)
        claim = distill(card, skill_text)
        graph.remember(claim, session_id=session_id)
        decision = should_distill(claim, graph)
        trusted_claim = None
        if decision.promote:
            trusted_claim = {
                **claim,
                "status": "trusted",
                "distill_reason": decision.reason,
                "distill_confidence": decision.confidence,
            }
            graph.remember(trusted_claim)
        entries.append(
            {
                "source_card": _source_card_view(card),
                "candidate": _claim_view(claim),
                "decision": asdict(decision),
                "trusted_claim": _claim_view(trusted_claim) if trusted_claim else None,
            }
        )
    return entries


def _run_state(
    *,
    run_id: str,
    label: str,
    skill_name: str,
    skill_text: str,
    graph: DemoGraphState,
    candidates: list[dict[str, Any]],
    answer: str,
    score: Any,
    lint_issues: list[dict[str, Any]],
    score_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": run_id,
        "label": label,
        "skill_name": skill_name,
        "skill_text": skill_text,
        "answer": answer,
        "score": _score_dict(score),
        "scorecard_rows": [
            {**row, "current": row["run_1"] if run_id == "run_001" else row["run_2"]}
            for row in score_rows
        ],
        "notes": list(score.notes),
        "lint_issues": list(lint_issues),
        "pipeline": candidates,
        "trusted_graph": {
            "claims": [_claim_view(claim) for claim in graph.trusted_graph],
            "retirements": list(graph.retirements),
            "contradictions": _contradictions(graph),
            "counts": {
                "redis_session_events": len(graph.redis_session),
                "trusted_claims": len(graph.trusted_graph),
                "retired_claims": len(graph.retirements),
                "contradictions": score.contradictions_caught,
            },
        },
        "redis_session": [_session_event_view(event) for event in graph.redis_session],
    }


def _retire_broad_claims(graph: DemoGraphState) -> None:
    positive_outcomes = {
        c["outcome"]
        for c in graph.trusted_graph
        if c.get("kind") == "hypothesis" and c.get("direction") == "improves"
    }
    for claim in list(graph.trusted_graph):
        contradicts = next(
            (
                evidence
                for evidence in graph.trusted_graph
                if evidence.get("outcome") in positive_outcomes
                and (
                    evidence.get("kind") == "negative_result"
                    or (
                        evidence.get("kind") == "evidence"
                        and evidence.get("direction") in {"conditional", "no_benefit"}
                    )
                )
            ),
            None,
        )
        if claim.get("kind") == "hypothesis" and claim.get("direction") == "improves" and contradicts:
            graph.retire(claim["id"], "broad claim narrowed by later evidence", contradicts["id"])
            break


def _provenance_state() -> dict[str, Any]:
    audit_db = _read_json(AUDIT_DB_PATH)
    source_cards = _read_json(MLPERF_CARDS_PATH)
    source_by_id = {card["paper_id"]: card for card in source_cards}

    trusted_claims = []
    for record in audit_db["records"]:
        source_card = source_by_id[record["paper_id"]]
        source_text = source_card["source_text"]
        start = record["evidence_start"]
        end = record["evidence_end"]
        trusted_claims.append(
            {
                "claim_id": record["claim_id"],
                "paper_id": record["paper_id"],
                "title": record["paper_title"],
                "source_url": record["source_url"],
                "kind": record["kind"],
                "audit_verdict": record["audit_verdict"],
                "text": record["text"],
                "outcome": record["outcome"],
                "direction": record["direction"],
                "scope_conditions": list(record["scope_conditions"]),
                "confidence": record["confidence"],
                "promotion_status": record["promotion_status"],
                "promotion_reason": record["promotion_reason"],
                "promotion_confidence": record["promotion_confidence"],
                "evidence_span": record["evidence_span"],
                "evidence_start": start,
                "evidence_end": end,
                "evidence_span_valid": record["evidence_span_valid"],
                "source_preview": {
                    "before": source_text[:start],
                    "highlight": source_text[start:end],
                    "after": source_text[end:],
                },
            }
        )

    return {
        "database_name": audit_db["database_name"],
        "version": audit_db["version"],
        "description": audit_db["description"],
        "summary": audit_db["summary"],
        "source_cards": source_cards,
        "trusted_claims": trusted_claims,
        "demo_queries": audit_db["demo_queries"],
    }


def _source_card_view(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": card["paper_id"],
        "title": card["title"],
        "year": card.get("year"),
        "url": card.get("url"),
        "finding": card.get("finding"),
        "conditions": list(card.get("conditions", [])),
        "outcome": card.get("outcome"),
        "direction": card.get("direction"),
        "result_type": card.get("result_type"),
    }


def _claim_view(claim: dict[str, Any] | None) -> dict[str, Any] | None:
    if claim is None:
        return None
    keys = [
        "id",
        "kind",
        "text",
        "source",
        "source_url",
        "scope_conditions",
        "outcome",
        "direction",
        "evidence_type",
        "status",
        "confidence",
        "distill_reason",
        "distill_confidence",
    ]
    return {key: claim.get(key) for key in keys if key in claim}


def _session_event_view(event: dict[str, Any]) -> dict[str, Any]:
    payload = event["payload"]
    event_id = payload.get("id") or payload.get("paper_id")
    if payload.get("paper_id"):
        kind = "source_card"
        summary = payload.get("finding") or payload.get("title")
    else:
        kind = payload.get("kind", "candidate")
        summary = payload.get("text")
    return {
        "session_id": event["session_id"],
        "id": event_id,
        "kind": kind,
        "summary": summary,
    }


def _contradictions(graph: DemoGraphState) -> list[dict[str, str]]:
    positive_claims = [
        claim
        for claim in graph.trusted_graph
        if claim.get("kind") == "hypothesis" and claim.get("direction") == "improves"
    ]
    rows: list[dict[str, str]] = []
    for positive in positive_claims:
        for evidence in graph.trusted_graph:
            if evidence.get("id") == positive.get("id"):
                continue
            if evidence.get("outcome") != positive.get("outcome"):
                continue
            kind = evidence.get("kind")
            if kind == "negative_result" or (
                kind == "evidence" and evidence.get("direction") in {"conditional", "no_benefit"}
            ):
                rows.append(
                    {
                        "claim_id": positive["id"],
                        "evidence_id": evidence["id"],
                        "reason": "same outcome undercuts universal offline-to-serving generalization",
                    }
                )
    return rows


def _score_dict(score: Any) -> dict[str, Any]:
    return {
        "retrieval_score": score.retrieval_score,
        "hypothesis_hygiene": score.hypothesis_hygiene,
        "scope_errors": score.scope_errors,
        "contradictions_caught": score.contradictions_caught,
        "retired_claims": score.retired_claims,
        "notes": list(score.notes),
    }


def _score_rows(run1_score: Any, run2_score: Any) -> list[dict[str, Any]]:
    rows = []
    run1 = _score_dict(run1_score)
    run2 = _score_dict(run2_score)
    for key, label, direction in SCORE_KEYS:
        before = run1[key]
        after = run2[key]
        rows.append(
            {
                "key": key,
                "label": label,
                "run_1": _format_score_value(before),
                "run_2": _format_score_value(after),
                "display": f"{_format_score_value(before)} -> {_format_score_value(after)}",
                "tone": _delta_tone(before, after, direction),
            }
        )
    return rows


def _delta_tone(before: int | float, after: int | float, direction: str) -> str:
    if before == after:
        return "flat"
    improved = after > before if direction == "higher" else after < before
    return "improved" if improved else "regressed"


def _format_score_value(value: int | float) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _rejection_feedback(candidates: list[dict[str, Any]]) -> list[str]:
    return [
        f"{entry['candidate']['id']}: {entry['decision']['reason']}"
        for entry in candidates
        if not entry["decision"]["promote"]
    ]


def _numbered_rules(skill_text: str) -> list[str]:
    return [
        line.strip()
        for line in skill_text.splitlines()
        if line.strip()[:1] in {"1", "2", "3", "4", "5"}
    ]


def _skill_diff(old_skill: str, new_skill: str) -> list[dict[str, str]]:
    rows = []
    for row in difflib.ndiff(old_skill.splitlines(), new_skill.splitlines()):
        marker = row[:2]
        if marker == "? ":
            continue
        rows.append(
            {
                "kind": {"- ": "removed", "+ ": "added", "  ": "same"}.get(marker, "same"),
                "text": row[2:],
            }
        )
    return rows


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())

