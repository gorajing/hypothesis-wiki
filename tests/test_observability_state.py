from pathlib import Path

from observability.state import build_observability_state


def test_observability_state_matches_demo_before_after_scores():
    state = build_observability_state()

    run1 = state["runs"]["run_001"]
    run2 = state["runs"]["run_002"]

    assert run1["score"]["retrieval_score"] == 0.70
    assert run1["score"]["hypothesis_hygiene"] == 0.15
    assert run1["score"]["scope_errors"] == 1
    assert run1["score"]["contradictions_caught"] == 0
    assert run1["score"]["retired_claims"] == 0

    assert run2["score"]["retrieval_score"] == 1.00
    assert run2["score"]["hypothesis_hygiene"] == 1.00
    assert run2["score"]["scope_errors"] == 0
    assert run2["score"]["contradictions_caught"] == 3
    assert run2["score"]["retired_claims"] == 1

    assert [row["display"] for row in state["before_after"]] == [
        "0.70 -> 1.00",
        "0.15 -> 1.00",
        "1 -> 0",
        "0 -> 3",
        "0 -> 1",
    ]


def test_observability_state_projects_gate_decisions_and_memory_counts():
    state = build_observability_state()
    run1 = state["runs"]["run_001"]
    run2 = state["runs"]["run_002"]

    assert run1["trusted_graph"]["counts"] == {
        "redis_session_events": 8,
        "trusted_claims": 0,
        "retired_claims": 0,
        "contradictions": 0,
    }
    assert run2["trusted_graph"]["counts"] == {
        "redis_session_events": 8,
        "trusted_claims": 4,
        "retired_claims": 1,
        "contradictions": 3,
    }

    assert {
        entry["decision"]["reason"]
        for entry in run1["pipeline"]
    } == {"hypothesis missing scope conditions"}
    assert all(entry["decision"]["status"] == "promote" for entry in run2["pipeline"])


def test_observability_state_precomputes_provenance_highlights():
    state = build_observability_state()

    claims = state["provenance"]["trusted_claims"]
    assert len(claims) == 6
    for claim in claims:
        assert claim["evidence_span_valid"] is True
        assert claim["source_preview"]["highlight"] == claim["evidence_span"]
        assert claim["evidence_start"] < claim["evidence_end"]


def test_static_ui_contains_no_hardcoded_demo_scores():
    app_js = Path("observability/static/app.js").read_text()

    assert "/api/state" in app_js
    assert "0.70" not in app_js
    assert "0.15" not in app_js
    assert "1.00" not in app_js
    assert "hypothesis missing scope conditions" not in app_js

