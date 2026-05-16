# Implementation Plan

## Build Order

### 1. Cognee + Redis Spike

Goal: prove the judged surface before building features.

Minimum calls:

```python
await cognee.remember(raw_claim, session_id=run_id)
await cognee.remember(validated_claim)
```

Decision to confirm:

- `session_id` memory remains session-scoped, or
- `session_id` memory auto-syncs to graph and direct `redis-py` is needed for quarantine.

Do not spend more than 20 minutes here.

### 2. Deterministic Local Loop

Build and keep the deterministic path working:

```text
source result cards -> candidate claims -> should_distill -> graph -> lint -> score
```

This is the fallback demo and the test harness for Cognee/Redis wiring.

### 3. Thin Cognee/Redis Adapter

Replace the mock store under the deterministic loop:

- Redis/session: raw cards, candidate claims, lint issues, run scores
- Cognee/permanent: promoted claims, contradictions, retired claims, skill feedback

Keep the interface small.

### 4. Skill Improvement

Required demo behavior:

- v1 distiller overgeneralizes
- critic identifies missing scope and negative evidence
- v2 distiller preserves scope and negative evidence
- score improves

Implementation preference:

1. record real `SkillRunEntry`
2. use Cognee `improve_skill(apply=True)` if it works
3. fallback to deterministic v1 -> v2 skill swap

## Cut Lines

Never cut:

- Redis quarantine
- Cognee promotion
- `should_distill()`
- lint output
- before/after score table

Cut first:

- semantic novelty scoring
- full-text ingestion
- UI
- live LLM extraction
- broad source search

## Done Definition

The hackathon artifact is shippable when:

```text
python3 demo.py
```

prints:

```text
Run 1: overgeneralized answer
Lint: missing scope / omitted negative evidence
Run 2: scoped answer
Hypothesis hygiene improves
Redis and Cognee roles are visible in output
```
