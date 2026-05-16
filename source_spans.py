from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceSpanIssue:
    code: str
    claim_id: str | None
    message: str


REQUIRED_PROVENANCE_FIELDS = (
    "id",
    "kind",
    "text",
    "source",
    "source_url",
    "paper_title",
    "doi",
    "scope_conditions",
    "outcome",
    "direction",
    "evidence_type",
    "evidence_span",
    "evidence_start",
    "evidence_end",
    "evidence_span_valid",
    "status",
    "confidence",
)

NON_EMPTY_PROVENANCE_FIELDS = (
    "id",
    "kind",
    "text",
    "source",
    "paper_title",
    "scope_conditions",
    "outcome",
    "direction",
    "evidence_type",
    "evidence_span",
    "status",
)


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


def validate_claim_contract(claim: dict[str, Any]) -> list[EvidenceSpanIssue]:
    """Validate the real-research provenance fields required before promotion."""
    claim_id = claim.get("id")
    issues: list[EvidenceSpanIssue] = []

    for field in REQUIRED_PROVENANCE_FIELDS:
        if field not in claim:
            issues.append(
                EvidenceSpanIssue(
                    "missing_contract_field",
                    claim_id,
                    f"claim is missing required provenance field {field!r}",
                )
            )

    for field in NON_EMPTY_PROVENANCE_FIELDS:
        if field in claim and not claim.get(field):
            issues.append(
                EvidenceSpanIssue(
                    "empty_contract_field",
                    claim_id,
                    f"required provenance field {field!r} is empty",
                )
            )

    if "scope_conditions" in claim and not isinstance(claim.get("scope_conditions"), list):
        issues.append(
            EvidenceSpanIssue(
                "invalid_scope_conditions",
                claim_id,
                "scope_conditions must be a list",
            )
        )

    if "confidence" in claim and not isinstance(claim.get("confidence"), (int, float)):
        issues.append(
            EvidenceSpanIssue(
                "invalid_confidence",
                claim_id,
                "confidence must be numeric",
            )
        )

    start = claim.get("evidence_start")
    end = claim.get("evidence_end")
    if "evidence_start" in claim and not isinstance(start, int):
        issues.append(
            EvidenceSpanIssue(
                "invalid_evidence_offset",
                claim_id,
                "evidence_start must be an integer",
            )
        )
    if "evidence_end" in claim and not isinstance(end, int):
        issues.append(
            EvidenceSpanIssue(
                "invalid_evidence_offset",
                claim_id,
                "evidence_end must be an integer",
            )
        )
    if isinstance(start, int) and isinstance(end, int) and start >= end:
        issues.append(
            EvidenceSpanIssue(
                "invalid_evidence_offset",
                claim_id,
                "evidence_start must be before evidence_end",
            )
        )

    if "evidence_span_valid" in claim and claim.get("evidence_span_valid") is not True:
        issues.append(
            EvidenceSpanIssue(
                "invalid_evidence_span",
                claim_id,
                "evidence_span_valid must be true",
            )
        )

    return issues


def validate_claim_evidence_span(claim: dict[str, Any], card: dict[str, Any]) -> list[EvidenceSpanIssue]:
    claim_id = claim.get("id")
    source_text = source_text_for_card(card)
    evidence_span = claim.get("evidence_span")

    if not evidence_span:
        return [
            EvidenceSpanIssue(
                "missing_evidence_span",
                claim_id,
                "claim has no verbatim evidence span",
            )
        ]
    if not source_text:
        return [EvidenceSpanIssue("missing_source_text", claim_id, "source card has no source text")]

    try:
        start, end = find_span(source_text, evidence_span)
    except ValueError as exc:
        return [EvidenceSpanIssue("unsupported_claim", claim_id, str(exc))]

    issues: list[EvidenceSpanIssue] = []
    if claim.get("evidence_start") is not None and claim.get("evidence_start") != start:
        issues.append(
            EvidenceSpanIssue(
                "span_start_drift",
                claim_id,
                "stored evidence_start does not match source text",
            )
        )
    if claim.get("evidence_end") is not None and claim.get("evidence_end") != end:
        issues.append(
            EvidenceSpanIssue(
                "span_end_drift",
                claim_id,
                "stored evidence_end does not match source text",
            )
        )
    return issues


def validate_claims_against_cards(
    claims: list[dict[str, Any]],
    cards: list[dict[str, Any]],
) -> list[EvidenceSpanIssue]:
    by_id = {card["paper_id"]: card for card in cards}
    issues: list[EvidenceSpanIssue] = []
    for claim in claims:
        issues.extend(validate_claim_contract(claim))
        card = by_id.get(claim.get("source"))
        if not card:
            issues.append(
                EvidenceSpanIssue(
                    "missing_source_card",
                    claim.get("id"),
                    f"no source card found for source {claim.get('source')!r}",
                )
            )
            continue
        issues.extend(validate_claim_evidence_span(claim, card))
    return issues
