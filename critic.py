from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreBreakdown:
    retrieval_score: float
    hypothesis_hygiene: float
    scope_errors: int
    contradictions_caught: int
    retired_claims: int
    notes: list[str]


def score_answer(answer: str, *, improved: bool) -> ScoreBreakdown:
    text = answer.lower()
    notes: list[str] = []

    has_scope = ("below 40c" in text or "25c" in text) and "e1" in text
    has_negative = any(term in text for term in ["negative", "no benefit", "degradation", "non-replicating"])
    avoids_high_temp_overclaim = not ("should be used for high-temperature" in text and "not" not in text)

    scope_errors = 0
    if not has_scope:
        scope_errors += 1
        notes.append("missing low-temperature / electrolyte E1 scope")
    if not has_negative:
        scope_errors += 1
        notes.append("omitted high-temperature or E2 negative evidence")
    if not avoids_high_temp_overclaim:
        notes.append("overclaimed high-temperature use")

    hygiene = 0.35
    if has_scope:
        hygiene += 0.22
    if has_negative:
        hygiene += 0.22
    if avoids_high_temp_overclaim:
        hygiene += 0.09

    return ScoreBreakdown(
        retrieval_score=0.91,
        hypothesis_hygiene=round(min(hygiene, 0.88), 2),
        scope_errors=scope_errors,
        contradictions_caught=2 if improved else 0,
        retired_claims=1 if improved else 0,
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

