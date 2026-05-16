# Hypothesis Wiki

A self-correcting scientific knowledge wiki for the Cognee x Redis hackathon.

Most knowledge wikis get bigger. Hypothesis Wiki is designed to get more correct. Redis holds tentative scientific claims in session memory. A distillation gate promotes only attributed, scoped, testable claims into the Cognee graph. Linting and critic feedback catch overclaims, contradictions, and missing negative evidence. The skill loop then improves the distiller so the same query gets a safer answer on the next run.

## Demo Target

Research question:

```text
Should AX-17 be used for high-temperature battery cells?
```

The baseline answer overclaims from a positive paper. The improved answer preserves the scope conditions and negative evidence:

```text
AX-17 only has support below 40C with electrolyte E1; high-temperature and E2 evidence is negative or non-replicating.
```

## Quickstart

The deterministic demo has no external dependencies:

```bash
python3 demo.py
```

Expected headline:

```text
Hypothesis hygiene: 0.35 -> 0.88
Scope errors:       2 -> 0
Contradictions:     0 -> 2
Retired claims:     0 -> 1
```

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
distillation_policy.py                 promotion gate from Redis to Cognee
critic.py                              lint checks and scoring
demo.py                                deterministic before/after demo
docs/ARCHITECTURE.md                   design overview
docs/DATA_CONTRACTS.md                 claim and memory schemas
docs/IMPLEMENTATION_PLAN.md            build order and cut lines
docs/DEMO_SCRIPT.md                    3-minute presentation script
SUBMISSION.md                          hackathon submission draft
my_skills/hypothesis_distiller/        baseline and improved skill text
```

## Hackathon Framing

Redis is not just a cache. It is the scientific quarantine layer: raw papers, candidate hypotheses, run traces, and critic notes live there until they earn permanence.

Cognee is the trusted graph: promoted hypotheses, evidence links, contradiction edges, retired claims, and skill improvements live there.

The unique angle is the distillation policy between them.

