import json
from pathlib import Path

from critic import lint_claims, score_answer
from distillation_policy import should_distill
from distiller import distill, propose_skill_revision

ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "paper_cards.json"
SKILL_DIR = ROOT / "my_skills" / "hypothesis_distiller"
V1_PATH = SKILL_DIR / "SKILL.md"
PROPOSED_PATH = SKILL_DIR / "SKILL.proposed.md"


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
    """Reference scope-preserving mapping (equivalent to distilling with v2).

    Retained for tests and as the honest baseline the distiller's v2 skill
    is expected to reproduce.
    """
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


def run_pass(cards, skill_text, graph, session_id):
    """Ingest -> distill (per skill) -> gate -> promote. Returns (candidates, rejections)."""
    candidates: list[dict] = []
    rejections: list[str] = []
    for card in cards:
        graph.remember(card, session_id=session_id)
        claim = distill(card, skill_text)
        candidates.append(claim)
        graph.remember(claim, session_id=session_id)
        decision = should_distill(claim, graph)
        if decision.promote:
            graph.remember({**claim, "status": "trusted", "distill_reason": decision.reason})
        else:
            rejections.append(f"{claim['id']}: {decision.reason}")
    return candidates, rejections


def compose_answer(graph: DemoGraphState) -> str:
    """Deterministically answer from the *trusted* graph only.

    With nothing trusted, the agent falls back to the optimistic raw finding
    from quarantine -- an ungrounded overclaim. With scoped + negative
    evidence promoted, the answer carries the scope and the negatives.
    """
    trusted = graph.trusted_graph
    if not trusted:
        return "AX-17 improves battery stability and should be used for high-temperature cells."

    support_scopes = sorted(
        {
            cond
            for claim in trusted
            if claim.get("kind") == "hypothesis" and claim.get("direction") == "improves"
            for cond in claim.get("scope_conditions", [])
        }
    )
    has_negative = any(
        claim.get("kind") == "negative_result"
        or (claim.get("kind") == "evidence" and claim.get("direction") in {"conditional", "no_benefit"})
        for claim in trusted
    )

    if support_scopes:
        head = f"AX-17 is supported only under {', '.join(support_scopes)}"
    else:
        head = "AX-17 is not supported as a general high-temperature additive"
    if has_negative:
        return head + "; high-temperature, E2, and pouch-cell evidence is negative or non-replicating."
    return head + "."


def print_score(label: str, score) -> None:
    print(label)
    print(f"  retrieval_score:       {score.retrieval_score:.2f}")
    print(f"  hypothesis_hygiene:    {score.hypothesis_hygiene:.2f}")
    print(f"  scope_errors:          {score.scope_errors}")
    print(f"  contradictions_caught: {score.contradictions_caught}")
    print(f"  retired_claims:        {score.retired_claims}")
    for note in score.notes:
        print(f"    - {note}")


def main() -> None:
    cards = json.loads(DATA_PATH.read_text())
    v1_skill = V1_PATH.read_text()
    graph = DemoGraphState()

    print("Hypothesis Wiki demo")
    print("=" * 38)
    print()
    print("Research question: Should AX-17 be used for high-temperature battery cells?")
    print()

    # ---- Run 1: weak v1 distiller -------------------------------------------
    candidates_v1, rejections_v1 = run_pass(cards, v1_skill, graph, "run_001")
    run1_answer = compose_answer(graph)
    run1_score = score_answer(run1_answer, graph)

    print("Run 1  (skill: SKILL.md / v1)")
    print(f"  answer: {run1_answer}")
    print("  lint on distilled candidates:")
    for issue in lint_claims(candidates_v1):
        print(f"    - {issue['code']}: {issue['claim']} ({issue['severity']})")
    print("  distillation gate rejections:")
    for reason in rejections_v1:
        print(f"    - {reason}")
    print_score("  run 1 score", run1_score)
    print()

    # ---- Self-improvement: propose a better skill FROM the feedback ----------
    feedback = rejections_v1 + run1_score.notes
    proposed_skill = propose_skill_revision(feedback)
    PROPOSED_PATH.write_text(proposed_skill)

    print("Self-improvement")
    print(f"  critic + gate feedback: {len(feedback)} signals")
    print(f"  proposed skill written to: {PROPOSED_PATH.relative_to(ROOT)}")
    print("  proposed rules:")
    for line in proposed_skill.splitlines():
        if line.strip().startswith(tuple("12345")):
            print(f"    {line.strip()}")
    print()

    # ---- Run 2: apply the proposed skill ------------------------------------
    graph2 = DemoGraphState()
    _, rejections_v2 = run_pass(cards, proposed_skill, graph2, "run_002")

    # A promoted positive hypothesis contradicted by later evidence is retired.
    positive_outcomes = {
        c["outcome"]
        for c in graph2.trusted_graph
        if c.get("kind") == "hypothesis" and c.get("direction") == "improves"
    }
    for claim in list(graph2.trusted_graph):
        contradicts = next(
            (
                e
                for e in graph2.trusted_graph
                if e.get("outcome") in positive_outcomes
                and (
                    e.get("kind") == "negative_result"
                    or (e.get("kind") == "evidence" and e.get("direction") in {"conditional", "no_benefit"})
                )
            ),
            None,
        )
        if claim.get("kind") == "hypothesis" and claim.get("direction") == "improves" and contradicts:
            graph2.retire(claim["id"], "broad claim narrowed by later evidence", contradicts["id"])
            break

    run2_answer = compose_answer(graph2)
    run2_score = score_answer(run2_answer, graph2)

    print("Run 2  (skill: SKILL.proposed.md / applied)")
    print(f"  answer: {run2_answer}")
    if rejections_v2:
        print("  distillation gate rejections:")
        for reason in rejections_v2:
            print(f"    - {reason}")
    print_score("  run 2 score", run2_score)
    print()

    print("Before / after  (all values computed from graph state)")
    print(f"  retrieval_score:       {run1_score.retrieval_score:.2f} -> {run2_score.retrieval_score:.2f}")
    print(f"  hypothesis_hygiene:    {run1_score.hypothesis_hygiene:.2f} -> {run2_score.hypothesis_hygiene:.2f}")
    print(f"  scope_errors:          {run1_score.scope_errors} -> {run2_score.scope_errors}")
    print(f"  contradictions_caught: {run1_score.contradictions_caught} -> {run2_score.contradictions_caught}")
    print(f"  retired_claims:        {run1_score.retired_claims} -> {run2_score.retired_claims}")
    print()

    print("Memory usage")
    print(f"  Redis session events (run 1):  {len(graph.redis_session)}")
    print(f"  Redis session events (run 2):  {len(graph2.redis_session)}")
    print(f"  Cognee trusted claims (run 1): {len(graph.trusted_graph)}")
    print(f"  Cognee trusted claims (run 2): {len(graph2.trusted_graph)}")
    print(f"  Retired claims:                {len(graph2.retirements)}")


if __name__ == "__main__":
    main()
