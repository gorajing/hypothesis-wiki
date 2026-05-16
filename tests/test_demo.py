"""compose_answer must be coherent: supporting conditions come only from
promoted positive hypotheses, negatives are described as negatives, and an
empty trusted graph yields the ungrounded fallback overclaim.
"""

import json
from pathlib import Path

from demo import DemoGraphState, claim_from_card, compose_answer

CARDS = {c["paper_id"]: c for c in json.loads((Path(__file__).parent.parent / "data" / "demo_mlperf_cards.json").read_text())}


def _trusted(graph, pid):
    graph.remember({**claim_from_card(CARDS[pid]), "status": "trusted"})


def test_empty_graph_yields_ungrounded_overclaim():
    assert "all Llama2 serving workloads" in compose_answer(DemoGraphState())


def test_supporting_scope_excludes_negative_claim_conditions():
    graph = DemoGraphState()
    _trusted(graph, "mlperf_demo_a")  # positive hypothesis: MI325X / Llama2 / Offline
    _trusted(graph, "mlperf_demo_d")  # negative_result: Offline does not generalize
    answer = compose_answer(graph).lower()

    # Scoped support is real and scorer-valid.
    assert "mi325x" in answer and "offline" in answer
    assert "do not generalize" in answer
    # Negative-claim conditions must NOT be presented as supporting scope.
    assert "serving workload distinction" not in answer
