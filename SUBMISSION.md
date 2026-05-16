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

The distillation gate's rejection reasons and the critic's notes are the
feedback signal. `propose_skill_revision(feedback)` derives a stronger
distiller skill from exactly those signals (and only those — unrelated
feedback is a no-op), the skill is written to disk, and the next run is
distilled with it. The improvement is a measured consequence of the skill
change, not a hand-written before/after.

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

The loop is executed, not scripted. `demo.py` runs the distiller with the
real v1 skill, gates every claim through `should_distill`, derives the
critic score from graph state, proposes a revised skill **from that
feedback**, writes it to `my_skills/hypothesis_distiller/SKILL.proposed.md`,
and re-runs with it.

```text
Run 1 (SKILL.md / v1)
  distiller drops scope -> gate rejects all 4 claims
  answer (from quarantine): AX-17 improves battery stability and should be
    used for high-temperature cells.

Self-improvement
  feedback = 4 gate rejections + 2 critic notes
  propose_skill_revision(feedback) -> SKILL.proposed.md (scope-preserving)

Run 2 (SKILL.proposed.md / applied)
  scope preserved -> gate promotes 4 claims, 3 contradictions surfaced,
    broad claim retired
  answer: AX-17 is supported only under 25C, coin cell, electrolyte E1;
    high-temperature, E2, and pouch-cell evidence is negative or
    non-replicating.
```

Score (every value computed from graph state; no hardcoded numbers):

```text
retrieval_score:        0.70 -> 0.70
hypothesis_hygiene:     0.15 -> 1.00
scope_errors:           1    -> 0
contradictions_caught:  0    -> 3
retired_claims:         0    -> 1
```

Retrieval is deliberately flat: the improved answer is more cautious, not
less retrieved, which closes the obvious "you just retrieved less" objection.

