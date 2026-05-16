# Hypothesis Wiki

## What We Built

Hypothesis Wiki is a self-correcting scientific knowledge wiki. It uses Redis as a session-memory quarantine for tentative scientific claims and Cognee as the trusted graph for promoted hypotheses, evidence, contradictions, retired claims, and skill feedback.

The wiki improves by learning which claims deserve promotion. It rewards source attribution, scope preservation, negative evidence, and contradiction handling.

## Ingest

Scientific paper cards are ingested into Redis session memory. Each card is deterministically transformed into typed candidate claims:

- hypothesis
- evidence
- negative result
- contradiction
- retired claim

Raw cards and candidate claims remain untrusted until the distillation gate evaluates them.

## Query + Self-Improve

Queries read from the trusted Cognee graph. A critic scores the answer for scientific hygiene:

- did it preserve source attribution?
- did it preserve experimental scope?
- did it include negative evidence?
- did it avoid overgeneralizing?
- did it retire contradicted claims?

Low-scoring runs produce skill feedback. The improved distiller preserves scope conditions and promotes negative results as first-class evidence.

## Lint

The lint pass catches:

- missing source
- missing scope condition
- overgeneralized claim
- contradiction
- omitted negative result
- duplicate claim
- claim that should be retired

## Redis Usage

Redis stores:

- raw paper cards
- candidate claims
- rejected claims and reasons
- lint issues
- critic feedback
- run score history

Redis is the lab scratchpad and quarantine layer.

## Cognee Usage

Cognee stores:

- promoted hypotheses
- evidence nodes
- scope conditions
- contradiction edges
- retired claims
- skill feedback and improvement proposals

Cognee is the trusted scientific graph.

## Self-Improvement Evidence

Headline demo:

```text
Research question: Should AX-17 be used for high-temperature battery cells?

Run 1 answer:
AX-17 improves battery stability and should be used for high-temperature cells.

Lint:
Missing scope condition below 40C / electrolyte E1.
Omitted negative evidence at 60C and E2.

Run 2 answer:
AX-17 is supported only below 40C with electrolyte E1. High-temperature and E2 evidence is negative or non-replicating.
```

Score:

```text
Retrieval score:        0.91 -> 0.91
Hypothesis hygiene:     0.35 -> 0.88
Scope errors:           2    -> 0
Contradictions caught:  0    -> 2
Retired claims:         0    -> 1
```

