from dataclasses import dataclass


@dataclass(frozen=True)
class DistillDecision:
    promote: bool
    status: str
    confidence: float
    reason: str


def promote(reason: str, confidence: float = 0.78) -> DistillDecision:
    return DistillDecision(True, "promote", confidence, reason)


def reject(reason: str) -> DistillDecision:
    return DistillDecision(False, "reject", 0.0, reason)


def hold(reason: str, confidence: float = 0.25) -> DistillDecision:
    return DistillDecision(False, "hold", confidence, reason)


def should_distill(claim: dict, graph_state) -> DistillDecision:
    """Gate candidate claims from Redis quarantine into the trusted graph."""
    if not claim.get("source"):
        return reject("missing source")

    if not claim.get("text"):
        return reject("missing claim text")

    if claim.get("evidence_span") and not claim.get("evidence_span_valid"):
        return reject("evidence span was not validated")

    if claim.get("evidence_span") and (
        claim.get("evidence_start") is None or claim.get("evidence_end") is None
    ):
        return reject("evidence span missing offsets")

    if graph_state.has_duplicate(claim):
        return reject("near duplicate")

    kind = claim.get("kind")
    if kind == "hypothesis":
        if not claim.get("outcome"):
            return reject("hypothesis missing testable outcome")
        if not claim.get("scope_conditions"):
            return reject("hypothesis missing scope conditions")
        if graph_state.has_conflict(claim):
            return hold("hypothesis conflicts with trusted graph; promote contradiction first")
        return promote("attributed, scoped, testable hypothesis")

    if kind in {"negative_result", "evidence"}:
        if not claim.get("outcome"):
            return reject("evidence missing outcome")
        return promote("attributed evidence")

    if kind == "contradiction":
        if not claim.get("contradicts"):
            return reject("contradiction missing target")
        return promote("explicit contradiction edge", confidence=0.82)

    if kind == "retired_claim":
        if not claim.get("retires"):
            return reject("retirement missing target")
        return promote("retirement keeps audit trail", confidence=0.9)

    return reject(f"unknown claim kind: {kind}")
