# Demo Script

## 3-Minute Pitch

### 0:00-0:25

Most science-agent demos optimize for more memory. That is dangerous. Science does not just need more recall; it needs memory that preserves scope, negative evidence, and contradictions.

Hypothesis Wiki gets more correct over time, not just bigger.

### 0:25-0:55

Architecture:

```text
Redis = lab scratchpad
Cognee = trusted graph
Distillation gate = scientific judgment
```

Every raw paper and candidate claim starts in Redis session memory. Only attributed, scoped, testable claims pass into Cognee's permanent graph.

### 0:55-1:45

Demo question:

```text
Should AX-17 be used for high-temperature battery cells?
```

Run 1 sees a positive paper and overclaims:

```text
AX-17 improves battery stability and should be used.
```

Lint catches the scientific error:

```text
Missing scope: below 40C, electrolyte E1
Omitted evidence: degradation at 60C
Action: retire broad claim
```

### 1:45-2:30

The critic records feedback and the distiller improves:

```text
Preserve experimental conditions.
Never collapse conditional findings into universal claims.
Promote negative results as first-class evidence.
```

Run 2 answer:

```text
AX-17 is supported only below 40C with electrolyte E1. High-temperature and E2 evidence is negative or non-replicating.
```

### 2:30-3:00

Scoreboard:

```text
Retrieval score:     flat
Hypothesis hygiene: up
Scope errors:       down
Contradictions:     caught
Retired claims:     tracked
```

Closing:

```text
Cognee gives us durable graph memory. Redis gives us session memory. The unique piece is the distillation policy between them: a wiki that learns what not to promote.
```

