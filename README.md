# Benchmark Claim Wiki

A self-correcting AI benchmark claim wiki for the Cognee x Redis hackathon.

Benchmark Claim Wiki audits current MLPerf Inference result claims. Redis holds raw result cards, candidate claims, rejected claims, and run feedback as session memory. A distillation gate promotes only attributed, scoped, provenance-validated claims into Cognee's durable graph. The critic catches scenario overclaims such as treating Offline throughput as if it applied to Server workloads, then rewrites the distiller skill so the next run preserves benchmark, model, hardware, scenario, and metric scope.

## Demo Target

Research question:

```text
Can the top MLPerf Offline Llama2 result be generalized to all serving workloads?
```

With the weak v1 skill, the distiller drops scope, the gate rejects every claim, and the agent overclaims from untrusted session memory. After the skill is improved from that feedback, the same query is answered from scoped, promoted evidence:

```text
MI325X Llama2 performance is supported only under MLPerf Inference v5.1, llama2-70b-99, Offline scenario, 8x AMD Instinct MI325X; Offline results do not generalize to Server serving workloads because MLPerf reports a separate lower Server result.
```

## Quickstart

The deterministic self-improvement demo has no external services:

```bash
python3 demo.py
```

Build benchmark claims from the MLPerf Inference v5.1 fixture:

```bash
python3 ingest_real_research.py \
  --from-cards data/mlperf_v5_1_cards.json \
  --claims-out data/mlperf_v5_1_claims.json \
  --extractor curated
```

Build the benchmark claim audit database used by the final submission:

```bash
python3 build_benchmark_database.py
```

Expected database summary:

```text
database: data/benchmark_claim_audit_db.json
sources:  6
claims:   6
valid:    6
promote:  6
offline:  3
server:   3
```

Run the test suite:

```bash
python3 -m pytest -q
```

Prove the real Redis/Cognee memory path in the hackathon environment:

```bash
python3 -m pip install -r requirements.txt
export REDIS_URL=redis://localhost:6379
export LLM_API_KEY=...  # or set OPENAI_API_KEY
export COGNEE_DATASET=benchmark-claim-wiki-trusted
python3 cognee_redis_spike.py
```

The spike requires `RedisSessionStore` and `CogneeTrustedGraphStore`; it does not silently fall back to in-memory stores.

Expected headline from `demo.py`:

```text
retrieval_score:       0.70 -> 1.00
hypothesis_hygiene:    0.15 -> 1.00
scope_errors:          1 -> 0
contradictions_caught: 0 -> 3
retired_claims:        0 -> 1
```

Retrieval improves because the final answer is both grounded in trusted graph claims and explicitly responsive to the MLPerf/Llama2 question.

## Architecture

```text
MLPerf result cards
  -> Redis session quarantine
  -> candidate benchmark claims
  -> source-span validation
  -> should_distill gate
  -> Cognee trusted graph
  -> lint + critic score
  -> skill feedback
  -> improved distiller
```

## Files

```text
data/mlperf_v5_1_cards.json           curated MLPerf Inference v5.1 result cards
data/mlperf_v5_1_claims.json          validated benchmark claims
data/benchmark_claim_audit_db.json    final audit database
data/demo_mlperf_cards.json           deterministic self-improvement corpus
build_benchmark_database.py           database builder
ingest_real_research.py               source-card ingestion command
backend/storage.py                    Redis session store + Cognee graph store
distiller.py                          skill-driven distiller + skill proposer
distillation_policy.py                promotion gate from Redis to Cognee
critic.py                             graph-derived scoring + lint
demo.py                               end-to-end before/after demo
tests/                                behavior tests
docs/ARCHITECTURE.md                  design overview
docs/DATA_CONTRACTS.md                claim and memory schemas
docs/BENCHMARK_RESULT_INGESTION.md    benchmark ingestion path
docs/DEMO_SCRIPT.md                   3-minute presentation script
docs/PROVENANCE_CONTRACT.md           verbatim evidence-span contract
SUBMISSION.md                         hackathon submission draft
```

## Hackathon Framing

Redis is the quarantine layer for raw benchmark result cards, candidate claims, rejected claims, and run-specific feedback.

Cognee is the trusted graph for promoted benchmark claims, evidence links, scenario scope, contradiction edges, retired claims, and skill improvements.

The unique piece is the distillation policy between them: a wiki that learns what not to promote.
