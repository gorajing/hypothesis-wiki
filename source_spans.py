from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceSpanIssue:
    code: str
    claim_id: str | None
    message: str


def source_text_for_card(card: dict[str, Any]) -> str:
    return card.get("source_text") or card.get("abstract") or ""


def find_span(source_text: str, quote: str) -> tuple[int, int]:
    """Find a verbatim quote in source text, returning character offsets."""
    if not quote:
        raise ValueError("empty evidence span")
    start = source_text.find(quote)
    if start == -1:
        preview = quote[:80].replace("\n", " ")
        raise ValueError(f"evidence span is not a verbatim substring: {preview!r}")
    return start, start + len(quote)


def attach_evidence_offsets(claim: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of claim with validated source-span offsets attached."""
    source_text = source_text_for_card(card)
    if not source_text:
        raise ValueError(f"source card {card.get('paper_id')} has no source text")

    evidence_span = claim.get("evidence_span")
    if not evidence_span:
        raise ValueError(f"claim {claim.get('id')} is missing evidence_span")

    start, end = find_span(source_text, evidence_span)
    return {
        **claim,
        "evidence_start": start,
        "evidence_end": end,
        "evidence_span_valid": True,
    }


def validate_claim_evidence_span(claim: dict[str, Any], card: dict[str, Any]) -> list[EvidenceSpanIssue]:
    claim_id = claim.get("id")
    source_text = source_text_for_card(card)
    evidence_span = claim.get("evidence_span")

    if not evidence_span:
        return [EvidenceSpanIssue("missing_evidence_span", claim_id, "claim has no verbatim evidence span")]
    if not source_text:
        return [EvidenceSpanIssue("missing_source_text", claim_id, "source card has no source text")]

    try:
        start, end = find_span(source_text, evidence_span)
    except ValueError as exc:
        return [EvidenceSpanIssue("unsupported_claim", claim_id, str(exc))]

    issues: list[EvidenceSpanIssue] = []
    if claim.get("evidence_start") is not None and claim.get("evidence_start") != start:
        issues.append(EvidenceSpanIssue("span_start_drift", claim_id, "stored evidence_start does not match source text"))
    if claim.get("evidence_end") is not None and claim.get("evidence_end") != end:
        issues.append(EvidenceSpanIssue("span_end_drift", claim_id, "stored evidence_end does not match source text"))
    return issues


def validate_claims_against_cards(
    claims: list[dict[str, Any]],
    cards: list[dict[str, Any]],
) -> list[EvidenceSpanIssue]:
    by_id = {card["paper_id"]: card for card in cards}
    issues: list[EvidenceSpanIssue] = []
    for claim in claims:
        card = by_id.get(claim.get("source"))
        if not card:
            issues.append(
                EvidenceSpanIssue(
                    "missing_source_card",
                    claim.get("id"),
                    f"no paper card found for source {claim.get('source')!r}",
                )
            )
            continue
        issues.extend(validate_claim_evidence_span(claim, card))
    return issues

