import json
from pathlib import Path

from distillation_policy import should_distill
from source_spans import validate_claims_against_cards


ROOT = Path(__file__).parent.parent


class EmptyGraph:
    def has_duplicate(self, claim: dict) -> bool:
        return False

    def has_conflict(self, claim: dict) -> bool:
        return False


def test_maude_claims_have_verbatim_source_spans():
    cards = json.loads((ROOT / "data" / "maude_2018_cart.json").read_text())
    claims = json.loads((ROOT / "data" / "maude_2018_claims.json").read_text())
    assert validate_claims_against_cards(claims, cards) == []


def test_distillation_rejects_unvalidated_real_claim_span():
    claim = {
        "id": "claim_unsupported",
        "kind": "hypothesis",
        "text": "Unsupported claim",
        "source": "maude_2018_cart",
        "outcome": "overall remission rate",
        "scope_conditions": ["within 3 months"],
        "evidence_span": "not a real quote",
    }

    decision = should_distill(claim, EmptyGraph())
    assert decision.promote is False
    assert "evidence span" in decision.reason

