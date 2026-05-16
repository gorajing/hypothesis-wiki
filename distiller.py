"""Executable hypothesis distiller.

The distiller's behavior is a function of the *skill text* it is given.
A weak skill (v1) drops benchmark scope and flattens negative or conditional
findings into a universal positive claim. A scope-preserving skill (v2) keeps
conditions and records contrary results as first-class evidence.

`propose_skill_revision` closes the loop: it derives a stronger skill
*from critic feedback*, which the caller then applies by re-running the
distiller with the returned text.
"""

# Machine-detectable capability phrases. The curated SKILL.v2.md carries
# these verbatim; SKILL.md (v1) deliberately does not.
_SCOPE_MARKER = "preserve benchmark condition"
BASE_SKILL = (
    "# Hypothesis Distiller v1\n\n"
    "Extract the main benchmark finding from each source card as a concise "
    "hypothesis. Prefer short, reusable statements.\n"
)

_KIND_BY_RESULT = {
    "positive": "hypothesis",
    "conditional": "evidence",
    "replication_failure": "evidence",
    "negative": "negative_result",
}


def _skill_preserves_scope(skill_text: str) -> bool:
    return _SCOPE_MARKER in skill_text.lower()


def distill(card: dict, skill_text: str) -> dict:
    """Turn a source card into a candidate claim, per the given skill."""
    base = {
        "id": f"claim_{card['paper_id']}",
        "text": card["finding"],
        "source": card["paper_id"],
        "source_url": card["url"],
        "outcome": card["outcome"],
        "evidence_type": "source_card",
        "status": "candidate",
        "confidence": 0.62,
    }

    if _skill_preserves_scope(skill_text):
        base["kind"] = _KIND_BY_RESULT.get(card["result_type"], "evidence")
        base["scope_conditions"] = list(card["conditions"])
        base["direction"] = card["direction"]
        return base

    # Weak v1 behavior: scope erased, every finding optimistically promoted
    # to a universal positive hypothesis.
    base["kind"] = "hypothesis"
    base["scope_conditions"] = []
    base["direction"] = "improves"
    return base


def propose_skill_revision(feedback: list[str]) -> str:
    """Propose a stronger distiller skill from critic feedback.

    Only the rules implied by the feedback are added. Absent the relevant
    complaints, the skill is returned unchanged so the loop stays
    feedback-driven rather than scripted.
    """
    notes = " ".join(feedback).lower()
    wants_scope = "scope" in notes or "condition" in notes
    wants_negative = (
        "negative" in notes
        or "contradict" in notes
        or "overclaim" in notes
        or "serving workload" in notes
    )

    if not (wants_scope or wants_negative):
        return BASE_SKILL

    lines = ["# Hypothesis Distiller v2 (revised from critic feedback)", "", "Rules:", ""]
    if wants_scope:
        lines.append(
            "1. Preserve benchmark conditions such as benchmark, hardware, "
            "model, scenario, metric, division, dataset, and run setting."
        )
        lines.append("2. Never collapse a conditional finding into a universal claim.")
    if wants_negative:
        lines.append("3. Promote contrary or scenario-specific results as first-class evidence.")
        lines.append("4. Mark contradictions explicitly instead of smoothing them away.")
    lines.append("5. Include the source card ID on every claim.")
    return "\n".join(lines) + "\n"
