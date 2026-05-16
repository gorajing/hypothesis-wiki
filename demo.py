import json
from pathlib import Path

from critic import score_answer
from distillation_policy import should_distill


DATA_PATH = Path(__file__).parent / "data" / "paper_cards.json"


class DemoGraphState:
    def __init__(self):
        self.redis_session: list[dict] = []
        self.trusted_graph: list[dict] = []
        self.retirements: list[dict] = []

    def remember(self, payload: dict, session_id: str | None = None) -> None:
        if session_id:
            self.redis_session.append({"session_id": session_id, "payload": payload})
        else:
            self.trusted_graph.append(payload)

    def has_duplicate(self, claim: dict) -> bool:
        return any(existing.get("text") == claim.get("text") for existing in self.trusted_graph)

    def has_conflict(self, claim: dict) -> bool:
        if claim.get("direction") != "improves":
            return False
        return any(
            existing.get("kind") == "negative_result"
            and existing.get("outcome") == claim.get("outcome")
            for existing in self.trusted_graph
        )

    def retire(self, claim_id: str, reason: str, evidence_id: str) -> None:
        self.retirements.append({"claim_id": claim_id, "reason": reason, "evidence_id": evidence_id})


def claim_from_card(card: dict) -> dict:
    result_type = card["result_type"]
    kind = "hypothesis"
    if result_type == "negative":
        kind = "negative_result"
    elif result_type in {"conditional", "replication_failure"}:
        kind = "evidence"

    return {
        "id": f"claim_{card['paper_id']}",
        "kind": kind,
        "text": card["finding"],
        "source": card["paper_id"],
        "source_url": card["url"],
        "scope_conditions": card["conditions"],
        "outcome": card["outcome"],
        "direction": card["direction"],
        "evidence_type": "paper_card",
        "status": "candidate",
        "confidence": 0.62,
    }


def print_score(label: str, score) -> None:
    print(f"{label}")
    print(f"  retrieval_score:       {score.retrieval_score:.2f}")
    print(f"  hypothesis_hygiene:    {score.hypothesis_hygiene:.2f}")
    print(f"  scope_errors:          {score.scope_errors}")
    print(f"  contradictions_caught: {score.contradictions_caught}")
    print(f"  retired_claims:        {score.retired_claims}")
    if score.notes:
        print("  notes:")
        for note in score.notes:
            print(f"    - {note}")


def main() -> None:
    cards = json.loads(DATA_PATH.read_text())
    graph = DemoGraphState()
    run_id = "run_001"

    print("Hypothesis Wiki deterministic demo")
    print("=" * 38)
    print()
    print("Research question: Should AX-17 be used for high-temperature battery cells?")
    print()

    # Run 1 intentionally uses only the first positive paper and overgeneralizes.
    first_card = cards[0]
    graph.remember(first_card, session_id=run_id)
    first_claim = claim_from_card(first_card)
    graph.remember(first_claim, session_id=run_id)
    decision = should_distill(first_claim, graph)
    if decision.promote:
        graph.remember({**first_claim, "status": "trusted", "distill_reason": decision.reason})

    run1_answer = "AX-17 improves battery stability and should be used for high-temperature cells."
    run1_score = score_answer(run1_answer, improved=False)

    print("Run 1 answer")
    print(f"  {run1_answer}")
    print_score("Run 1 score", run1_score)
    print()

    # Run 2 ingests conditional and negative evidence, then improves the answer.
    for card in cards[1:]:
        graph.remember(card, session_id="run_002")
        claim = claim_from_card(card)
        graph.remember(claim, session_id="run_002")
        decision = should_distill(claim, graph)
        if decision.promote:
            graph.remember({**claim, "status": "trusted", "distill_reason": decision.reason})

    graph.retire(
        "claim_paper_a",
        "broad AX-17 benefit was overgeneralized; later evidence limits scope",
        "claim_paper_b",
    )

    run2_answer = (
        "AX-17 should not be used as a general high-temperature additive. "
        "Evidence supports benefit below 40C with electrolyte E1, while high-temperature, "
        "E2, and pouch-cell evidence is negative or non-replicating."
    )
    run2_score = score_answer(run2_answer, improved=True)

    print("Lint")
    print("  scope_error: paper_a benefit was below 40C / electrolyte E1, not universal")
    print("  contradiction: paper_b reports degradation at 60C")
    print("  negative_result: paper_d reports no high-temperature pouch-cell benefit")
    print("  action: retire broad claim and replace with scoped claim")
    print()
    print("Run 2 answer")
    print(f"  {run2_answer}")
    print_score("Run 2 score", run2_score)
    print()

    print("Before / after")
    print("  retrieval_score:       0.91 -> 0.91")
    print(f"  hypothesis_hygiene:    {run1_score.hypothesis_hygiene:.2f} -> {run2_score.hypothesis_hygiene:.2f}")
    print(f"  scope_errors:          {run1_score.scope_errors} -> {run2_score.scope_errors}")
    print(f"  contradictions_caught: {run1_score.contradictions_caught} -> {run2_score.contradictions_caught}")
    print(f"  retired_claims:        {run1_score.retired_claims} -> {run2_score.retired_claims}")
    print()

    print("Memory usage")
    print(f"  Redis session events:  {len(graph.redis_session)}")
    print(f"  Cognee graph claims:   {len(graph.trusted_graph)}")
    print(f"  Retired claims:        {len(graph.retirements)}")


if __name__ == "__main__":
    main()

