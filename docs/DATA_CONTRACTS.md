# Data Contracts

## Source Card

Source cards are normalized inputs. The final demo uses curated MLPerf Inference v5.1 result cards, but the same shape can be produced by a benchmark-results adapter or a research-paper adapter.

```json
{
  "paper_id": "mlperf_v5_1_0007_mi325x_llama2_offline",
  "title": "MLPerf Inference v5.1 result 5.1-0007: Llama2-70B Offline on 8x AMD Instinct MI325X",
  "year": 2025,
  "url": "https://mlcommons.org/benchmarks/inference-datacenter/",
  "source_type": "benchmark_result",
  "source_text": "MLPerf Inference v5.1 closed division result 5.1-0007 reports system_name QuantaGrid D74A-7U with 8x AMD Instinct MI325X, benchmark llama2-70b-99, scenario Offline, performance_sample_count 24576, and Result Samples per second 34520.4.",
  "finding": "MI325X reached 34,520.4 samples/s on llama2-70b-99 in MLPerf Offline.",
  "conditions": ["MLPerf Inference v5.1", "closed division", "llama2-70b-99", "Offline scenario", "8x AMD Instinct MI325X"],
  "outcome": "llama2-70b-99 throughput",
  "direction": "observes",
  "result_type": "benchmark_result"
}
```

Common `result_type` values:

```text
benchmark_result
conditional
negative
replication_failure
```

## Candidate Claim

Candidate claims live first in Redis session memory.

```json
{
  "id": "claim_mlperf_v5_1_0007_mi325x_llama2_offline",
  "kind": "evidence",
  "text": "MI325X reached 34,520.4 samples/s on llama2-70b-99 in MLPerf Offline.",
  "source": "mlperf_v5_1_0007_mi325x_llama2_offline",
  "source_url": "https://mlcommons.org/benchmarks/inference-datacenter/",
  "paper_title": "MLPerf Inference v5.1 result 5.1-0007: Llama2-70B Offline on 8x AMD Instinct MI325X",
  "scope_conditions": ["MLPerf Inference v5.1", "closed division", "llama2-70b-99", "Offline scenario", "8x AMD Instinct MI325X"],
  "outcome": "llama2-70b-99 throughput",
  "direction": "observes",
  "evidence_type": "curated_real_paper_span",
  "evidence_span": "MLPerf Inference v5.1 closed division result 5.1-0007 reports system_name QuantaGrid D74A-7U with 8x AMD Instinct MI325X, benchmark llama2-70b-99, scenario Offline, performance_sample_count 24576, and Result Samples per second 34520.4.",
  "evidence_start": 0,
  "evidence_end": 235,
  "evidence_span_valid": true,
  "status": "candidate",
  "confidence": 0.95
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

Cognee should provide storage and retrieval beneath this interface.

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
  "retrieval_score": 0.70,
  "hypothesis_hygiene": 1.00,
  "scope_errors": 0,
  "contradictions_caught": 3,
  "retired_claims": 1
}
```

Retrieval should not collapse while hypothesis hygiene improves. That prevents the obvious judge objection: "Did you become more cautious by retrieving less?"
