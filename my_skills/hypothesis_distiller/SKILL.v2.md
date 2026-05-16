# Hypothesis Distiller v2

Extract benchmark findings as scoped, attributed hypotheses.

Rules:

1. Preserve benchmark conditions such as benchmark, hardware, model, scenario, metric, division, dataset, and run setting.
2. Never collapse a conditional finding into a universal claim.
3. Promote contrary or scenario-specific results as first-class evidence.
4. Mark contradictions explicitly instead of smoothing them away.
5. Retire broad claims when later evidence narrows or falsifies them.
6. Include the source card ID on every claim.

Output must distinguish:

- hypothesis
- evidence
- negative_result
- contradiction
- retired_claim
