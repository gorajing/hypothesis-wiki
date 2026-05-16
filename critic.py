from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreBreakdown:
    retrieval_score: float
    hypothesis_hygiene: float
    scope_errors: int
    contradictions_caught: int
    retired_claims: int
    notes: list[str]


def _trusted_positive_outcomes(graph) -> set[str]:
    return {
        c.get("outcome")
        for c in graph.trusted_graph
        if c.get("kind") == "hypothesis" and c.get("direction") == "improves"
    }


def _count_contradictions(graph) -> int:
    """A trusted claim contradicts the wiki when it undercuts a promoted
    positive hypothesis on the same outcome (negative result, or conditional/
    no-benefit evidence). Derived from graph state, never from a flag."""
    positive_outcomes = _trusted_positive_outcomes(graph)
    count = 0
    for claim in graph.trusted_graph:
        if claim.get("outcome") not in positive_outcomes:
            continue
        kind = claim.get("kind")
        if kind == "negative_result":
            count += 1
        elif kind == "evidence" and claim.get("direction") in {"conditional", "no_benefit"}:
            count += 1
    return count


def _has_scoped_trusted_claims(graph) -> bool:
    return any(c.get("scope_conditions") for c in graph.trusted_graph)


def score_answer(answer: str, graph) -> ScoreBreakdown:
    """Score an answer against the trusted graph it should be grounded in.

    Every metric is computed from real graph state (promoted claims +
    retirements) and the answer text. There is no caller-supplied
    'improved' switch: a cautious answer scores well only if the graph
    actually contains the scope/negative evidence it reflects.
    """
    text = answer.lower()
    notes: list[str] = []

    has_scope = (
        "mlperf" in text
        and "offline" in text
        and "server" in text
        and ("mi325x" in text or "mi300x" in text)
    )
    has_negative = any(
        term in text
        for term in ["not general", "do not generalize", "lower", "scenario-specific", "separate"]
    )
    overclaims = "all llama2 serving workloads" in text and "not" not in text

    contradictions = _count_contradictions(graph)
    retired = len(graph.retirements)
    grounded_in_graph = len(graph.trusted_graph) > 0

    scope_errors = 0
    if not grounded_in_graph:
        scope_errors += 1
        notes.append("answer not grounded in any trusted claim")
    if _has_scoped_trusted_claims(graph) and not has_scope:
        scope_errors += 1
        notes.append("missing scope conditions present in trusted claims")
    if contradictions > 0 and not has_negative:
        scope_errors += 1
        notes.append("omitted negative/contradicting evidence in the trusted graph")
    if overclaims:
        notes.append("overclaimed offline throughput for serving workloads")

    addresses_question = "llama2" in text or "mlperf" in text
    if not grounded_in_graph:
        # Vacuous-truth guard: an answer with no trusted backing earns no
        # scope/negative credit just because the graph is empty.
        scope_ok = 0.0
        negative_ok = 0.0
    else:
        scope_ok = 1.0 if (has_scope or not _has_scoped_trusted_claims(graph)) else 0.0
        negative_ok = 1.0 if (has_negative or contradictions == 0) else 0.0
    no_overclaim = 0.0 if overclaims else 1.0
    hygiene = (
        0.15 * (1.0 if addresses_question else 0.0)
        + 0.35 * scope_ok
        + 0.35 * negative_ok
        + 0.15 * no_overclaim
    )

    total = len(graph.trusted_graph)
    grounded = sum(
        1
        for c in graph.trusted_graph
        if str(c.get("source", "")) in answer
        or any(w in text for w in str(c.get("outcome", "")).split())
    )
    # Deliberately flat-ish: a cautious answer must not look like it
    # "retrieved less" (DATA_CONTRACTS.md). Coverage nudges, never collapses.
    retrieval = round(min(1.0, 0.70 + 0.30 * (grounded / total if total else 0.0)), 2)

    return ScoreBreakdown(
        retrieval_score=retrieval,
        hypothesis_hygiene=round(hygiene, 2),
        scope_errors=scope_errors,
        contradictions_caught=contradictions,
        retired_claims=retired,
        notes=notes,
    )


def lint_claims(claims: list[dict]) -> list[dict]:
    issues: list[dict] = []
    for claim in claims:
        if not claim.get("source"):
            issues.append({"code": "missing_source", "claim": claim.get("id"), "severity": "error"})
        if claim.get("kind") == "hypothesis" and not claim.get("scope_conditions"):
            issues.append({"code": "missing_scope", "claim": claim.get("id"), "severity": "error"})
    return issues
