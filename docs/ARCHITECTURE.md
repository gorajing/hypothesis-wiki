# Architecture

## Product Claim

Hypothesis Wiki is a scientific memory layer for research agents. It does not claim to discover new science on its own. It claims to preserve the evidence discipline a science agent needs before it can do novel research safely.

The core demo claim:

```text
Every wiki gets bigger. This one gets less wrong.
```

## Components

### Redis Session Memory

Redis stores untrusted, run-scoped material:

- raw paper cards
- candidate extracted claims
- rejected claims and rejection reasons
- lint issues
- critic feedback
- run scores

This is the lab scratchpad. Claims in Redis are not trusted wiki knowledge.

### Distillation Gate

`should_distill()` is the judged mechanism. It decides which Redis session events are promoted into permanent graph memory.

Hard gates:

- source attribution is present
- claim has a testable outcome or is explicit evidence
- scientific scope conditions are preserved when required
- near-duplicate claims are rejected
- negative evidence is not erased
- contradictions are marked open, resolved, or converted into retirement edges

### Cognee Graph

Cognee stores durable scientific memory:

- promoted hypotheses
- evidence nodes
- source links
- scope conditions
- contradictions
- retired claims
- skill feedback and improvement proposals

### Lint

Lint checks the graph for scientific hygiene:

- missing source
- missing scope condition
- overgeneralized hypothesis
- contradiction with promoted evidence
- omitted negative result
- duplicate claim
- stale claim that should be retired

### Self-Improvement

The deterministic demo uses a controlled v1 -> v2 distiller change so the live presentation cannot fail because of an API or LLM variance.

The Cognee integration should still record real `SkillRunEntry` feedback. If Cognee `improve_skill(apply=True)` works in the environment, it becomes the live mechanism. If not, the deterministic skill swap is the fallback with the same visible behavior.

## Data Flow

```text
1. Ingest paper card
2. Store raw card in Redis session memory
3. Deterministically map card to candidate claim
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
- No full PDF ingestion in the first demo path.
- No full Zuhn or Memric port.
- No claim of autonomous scientific discovery.
- No dependency on a live LLM call during the judged demo.

