import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from source_spans import attach_evidence_offsets, source_text_for_card


EVIDENCE_PATTERNS = [
    "improv",
    "increase",
    "enhance",
    "higher",
    "reduce",
    "decrease",
    "lower",
    "suppress",
    "no significant",
    "no measurable",
    "no benefit",
    "failed",
    "fails",
    "did not",
    "depends",
    "only",
    "whereas",
    "however",
    "observed",
    "reports",
    "result",
    "benchmark",
    "throughput",
    "samples per second",
    "scheduled samples",
    "offline",
    "server",
    "%",
]


def extract_claims_from_cards(
    cards: list[dict[str, Any]],
    *,
    extractor: str = "heuristic",
    model: str | None = None,
) -> list[dict[str, Any]]:
    if extractor == "heuristic":
        return [claim for card in cards for claim in extract_claims_heuristic(card)]
    if extractor == "curated":
        return [claim for card in cards for claim in extract_claims_curated(card)]
    if extractor == "openai":
        return [claim for card in cards for claim in extract_claims_openai(card, model=model)]
    if extractor == "none":
        return []
    raise ValueError(f"unknown extractor: {extractor}")


def extract_claims_heuristic(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract source-grounded claims from a source card without model calls."""
    abstract = source_text_for_card(card).strip()
    if not abstract:
        return []

    sentences = _split_sentences(abstract)
    claims: list[dict[str, Any]] = []
    for index, sentence in enumerate(sentences):
        if not _looks_like_evidence(sentence):
            continue

        direction = _infer_direction(sentence)
        kind = _kind_for_direction(direction)
        conditions = _extract_conditions(sentence)

        claim = {
            "id": f"claim_{card['paper_id']}_{index + 1}",
            "kind": kind,
            "text": sentence,
            "source": card["paper_id"],
            "source_url": card.get("url"),
            "paper_title": card.get("title"),
            "paper_year": card.get("year"),
            "doi": card.get("doi"),
            "scope_conditions": conditions,
            "outcome": _infer_outcome(sentence, card),
            "direction": direction,
            "evidence_type": "abstract_sentence",
            "evidence_span": sentence,
            "status": "candidate",
            "confidence": _heuristic_confidence(direction, conditions),
        }
        try:
            claims.append(attach_evidence_offsets(claim, card))
        except ValueError:
            continue

    return claims


def extract_claims_curated(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize hand-curated real-paper claims and attach verbatim spans."""
    claims: list[dict[str, Any]] = []
    for index, item in enumerate(card.get("expected_claims", [])):
        claim = {
            "id": item.get("id") or f"claim_{card['paper_id']}_{index + 1}",
            "kind": item["kind"],
            "text": item["text"],
            "source": card["paper_id"],
            "source_url": card.get("url"),
            "paper_title": card.get("title"),
            "paper_year": card.get("year"),
            "doi": card.get("doi"),
            "pmid": card.get("pmid"),
            "pmcid": card.get("pmcid"),
            "scope_conditions": item.get("scope_conditions", []),
            "outcome": item.get("outcome", "reported outcome"),
            "direction": item.get("direction", "observes"),
            "evidence_type": "curated_real_paper_span",
            "evidence_span": item["evidence_span"],
            "status": "candidate",
            "confidence": item.get("confidence", 0.9),
        }
        claims.append(attach_evidence_offsets(claim, card))
    return claims


def extract_claims_openai(card: dict[str, Any], *, model: str | None = None) -> list[dict[str, Any]]:
    """Use OpenAI structured outputs to extract claims from one source card."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for extractor='openai'")

    model = model or os.environ.get("OPENAI_MODEL", "gpt-5.2")
    payload = {
        "model": model,
        "instructions": (
            "Extract source-grounded benchmark claims from the source card. "
        "Use only the title and source text. Preserve scope conditions, negative "
            "results, and uncertainty. Do not infer beyond the abstract."
        ),
        "input": json.dumps(card, ensure_ascii=True),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "benchmark_claim_extraction",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "claims": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "kind": {
                                        "type": "string",
                                        "enum": [
                                            "hypothesis",
                                            "evidence",
                                            "negative_result",
                                            "contradiction",
                                        ],
                                    },
                                    "text": {"type": "string"},
                                    "scope_conditions": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "outcome": {"type": "string"},
                                    "direction": {"type": "string"},
                                    "evidence_span": {"type": "string"},
                                    "confidence": {"type": "number"},
                                },
                                "required": [
                                    "kind",
                                    "text",
                                    "scope_conditions",
                                    "outcome",
                                    "direction",
                                    "evidence_span",
                                    "confidence",
                                ],
                            },
                        }
                    },
                    "required": ["claims"],
                },
            }
        },
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI extraction failed: {exc.code} {detail}") from exc

    output_text = _response_output_text(body)
    parsed = json.loads(output_text)
    claims = []
    for index, claim in enumerate(parsed.get("claims", [])):
        normalized = {
            "id": f"claim_{card['paper_id']}_{index + 1}",
            "source": card["paper_id"],
            "source_url": card.get("url"),
            "paper_title": card.get("title"),
            "paper_year": card.get("year"),
            "doi": card.get("doi"),
            "evidence_type": "abstract_openai_structured",
            "status": "candidate",
            **claim,
        }
        try:
            claims.append(attach_evidence_offsets(normalized, card))
        except ValueError:
            continue
    return claims


def _split_sentences(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", stripped) if part.strip()]


def _looks_like_evidence(sentence: str) -> bool:
    lower = sentence.lower()
    return any(pattern in lower for pattern in EVIDENCE_PATTERNS)


def _infer_direction(sentence: str) -> str:
    lower = sentence.lower()
    if any(phrase in lower for phrase in ["no significant", "no measurable", "no benefit", "did not", "failed", "fails"]):
        return "no_benefit"
    if any(phrase in lower for phrase in ["only", "depends", "whereas", "however", "below", "above", "under"]):
        return "conditional"
    if any(phrase in lower for phrase in ["reduce", "decrease", "lower", "suppress"]):
        return "reduces"
    if any(phrase in lower for phrase in ["improv", "increase", "enhance", "higher"]):
        return "improves"
    return "observes"


def _kind_for_direction(direction: str) -> str:
    if direction == "no_benefit":
        return "negative_result"
    if direction == "conditional":
        return "evidence"
    return "hypothesis"


def _extract_conditions(sentence: str) -> list[str]:
    patterns = [
        r"\bwithin\s+[A-Za-z0-9 ./%+-]{1,40}",
        r"\bat\s+\d+\s+months?\b",
        r"\bas\s+long\s+as\s+[A-Za-z0-9 ./%+-]{1,40}",
        r"\b(?:below|above|under|over|at)\s+[A-Za-z0-9 ./%+-]{1,40}",
        r"\bwith\s+[A-Za-z0-9 ./%+-]{1,60}",
        r"\busing\s+[A-Za-z0-9 ./%+-]{1,60}",
        r"\bMLPerf\s+Inference\s+v\d+(?:\.\d+)?\b",
        r"\b(?:Offline|Server)\s+scenario\b",
        r"\b(?:llama2-70b-99|mixtral-8x7b)\b",
        r"\b\d+x\s+(?:AMD\s+)?Instinct\s+MI\d+X\b",
        r"\b\d+(?:,\d{3})*(?:\.\d+)?\s+(?:scheduled\s+)?samples\s+per\s+second\b",
        r"\b\d+(?:\.\d+)?\s?%\b",
    ]
    conditions: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, sentence, flags=re.IGNORECASE):
            value = match.group(0).strip(" .,;")
            if value and value.lower() not in {item.lower() for item in conditions}:
                conditions.append(value)
    return conditions


def _infer_outcome(sentence: str, card: dict[str, Any]) -> str:
    lower = sentence.lower()
    outcomes = [
        "llama2-70b-99 throughput",
        "mixtral-8x7b throughput",
        "result samples per second",
        "scheduled samples per second",
        "benchmark throughput",
        "scenario-specific throughput",
        "performance",
    ]
    for outcome in outcomes:
        if outcome in lower:
            return outcome
    return card.get("outcome") or "reported outcome"


def _heuristic_confidence(direction: str, conditions: list[str]) -> float:
    confidence = 0.55
    if direction in {"improves", "reduces", "no_benefit"}:
        confidence += 0.1
    if conditions:
        confidence += 0.1
    return round(min(confidence, 0.78), 2)


def _response_output_text(body: dict[str, Any]) -> str:
    if isinstance(body.get("output_text"), str):
        return body["output_text"]
    for item in body.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise RuntimeError("OpenAI response did not include output text")
