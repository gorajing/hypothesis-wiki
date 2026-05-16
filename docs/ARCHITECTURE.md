# Architecture

## Product Claim

Benchmark Claim Wiki is a memory layer for AI benchmark agents. It does not claim to invent new benchmarks. It preserves the evidence discipline needed to answer benchmark questions without losing model, hardware, scenario, metric, or source scope.

The core demo claim:

```text
Every wiki gets bigger. This one gets less wrong.
```

## Components

### Redis Session Memory

Redis stores untrusted, run-scoped material:

- raw MLPerf result cards
- candidate extracted claims
- rejected claims and rejection reasons
- lint issues
- critic feedback
- run scores

This is the session quarantine. Claims in Redis are not trusted wiki knowledge.

### Distillation Gate

`should_distill()` is the judged mechanism. It decides which Redis session events are promoted into permanent graph memory.

Hard gates:

- source attribution is present
- claim has a benchmark outcome or explicit evidence
- benchmark, model, hardware, scenario, and metric scope are preserved when required
- near-duplicate claims are rejected
- conditional or contrary evidence is not erased
- contradictions are marked open, resolved, or converted into retirement edges

### Cognee Graph

Cognee stores durable trusted memory:

- promoted benchmark claims
- evidence nodes
- source links
- scope conditions
- contradictions
- retired claims
- skill feedback and improvement proposals

### Lint

Lint checks the graph for benchmark hygiene:

- missing source
- missing scope condition
- overgeneralized benchmark claim
- contradiction with promoted evidence
- omitted scenario-specific result
- duplicate claim
- stale claim that should be retired

### Self-Improvement

The deterministic demo uses a controlled v1 -> v2 distiller change so the live presentation cannot fail because of API or LLM variance.

The live Cognee/Redis spike proves the same storage split with real services: Redis for session memory, Cognee for trusted graph memory, no silent in-memory fallback.

## Data Flow

```text
1. Ingest MLPerf result card
2. Store raw card in Redis session memory
3. Map card to candidate benchmark claim
4. Store candidate claim in Redis session memory
5. Run should_distill(candidate, graph_state)
6. Promote accepted claims to Cognee graph
7. Lint promoted graph against new evidence
8. Score answer and run trace
9. Record critic feedback
10. Improve distiller skill
11. Re-run query and show score movement
```

## Non-Goals

- No UI for the hackathon version.
- No autonomous benchmark discovery claim.
- No dependency on a live LLM call during the judged demo.
- No silent fallback when Redis or Cognee are required.
