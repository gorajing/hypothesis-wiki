import json

from build_science_database import DEFAULT_SOURCES, ROOT, build_database
from source_spans import validate_claims_against_cards


def test_science_claim_database_summary_matches_real_fixtures():
    database = build_database([(ROOT / cards, ROOT / claims) for cards, claims in DEFAULT_SOURCES])

    assert database["summary"] == {
        "paper_count": 6,
        "claim_count": 6,
        "provenance_valid_claims": 6,
        "trusted_graph_ready_claims": 6,
        "offline_benchmark_claims": 3,
        "server_benchmark_claims": 3,
        "safety_risk_claims": 0,
        "supported_efficacy_claims": 0,
        "supporting_evidence_claims": 0,
        "promotion_status_counts": {"promote": 6},
        "audit_verdict_counts": {
            "offline_benchmark_result": 3,
            "server_benchmark_result": 3,
        },
    }


def test_committed_science_claim_database_is_regenerable():
    expected = json.loads((ROOT / "data" / "science_claim_audit_db.json").read_text())
    regenerated = build_database([(ROOT / cards, ROOT / claims) for cards, claims in DEFAULT_SOURCES])

    assert regenerated == expected


def test_science_claim_database_records_keep_verbatim_evidence_spans():
    database = json.loads((ROOT / "data" / "science_claim_audit_db.json").read_text())

    for cards_file, claims_file in DEFAULT_SOURCES:
        cards = json.loads((ROOT / cards_file).read_text())
        claims = json.loads((ROOT / claims_file).read_text())
        assert validate_claims_against_cards(claims, cards) == []

    records = database["records"]
    assert all(record["evidence_span_valid"] is True for record in records)
    assert all(record["evidence_start"] < record["evidence_end"] for record in records)
    assert all(record["trusted_graph_ready"] is True for record in records)
    assert {record["audit_verdict"] for record in records} == {
        "offline_benchmark_result",
        "server_benchmark_result",
    }
    assert all("MLPerf Inference v5.1" in record["scope_conditions"] for record in records)
