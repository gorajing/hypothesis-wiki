"""compose_answer must be coherent: supporting conditions come only from
promoted positive hypotheses, negatives are described as negatives, and an
empty trusted graph yields the ungrounded fallback overclaim.
"""

import json
from pathlib import Path

from demo import DemoGraphState, claim_from_card, compose_answer

CARDS = {c["paper_id"]: c for c in json.loads((Path(__file__).parent.parent / "data" / "paper_cards.json").read_text())}


def _trusted(graph, pid):
    graph.remember({**claim_from_card(CARDS[pid]), "status": "trusted"})


def test_empty_graph_yields_ungrounded_overclaim():
    assert "should be used for high-temperature" in compose_answer(DemoGraphState())


def test_supporting_scope_excludes_negative_claim_conditions():
    graph = DemoGraphState()
    _trusted(graph, "paper_a")  # positive hypothesis: 25C / coin cell / E1
    _trusted(graph, "paper_d")  # negative_result: pouch cell / high-temp
    answer = compose_answer(graph).lower()

    # Scoped support is real and scorer-valid.
    assert "25c" in answer and "electrolyte e1" in answer
    assert "negative or non-replicating" in answer
    # Negative-claim conditions must NOT be presented as supporting scope.
    assert "pouch cell" not in answer
