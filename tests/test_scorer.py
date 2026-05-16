"""Behavior tests for the honest, graph-derived scorer.

These pin the contract that score_answer derives its metrics from real
graph state (trusted claims + retirements), NOT from a caller-supplied
`improved` flag. The relational assertions are intentionally float-tolerant.
"""

import json
from pathlib import Path

from critic import score_answer
from demo import DemoGraphState, claim_from_card

CARDS = json.loads((Path(__file__).parent.parent / "data" / "paper_cards.json").read_text())
CARD = {c["paper_id"]: c for c in CARDS}

OVERCLAIM = "AX-17 improves battery stability and should be used for high-temperature cells."
SCOPED = (
    "AX-17 is supported only below 40C with electrolyte E1; high-temperature "
    "and E2 evidence is negative or non-replicating."
)


def _trusted(graph: DemoGraphState, paper_id: str) -> None:
    claim = claim_from_card(CARD[paper_id])
    graph.remember({**claim, "status": "trusted"})


def test_retired_claims_reflects_graph_not_a_flag():
    graph = DemoGraphState()
    _trusted(graph, "paper_a")
    assert score_answer(OVERCLAIM, graph).retired_claims == 0

    graph.retire("claim_paper_a", "overgeneralized", "claim_paper_b")
    graph.retire("claim_paper_x", "stale", "claim_paper_c")
    assert score_answer(SCOPED, graph).retired_claims == 2


def test_contradictions_counted_from_graph_not_from_flag():
    positive_only = DemoGraphState()
    _trusted(positive_only, "paper_a")
    assert score_answer(SCOPED, positive_only).contradictions_caught == 0

    with_conflicts = DemoGraphState()
    _trusted(with_conflicts, "paper_a")  # positive hypothesis
    _trusted(with_conflicts, "paper_b")  # conditional evidence vs same outcome
    _trusted(with_conflicts, "paper_d")  # negative result vs same outcome
    assert score_answer(SCOPED, with_conflicts).contradictions_caught == 2


def test_overclaim_penalized_more_when_contradicting_evidence_exists():
    early = DemoGraphState()
    _trusted(early, "paper_a")
    late = DemoGraphState()
    for pid in ("paper_a", "paper_b", "paper_c", "paper_d"):
        _trusted(late, pid)

    # Same overclaiming answer; later graph has negative evidence to ignore.
    assert (
        score_answer(OVERCLAIM, late).scope_errors
        > score_answer(OVERCLAIM, early).scope_errors
    )


def test_scoped_answer_has_higher_hygiene_than_overclaim_on_same_graph():
    graph = DemoGraphState()
    for pid in ("paper_a", "paper_b", "paper_c", "paper_d"):
        _trusted(graph, pid)
    assert (
        score_answer(SCOPED, graph).hypothesis_hygiene
        > score_answer(OVERCLAIM, graph).hypothesis_hygiene
    )


def test_ungrounded_overclaim_against_empty_graph_scores_low():
    empty = DemoGraphState()
    over = score_answer(OVERCLAIM, empty)
    # No trusted grounding at all: the answer is not "fine because nothing
    # contradicts it" -- it is unsupported. Must be flagged and score low.
    assert any("ground" in n for n in over.notes)
    assert over.scope_errors >= 1

    full = DemoGraphState()
    for pid in ("paper_a", "paper_b", "paper_c", "paper_d"):
        _trusted(full, pid)
    assert over.hypothesis_hygiene < score_answer(SCOPED, full).hypothesis_hygiene


def test_retrieval_stays_flat_between_overclaim_and_scoped():
    graph = DemoGraphState()
    for pid in ("paper_a", "paper_b", "paper_c", "paper_d"):
        _trusted(graph, pid)
    over = score_answer(OVERCLAIM, graph).retrieval_score
    scoped = score_answer(SCOPED, graph).retrieval_score
    # Design intent (DATA_CONTRACTS.md): retrieval must not collapse when the
    # answer becomes more cautious, or "you just retrieved less" is a valid jab.
    assert abs(over - scoped) <= 0.1
