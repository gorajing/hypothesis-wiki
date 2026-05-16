import json
from pathlib import Path

from distillation_policy import should_distill
from research_claim_extractor import extract_claims_from_cards
from source_spans import validate_claim_contract, validate_claims_against_cards


ROOT = Path(__file__).parent.parent
REAL_FIXTURES = [
    ("mlperf_v5_1_cards.json", "mlperf_v5_1_claims.json"),
]


class EmptyGraph:
    def has_duplicate(self, claim: dict) -> bool:
        return False

    def has_conflict(self, claim: dict) -> bool:
        return False


def _read_data(name: str):
    return json.loads((ROOT / "data" / name).read_text())


def test_real_claims_have_verbatim_source_spans_and_contract_fields():
    for cards_file, claims_file in REAL_FIXTURES:
        cards = _read_data(cards_file)
        claims = _read_data(claims_file)
        assert validate_claims_against_cards(claims, cards) == []


def test_curated_extractor_regenerates_committed_real_claims():
    for cards_file, claims_file in REAL_FIXTURES:
        cards = _read_data(cards_file)
        expected_claims = _read_data(claims_file)
        assert extract_claims_from_cards(cards, extractor="curated") == expected_claims


def test_contract_reports_missing_required_provenance_fields():
    claim = _read_data("mlperf_v5_1_claims.json")[0]
    malformed = {**claim, "evidence_span_valid": False}
    del malformed["paper_title"]

    issues = validate_claim_contract(malformed)
    codes = [issue.code for issue in issues]

    assert "missing_contract_field" in codes
    assert "invalid_evidence_span" in codes


def test_distillation_rejects_unvalidated_real_claim_span():
    claim = {
        "id": "claim_unsupported",
        "kind": "hypothesis",
        "text": "Unsupported claim",
        "source": "mlperf_v5_1_0001_mi300x_llama2_offline",
        "outcome": "llama2-70b-99 throughput",
        "scope_conditions": ["MLPerf Inference v5.1", "Offline scenario"],
        "evidence_span": "not a real quote",
    }

    decision = should_distill(claim, EmptyGraph())
    assert decision.promote is False
    assert "evidence span" in decision.reason
