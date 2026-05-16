# Benchmark Result Ingestion

The final demo is centered on MLCommons MLPerf Inference v5.1 result records. These records are relevant to the hackathon audience because they are about current AI inference systems, hardware, serving scenarios, and throughput metrics.

## Deterministic MLPerf Path

Use the curated MLPerf fixture for the judged run:

```bash
python3 ingest_real_research.py \
  --from-cards data/mlperf_v5_1_cards.json \
  --claims-out data/mlperf_v5_1_claims.json \
  --extractor curated
```

This writes:

```text
data/mlperf_v5_1_claims.json
```

Before `claims-out` is written, the ingestion command validates every claim against the provenance contract: required metadata fields, a verbatim `evidence_span`, deterministic `evidence_start` / `evidence_end`, and `evidence_span_valid: true`.

## Build The Audit Database

```bash
python3 build_benchmark_database.py
```

Expected summary:

```text
database: data/benchmark_claim_audit_db.json
sources:  6
claims:   6
valid:    6
promote:  6
offline:  3
server:   3
```

The database contains:

- source URLs
- verbatim evidence spans
- model scope
- hardware scope
- MLPerf scenario scope
- throughput metric labels
- distillation-gate promotion decisions

## Optional Search Path

`ingest_real_research.py` still supports Semantic Scholar search for future expansion:

```bash
export SEMANTIC_SCHOLAR_API_KEY=...

python3 ingest_real_research.py \
  --queries-file data/research_queries.json \
  --cards-out data/real_benchmark_cards.json \
  --claims-out data/real_benchmark_claims.json \
  --extractor heuristic
```

For the hackathon, the curated MLPerf path is preferred because it is current, deterministic, and directly relevant to AI infrastructure.

## Optional OpenAI Extraction

OpenAI extraction is optional. It is useful for richer claim structure, but it is not required for the judged demo path.

```bash
export OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-5.2

python3 ingest_real_research.py \
  --from-cards data/real_benchmark_cards.json \
  --claims-out data/real_benchmark_claims.openai.json \
  --extractor openai
```

The OpenAI path uses the Responses API with JSON Schema structured outputs. It must preserve source wording, benchmark scope, scenario scope, hardware scope, metric labels, and uncertainty.

## Claim Contract

Every extracted claim must include:

```text
source
source_url
paper_title
doi
evidence_span
evidence_start
evidence_end
evidence_span_valid
kind
text
outcome
direction
scope_conditions
confidence
```

The critical integrity rule:

```text
The claim text must be grounded in an evidence_span from the source card.
```

If the extractor cannot find an evidence-bearing sentence, it should emit no claim rather than invent one.
