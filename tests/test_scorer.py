"""Behavior tests for the honest, graph-derived scorer.

These pin the contract that score_answer derives its metrics from real
graph state (trusted claims + retirements), NOT from a caller-supplied
`improved` flag. The relational assertions are intentionally float-tolerant.
"""

import json
from pathlib import Path

from critic import score_answer
from demo import DemoGraphState, claim_from_card

CARDS = json.loads((Path(__file__).parent.parent / "data" / "demo_mlperf_cards.json").read_text())
CARD = {c["paper_id"]: c for c in CARDS}

OVERCLAIM = "MI325X delivers top Llama2 throughput and should be used for all Llama2 serving workloads."
SCOPED = (
    "MI325X Llama2 performance is supported only under MLPerf Inference v5.1, "
    "llama2-70b-99, Offline scenario, and 8x AMD Instinct MI325X; Offline "
    "results do not generalize to Server serving workloads."
)


def _trusted(graph: DemoGraphState, paper_id: str) -> None:
    claim = claim_from_card(CARD[paper_id])
    graph.remember({**claim, "status": "trusted"})


def test_retired_claims_reflects_graph_not_a_flag():
    graph = DemoGraphState()
    _trusted(graph, "mlperf_demo_a")
    assert score_answer(OVERCLAIM, graph).retired_claims == 0

    graph.retire("claim_mlperf_demo_a", "overgeneralized", "claim_mlperf_demo_b")
    graph.retire("claim_mlperf_demo_x", "stale", "claim_mlperf_demo_c")
    assert score_answer(SCOPED, graph).retired_claims == 2


def test_contradictions_counted_from_graph_not_from_flag():
    positive_only = DemoGraphState()
    _trusted(positive_only, "mlperf_demo_a")
    assert score_answer(SCOPED, positive_only).contradictions_caught == 0

    with_conflicts = DemoGraphState()
    _trusted(with_conflicts, "mlperf_demo_a")  # positive hypothesis
    _trusted(with_conflicts, "mlperf_demo_b")  # conditional evidence vs same outcome
    _trusted(with_conflicts, "mlperf_demo_d")  # negative result vs same outcome
    assert score_answer(SCOPED, with_conflicts).contradictions_caught == 2


def test_overclaim_penalized_more_when_contradicting_evidence_exists():
    early = DemoGraphState()
    _trusted(early, "mlperf_demo_a")
    late = DemoGraphState()
    for pid in ("mlperf_demo_a", "mlperf_demo_b", "mlperf_demo_c", "mlperf_demo_d"):
        _trusted(late, pid)

    # Same overclaiming answer; later graph has negative evidence to ignore.
    assert (
        score_answer(OVERCLAIM, late).scope_errors
        > score_answer(OVERCLAIM, early).scope_errors
    )


def test_scoped_answer_has_higher_hygiene_than_overclaim_on_same_graph():
    graph = DemoGraphState()
    for pid in ("mlperf_demo_a", "mlperf_demo_b", "mlperf_demo_c", "mlperf_demo_d"):
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
    for pid in ("mlperf_demo_a", "mlperf_demo_b", "mlperf_demo_c", "mlperf_demo_d"):
        _trusted(full, pid)
    assert over.hypothesis_hygiene < score_answer(SCOPED, full).hypothesis_hygiene


def test_retrieval_does_not_collapse_between_overclaim_and_scoped():
    graph = DemoGraphState()
    for pid in ("mlperf_demo_a", "mlperf_demo_b", "mlperf_demo_c", "mlperf_demo_d"):
        _trusted(graph, pid)
    over = score_answer(OVERCLAIM, graph).retrieval_score
    scoped = score_answer(SCOPED, graph).retrieval_score
    # Design intent (DATA_CONTRACTS.md): retrieval must not collapse when the
    # answer becomes scoped, or "you just retrieved less" is a valid objection.
    assert abs(over - scoped) <= 0.1
