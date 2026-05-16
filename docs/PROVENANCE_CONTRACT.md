# Provenance Contract

Benchmark Claim Wiki does not trust extracted claims until they are anchored to verbatim source text.

## Rule

Every promoted benchmark claim should carry:

```text
id
kind
text
source
source_url
paper_title
doi
scope_conditions
outcome
direction
evidence_type
evidence_span
evidence_start
evidence_end
evidence_span_valid
status
confidence
```

The span must be a literal substring of the source card's `source_text` or `abstract`. `source_spans.validate_claims_against_cards()` enforces both the required fields and the deterministic span offsets before claims are written or promoted.

## Extraction Pattern

Use a two-schema flow:

```text
model or curator emits:
  claim text
  kind
  outcome
  direction
  scope_conditions
  verbatim evidence_span

server computes:
  stable ID
  source metadata
  evidence_start
  evidence_end
  evidence_span_valid
```

Do not ask the model to compute offsets. Python computes offsets deterministically.

## Promotion Gate

`should_distill()` rejects an extracted claim if it has an `evidence_span` but lacks validated offsets.

This preserves the Redis/Cognee split:

```text
unsupported candidate claim -> Redis only
validated evidence-backed claim -> Cognee graph
```

## Deterministic MLPerf Fixture

The repository keeps a curated MLPerf Inference v5.1 fixture so tests can prove the ingestion path without live API variance:

- `data/mlperf_v5_1_cards.json`: source result cards for six MLPerf records.
- `data/mlperf_v5_1_claims.json`: generated and validated claims for those records.
- `data/benchmark_claim_audit_db.json`: final audit database built from the validated claims.

Generate candidate claims:

```bash
python3 ingest_real_research.py \
  --from-cards data/mlperf_v5_1_cards.json \
  --claims-out data/mlperf_v5_1_claims.json \
  --extractor curated
```

Build the submission database:

```bash
python3 build_benchmark_database.py
```

This gives the wiki current AI benchmark substance without introducing live API variance during the judged demo.
