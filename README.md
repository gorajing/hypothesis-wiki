# Hypothesis Wiki

A self-correcting scientific knowledge wiki for the Cognee x Redis hackathon.

Most knowledge wikis get bigger. Hypothesis Wiki is designed to get more correct. Redis holds tentative scientific claims in session memory. A distillation gate promotes only attributed, scoped, testable claims into the Cognee graph. Linting and critic feedback catch overclaims, contradictions, and missing negative evidence. The skill loop then improves the distiller so the same query gets a safer answer on the next run.

## Demo Target

Research question:

```text
Should AX-17 be used for high-temperature battery cells?
```

With the weak v1 skill, the distiller drops scope, the distillation gate rejects every claim, and the agent overclaims from unverified session memory. After the skill is improved from that feedback, the same query is answered from scoped, promoted evidence:

```text
AX-17 is supported only under 25C, coin cell, electrolyte E1; high-temperature, E2, and pouch-cell evidence is negative or non-replicating.
```

## Quickstart

The demo has no external dependencies:

```bash
python3 demo.py
```

Build AI benchmark claims from the MLPerf Inference v5.1 fixture:

```bash
python3 ingest_real_research.py \
  --from-cards data/mlperf_v5_1_cards.json \
  --claims-out data/mlperf_v5_1_claims.json \
  --extractor curated
```

Build the science claim audit database used by the final submission:

```bash
python3 build_science_database.py
```

Expected database summary:

```text
papers:   6
claims:   6
valid:    6
promote:  6
offline:  3
server:   3
```

Behavior is covered by tests (the scorer reads graph state, the v1→v2 skill change is executed, not scripted):

```bash
python3 -m pytest tests/ -q
```

Prove the real Redis/Cognee memory path in the hackathon environment:

```bash
python3 -m pip install -r requirements.txt
export REDIS_URL=redis://localhost:6379
export LLM_API_KEY=...  # or set OPENAI_API_KEY
export COGNEE_DATASET=hypothesis-wiki-trusted
python3 cognee_redis_spike.py
```

The spike requires `RedisSessionStore` and `CogneeTrustedGraphStore`; it does
not silently fall back to in-memory stores.

Expected headline (every value computed from graph state, nothing hardcoded):

```text
retrieval_score:       0.70 -> 0.70
hypothesis_hygiene:    0.15 -> 1.00
scope_errors:          1 -> 0
contradictions_caught: 0 -> 3
retired_claims:        0 -> 1
```

Retrieval stays flat by design: the improved answer is more cautious, not less informed.

## Architecture

```text
paper cards
  -> Redis session quarantine
  -> candidate typed claims
  -> should_distill gate
  -> Cognee trusted graph
  -> lint + critic score
  -> skill feedback
  -> improved distiller
```

## Files

```text
data/paper_cards.json                 controlled science corpus
distiller.py                           skill-driven distiller + skill proposer
distillation_policy.py                 promotion gate from Redis to Cognee
critic.py                              graph-derived scoring + lint
demo.py                                end-to-end before/after demo
tests/                                 behavior tests (pytest)
docs/ARCHITECTURE.md                   design overview
docs/DATA_CONTRACTS.md                 claim and memory schemas
docs/IMPLEMENTATION_PLAN.md            build order and cut lines
docs/DEMO_SCRIPT.md                    3-minute presentation script
docs/PROVENANCE_CONTRACT.md            verbatim evidence-span contract
SUBMISSION.md                          hackathon submission draft
my_skills/hypothesis_distiller/        v1 + v2 skills; SKILL.proposed.md is
                                       written by the demo's apply step
```

## Hackathon Framing

Redis is not just a cache. It is the scientific quarantine layer: raw papers, candidate hypotheses, run traces, and critic notes live there until they earn permanence.

Cognee is the trusted graph: promoted hypotheses, evidence links, contradiction edges, retired claims, and skill improvements live there.

The unique angle is the distillation policy between them.
