# Data Contracts

## Paper Card

Paper cards are the normalized input. For the deterministic demo, these are curated from a narrow research question. For real science ingestion, a Semantic Scholar or PMC adapter should produce the same shape.

```json
{
  "paper_id": "paper_a",
  "title": "AX-17 improves retention in low-temperature cells",
  "year": 2025,
  "url": "https://example.org/paper-a",
  "abstract": "Short source text.",
  "finding": "AX-17 improved capacity retention by 22%.",
  "conditions": ["25C", "electrolyte E1"],
  "outcome": "capacity retention",
  "direction": "improves",
  "result_type": "positive"
}
```

Allowed `result_type` values:

```text
positive
conditional
negative
replication_failure
```

## Candidate Claim

Candidate claims live first in Redis session memory.

```json
{
  "id": "claim_paper_a",
  "kind": "hypothesis",
  "text": "AX-17 improves capacity retention.",
  "source": "paper_a",
  "source_url": "https://example.org/paper-a",
  "scope_conditions": ["25C", "electrolyte E1"],
  "outcome": "capacity retention",
  "direction": "improves",
  "evidence_type": "paper_card",
  "evidence_span": "AX-17 improved capacity retention by 22%.",
  "evidence_start": 123,
  "evidence_end": 183,
  "evidence_span_valid": true,
  "status": "candidate",
  "confidence": 0.62
}
```

Allowed `kind` values:

```text
hypothesis
evidence
negative_result
contradiction
retired_claim
```

## Distill Decision

```json
{
  "promote": true,
  "status": "promote",
  "confidence": 0.78,
  "reason": "attributed, scoped, non-duplicate"
}
```

Allowed `status` values:

```text
promote
reject
hold
retire
```

## Graph State

The first implementation uses an in-memory graph state. Cognee should replace the storage and retrieval beneath this interface.

Required methods:

```python
has_duplicate(claim) -> bool
has_conflict(claim) -> bool
negative_evidence_for(outcome) -> list[dict]
promote(claim) -> None
retire(claim_id, reason, evidence_id) -> None
```

## Run Score

```json
{
  "run_id": "run_001",
  "retrieval_score": 0.91,
  "hypothesis_hygiene": 0.35,
  "scope_errors": 2,
  "contradictions_caught": 0,
  "retired_claims": 0
}
```

Retrieval should stay roughly flat while hypothesis hygiene improves. That prevents the obvious judge objection: "Did you become more cautious by retrieving less?"
