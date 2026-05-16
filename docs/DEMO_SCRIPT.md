# Demo Script

## 3-Minute Pitch

### 0:00-0:25

AI benchmark claims spread fast, but the scope often gets lost. A result that is valid for one benchmark, model, hardware setup, scenario, and metric can turn into a broad claim about "best inference performance."

Benchmark Claim Wiki gets more correct over time, not just bigger.

### 0:25-0:55

Architecture:

```text
Redis = session quarantine
Cognee = trusted graph
Distillation gate = promotion policy
```

Every raw result card and candidate claim starts in Redis session memory. Only attributed, scoped, testable claims pass into Cognee's permanent graph.

### 0:55-1:45

Demo question:

```text
Can the top MLPerf Offline Llama2 result be generalized to all serving workloads?
```

Run 1 overclaims:

```text
MI325X delivers top Llama2 throughput and should be used for all Llama2 serving workloads.
```

Lint and critic feedback catch the error:

```text
Missing scope: MLPerf Inference v5.1, model, hardware, scenario, metric
Omitted evidence: Server is a separate lower result
Action: retire broad serving-workload claim
```

### 1:45-2:30

The critic records feedback and the distiller improves:

```text
Preserve benchmark, model, hardware, scenario, and metric.
Never collapse scenario-specific findings into universal claims.
Promote conditional or contrary results as first-class evidence.
```

Run 2 answer:

```text
MI325X Llama2 performance is supported only under MLPerf Inference v5.1, llama2-70b-99, Offline scenario, 8x AMD Instinct MI325X; Offline results do not generalize to Server serving workloads because MLPerf reports a separate lower Server result.
```

### 2:30-3:00

Scoreboard:

```text
Retrieval score:     up
Hypothesis hygiene: up
Scope errors:       down
Contradictions:     caught
Retired claims:     tracked
```

Closing:

```text
Cognee gives us durable graph memory. Redis gives us session memory. The unique piece is the distillation policy between them: a wiki that learns what not to promote.
```
