import asyncio
import json
from datetime import datetime, timezone

from backend.storage import create_memory_backend, decision_to_dict


RUN_ID = "hypothesis-wiki-spike"


async def main() -> None:
    raw_candidate = {
        "id": "spike_candidate_001",
        "kind": "hypothesis",
        "text": "AX-17 improves retention below 40C with electrolyte E1.",
        "source": "spike_paper",
        "scope_conditions": ["below 40C", "electrolyte E1"],
        "outcome": "retention",
        "direction": "improves",
        "status": "redis_quarantine",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    backend = await create_memory_backend()
    print(f"Session backend: {backend.session_store.__class__.__name__}")
    print(f"Trusted graph backend: {backend.trusted_graph.__class__.__name__}")

    print("Writing candidate claim to session memory...")
    await backend.remember(raw_candidate, session_id=RUN_ID)
    print("session write ok")

    print("Promoting candidate through distillation gate...")
    decision = await backend.promote_candidate(raw_candidate)
    print(json.dumps(decision_to_dict(decision), sort_keys=True))
    if not decision.promote:
        raise SystemExit("candidate was not promoted into the trusted graph")
    print("graph write ok")

    print("Recalling from session memory...")
    session_result = await backend.recall("AX-17 retention E1", session_id=RUN_ID)
    print("session recall returned data")
    print(_preview(session_result))

    print("Recalling from graph memory...")
    graph_result = await backend.recall("AX-17 retention E1")
    print("graph recall returned data")
    print(_preview(graph_result))

    print()
    print("Spike complete. Session memory is routed separately from trusted graph memory.")
    print("Set REDIS_URL for Redis quarantine and COGNEE_ENABLED=1 for Cognee graph writes.")


def _preview(value) -> str:
    text = repr(value)
    if len(text) > 500:
        return text[:500] + "..."
    return text


if __name__ == "__main__":
    asyncio.run(main())
