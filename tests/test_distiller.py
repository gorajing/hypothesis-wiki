"""Behavior tests for the executable skill loop.

The v1 -> v2 improvement must be a real consequence of the skill text the
distiller is run with, and the v2 skill must be *proposed from critic
feedback* (propose) and then change distiller behavior on re-run (apply).
Nothing here hardcodes the improved output.
"""

import json
from pathlib import Path

from distiller import distill, propose_skill_revision

ROOT = Path(__file__).parent.parent
CARDS = {c["paper_id"]: c for c in json.loads((ROOT / "data" / "demo_mlperf_cards.json").read_text())}
V1 = (ROOT / "my_skills" / "hypothesis_distiller" / "SKILL.md").read_text()
V2 = (ROOT / "my_skills" / "hypothesis_distiller" / "SKILL.v2.md").read_text()


def test_v1_skill_drops_scope_and_overgeneralizes_negatives():
    pos = distill(CARDS["mlperf_demo_a"], V1)
    assert pos["scope_conditions"] == []
    assert pos["kind"] == "hypothesis"

    neg = distill(CARDS["mlperf_demo_d"], V1)  # a negative result card
    # v1 is documented as weak: it erases negative evidence into a positive claim.
    assert neg["kind"] == "hypothesis"
    assert neg["direction"] == "improves"


def test_v2_skill_preserves_scope_and_claim_kind():
    pos = distill(CARDS["mlperf_demo_a"], V2)
    assert pos["scope_conditions"] == CARDS["mlperf_demo_a"]["conditions"]
    assert pos["kind"] == "hypothesis"

    neg = distill(CARDS["mlperf_demo_d"], V2)
    assert neg["kind"] == "negative_result"
    assert neg["scope_conditions"] == CARDS["mlperf_demo_d"]["conditions"]
    assert neg["direction"] == "no_benefit"


def test_revision_proposed_from_feedback_then_applied_fixes_distiller():
    feedback = [
        "missing scope conditions present in trusted claims",
        "omitted negative/contradicting evidence in the trusted graph",
    ]
    revised = propose_skill_revision(feedback)

    # propose: the revision must encode the rules the feedback implies.
    assert "preserve benchmark condition" in revised.lower()
    assert "scenario-specific results as first-class" in revised.lower()

    # apply: re-running the distiller with the proposed skill fixes behavior.
    neg = distill(CARDS["mlperf_demo_d"], revised)
    assert neg["kind"] == "negative_result"
    assert neg["scope_conditions"] == CARDS["mlperf_demo_d"]["conditions"]


def test_revision_is_feedback_driven_not_hardcoded():
    # No scope/negative complaints -> proposal must NOT silently upgrade the
    # skill, or the loop would be theater rather than feedback-driven.
    revised = propose_skill_revision(["retrieval looked fine"])
    assert "preserve benchmark condition" not in revised.lower()
    assert distill(CARDS["mlperf_demo_a"], revised)["scope_conditions"] == []
