# Team Submission

## Team

Team name: Hypothesis Wiki

Participants: Jin Choi

Wiki / project name: Hypothesis Wiki

## Wiki Overview

Hypothesis Wiki is a self-correcting scientific knowledge wiki for auditing
claims in research literature. Redis acts as the hot session-memory quarantine:
raw papers, candidate claims, rejected claims, critic notes, and run traces are
kept there until they earn promotion. Cognee is the durable trusted graph:
only attributed, scoped, provenance-validated claims are promoted into it. The
wiki self-improves by using distillation-gate rejections and critic feedback to
rewrite the distiller skill, then rerunning the same query to prove that
scope preservation, contradiction handling, and claim retirement improved.

Domain or data sources:

- MLCommons MLPerf Inference v5.1 result records:
  - Llama2-70B and Mixtral-8x7B benchmark claims
  - Offline vs Server scenario scope
  - AMD Instinct MI300X vs MI325X hardware scope
- Optional Semantic Scholar abstract search via `ingest_real_research.py`
- Optional CAR-T paper fixtures retained as biomedical examples
- Controlled AX-17 battery corpus for deterministic before/after
  self-improvement evidence

Primary use case:

Literature-scale claim auditing: show which claims are supported, which are
scope-limited, which conflict with negative evidence, and which should be
retired or downgraded.

What makes it stand out:

- It separates tentative session memory from durable graph memory.
- It fails loudly if Redis or Cognee are missing; no silent in-memory fallback.
- Real-paper claims must pass span-level provenance validation before writing.
- The before/after improvement is computed from graph state, not hardcoded.
- The skill loop actually proposes and applies a revised distiller skill.

## The Three Operations

### Ingest

What goes in:

- Source cards containing MLPerf result metadata, source URLs, benchmark name,
  hardware, scenario, measured throughput, and evidence text
- Candidate claims extracted from those cards
- Agent run traces and raw intermediate observations
- Rejected claims and distillation-gate reasons

How it is captured:

- `ingest_real_research.py` extracts candidate claims from source cards.
- `source_spans.validate_claims_against_cards()` validates each claim against a
  verbatim evidence span with deterministic offsets.
- `RedisSessionStore.remember(payload, session_id=...)` stores raw/candidate
  session memory in Redis.
- `should_distill(claim, graph_state)` decides whether a candidate is promoted.
- `CogneeTrustedGraphStore.remember(payload)` writes promoted trusted claims to
  Cognee.

Code entry point:

- `ingest_real_research.py`
- `backend/storage.py`
- `distillation_policy.py`

### Query + Self-improve

How users query the wiki:

- Demo query path: `python3 demo.py`
- Live Redis/Cognee proof path: `python3 cognee_redis_spike.py`
- Programmatic path: `await backend.recall(query, session_id=...)` for Redis
  session memory, or `await backend.recall(query)` for Cognee trusted graph
  memory.

Where feedback comes from:

- Distillation-gate rejection reasons, such as missing scope or invalid
  evidence span
- Critic notes, such as overclaiming, omitted negative evidence, or ungrounded
  answer
- Lint issues from missing source/scope
- Test/eval metrics computed from graph state

How feedback updates the wiki:

- `propose_skill_revision(feedback)` turns concrete gate/critic feedback into a
  stronger distiller skill.
- The proposed skill is written to
  `my_skills/hypothesis_distiller/SKILL.proposed.md`.
- The same cards are redistilled with the proposed skill.
- More claims pass the gate, negative evidence is preserved, and contradicted
  broad claims are retired.

Code entry point:

- `demo.py`
- `distiller.py`
- `critic.py`

### Lint

What "linting" means in this wiki:

- Reject ungrounded claims with no source
- Reject hypotheses with missing scope conditions
- Reject real-paper claims whose evidence spans are absent or invalid
- Detect contradictions where a promoted positive hypothesis is undercut by
  negative or conditional evidence on the same outcome
- Track claims that should be retired after stronger contrary evidence appears

How it runs:

- On ingest: provenance validation before `claims-out` is written
- On promotion: `should_distill()` runs before Cognee writes
- On query/demo: `lint_claims()` and `score_answer()` run on demand

Code entry point:

- `source_spans.py`
- `distillation_policy.py`
- `critic.py`

## Self-Improvement Evidence

The live real-data path proves that current AI benchmark claims can be
extracted and provenance-validated, and that Redis/Cognee are actually used.
The self-improvement evidence uses a controlled AX-17 corpus so the before/after
run is deterministic and judge-repeatable.

Real-data ingest proof:

```text
python3 build_science_database.py

database: data/science_claim_audit_db.json
papers:   6
claims:   6
valid:    6
promote:  6
offline:  3
server:   3

python3 ingest_real_research.py \
  --from-cards data/mlperf_v5_1_cards.json \
  --claims-out /tmp/mlperf_claims.json \
  --extractor curated

paper_cards: 6 -> data/mlperf_v5_1_cards.json
claims:      6 -> /tmp/mlperf_claims.json
```

Live Redis/Cognee proof:

```text
Session backend: RedisSessionStore
Trusted graph backend: CogneeTrustedGraphStore
session write ok
graph write ok
session recall returned data
graph recall returned data
```

### Baseline Run

Query / task:

Should AX-17 be used for high-temperature battery cells?

Result:

```text
AX-17 improves battery stability and should be used for high-temperature cells.
```

Score:

```text
retrieval_score:       0.70
hypothesis_hygiene:    0.15
scope_errors:          1
contradictions_caught: 0
retired_claims:        0
```

Recorded feedback:

```text
error_type: missing_scope
error_message: v1 distiller dropped conditions, so the gate rejected all 4 claims
feedback:
  - claim_paper_a: hypothesis missing scope conditions
  - claim_paper_b: hypothesis missing scope conditions
  - claim_paper_c: hypothesis missing scope conditions
  - claim_paper_d: hypothesis missing scope conditions
  - answer not grounded in any trusted claim
  - overclaimed high-temperature use
success_score: 0.15
```

### Improved Run

Query / task:

Should AX-17 be used for high-temperature battery cells?

Result:

```text
AX-17 is supported only under 25C, coin cell, electrolyte E1; high-temperature,
E2, and pouch-cell evidence is negative or non-replicating.
```

Score:

```text
retrieval_score:       0.70
hypothesis_hygiene:    1.00
scope_errors:          0
contradictions_caught: 3
retired_claims:        1
```

What changed in the wiki between runs:

Before:

- v1 skill erased experimental scope
- all four distilled claims were rejected
- the trusted graph was empty
- the answer overclaimed from untrusted session memory

After:

- critic/gate feedback produced `SKILL.proposed.md`
- v2-style skill preserved temperature, cell format, electrolyte, and negative
  evidence
- four claims were promoted into the trusted graph
- three contradictory/negative findings were surfaced
- one broad claim was retired

Before / after:

```text
retrieval_score:       0.70 -> 0.70
hypothesis_hygiene:    0.15 -> 1.00
scope_errors:          1    -> 0
contradictions_caught: 0    -> 3
retired_claims:        0    -> 1
```

Retrieval is deliberately flat. The improved answer is more careful, not less
retrieved, which avoids the obvious failure mode of "it improved by saying
less."

## Architecture

```text
[AI benchmark result cards / agent turns / run traces]
        |
        v
[ Redis - session memory quarantine ]
        |
        | source-span validation + distillation gate
        v
[ Cognee - permanent trusted graph ]
        |
        v
[ recall / answer generation ]
        |
        v
[ critic + lint feedback -> skill improvement ]
        |
        v
[ revised distiller skill -> re-ingest / re-query ]
```

Components:

- `ingest_real_research.py`: fetch/use source cards and extract claims
- `source_spans.py`: validate evidence spans and offsets
- `backend/storage.py`: Redis session store and Cognee trusted graph adapter
- `distillation_policy.py`: promotion gate
- `distiller.py`: skill-driven claim distiller and skill proposer
- `critic.py`: graph-derived scoring and lint
- `demo.py`: deterministic self-improvement run
- `cognee_redis_spike.py`: live Redis/Cognee proof

## Redis-as-session-memory

What the agent writes into Redis:

- raw source cards
- candidate claims
- rejected claims and rejection reasons
- critic feedback
- run-specific observations and traces

How and when content is distilled into the graph:

- Candidate claims first live in Redis under a session id.
- The distillation gate checks attribution, evidence-span validity, scope,
  duplication, and conflicts.
- Only promoted claims are written to Cognee.

What stays in Redis vs. what gets promoted:

- Stays in Redis: raw notes, raw cards, untrusted candidate claims, rejected
  claims, failed spans, run-local feedback.
- Promoted to Cognee: attributed, scoped, validated claims; negative evidence;
  contradiction/retirement-relevant claims.

How distillation quality improved between baseline and improved run:

- Baseline skill dropped scope, so every claim was rejected.
- Improved skill preserved scope and negative evidence, so the graph gained
  usable trusted claims and the answer became conditional instead of universal.

## Agents / Skills

Skill path(s):

- `my_skills/hypothesis_distiller/SKILL.md`
- `my_skills/hypothesis_distiller/SKILL.v2.md`
- `my_skills/hypothesis_distiller/SKILL.proposed.md`

Roles:

- Ingestor: `ingest_real_research.py`, `research_claim_extractor.py`,
  `source_spans.py`
- Querier: `demo.py`, `backend.recall(...)`
- Linter: `source_spans.py`, `critic.py`, `distillation_policy.py`
- Critic: `critic.py`, `distiller.propose_skill_revision(...)`

## Reproduction

Commands to reproduce the judged demo:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

python3 -m pytest -q

python3 build_science_database.py

python3 ingest_real_research.py \
  --from-cards data/mlperf_v5_1_cards.json \
  --claims-out /tmp/mlperf_claims.json \
  --extractor curated

python3 demo.py
```

Commands to reproduce the live Redis/Cognee proof:

```bash
brew services start redis

export REDIS_URL=redis://localhost:6379
export LLM_API_KEY=...
export COGNEE_DATASET=hypothesis-wiki-trusted

python3 cognee_redis_spike.py
```

Environment variables required:

```text
LLM_API_KEY
REDIS_URL
COGNEE_DATASET
```

Optional:

```text
OPENAI_API_KEY
OPENAI_MODEL
SEMANTIC_SCHOLAR_API_KEY
COGNEE_URL
COGNEE_API_KEY
```

## Demo

Live demo link:

Local instructions above. A screen recording can show the commands in the same
order: real-paper ingest, tests, self-improvement demo, live Redis/Cognee spike.

3-minute pitch outline:

1. Problem / idea
   - Scientific wikis get bigger, but not necessarily more correct.
   - Hypothesis Wiki treats raw claims as untrusted until they pass provenance
     and scope checks.
2. Ingest demo
   - Run MLPerf v5.1 ingest.
   - Show 6 validated AI benchmark claims with source URLs, exact evidence
     spans, hardware scope, benchmark scope, and Offline/Server scenario scope.
3. Query demo before improvement
   - Run `python3 demo.py`.
   - Show v1 answer overclaims because the distiller erased scope.
4. Self-improve step
   - Show feedback: 4 gate rejections plus critic notes.
   - Show `SKILL.proposed.md` generated from that feedback.
5. Query demo after improvement
   - Show the improved answer preserves scope and negative evidence.
   - Show hygiene 0.15 -> 1.00, contradictions 0 -> 3, retired claims 0 -> 1.
6. What is next
   - Replace the controlled AX-17 corpus with an external benchmark harness
     using empirical ML/reproducibility datasets.
   - Gate future skill revisions on held-out accuracy, not internal score alone.

## Links

Repo:

https://github.com/gorajing/hypothesis-wiki

Slides / writeup:

TBD

Anything else:

- `docs/COGNEE_REDIS_SPIKE.md`
- `docs/REAL_RESEARCH_INGESTION.md`
- `docs/PROVENANCE_CONTRACT.md`
