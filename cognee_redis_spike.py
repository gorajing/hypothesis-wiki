import asyncio
import json
from datetime import datetime, timezone


RUN_ID = "hypothesis-wiki-spike"


async def main() -> None:
    try:
        import cognee
    except ImportError as exc:
        raise SystemExit(
            "cognee is not installed in this environment. "
            "Install the hackathon dependencies, then rerun this spike."
        ) from exc

    raw_candidate = {
        "type": "candidate_claim",
        "id": "spike_candidate_001",
        "text": "AX-17 improves retention below 40C with electrolyte E1.",
        "source": "spike_paper",
        "status": "redis_quarantine",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    promoted_claim = {
        "type": "trusted_hypothesis",
        "id": "spike_trusted_001",
        "text": "AX-17 evidence is scoped to below 40C with electrolyte E1.",
        "source": "spike_paper",
        "scope_conditions": ["below 40C", "electrolyte E1"],
        "status": "trusted_graph",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    print("Writing candidate claim to session memory...")
    await cognee.remember(json.dumps(raw_candidate), session_id=RUN_ID)
    print("session write ok")

    print("Writing promoted claim to permanent graph...")
    await cognee.remember(json.dumps(promoted_claim))
    print("graph write ok")

    print("Recalling from session memory...")
    session_result = await cognee.recall("AX-17 retention E1", session_id=RUN_ID)
    print("session recall returned data")
    print(_preview(session_result))

    print("Recalling from graph memory...")
    graph_result = await cognee.recall("AX-17 scoped evidence")
    print("graph recall returned data")
    print(_preview(graph_result))

    print()
    print("Spike complete. If session recall and graph recall show distinct behavior,")
    print("use Cognee session memory as the Redis quarantine. If not, use direct redis-py")
    print("for quarantine and reserve Cognee for promoted claims.")


def _preview(value) -> str:
    text = repr(value)
    if len(text) > 500:
        return text[:500] + "..."
    return text


if __name__ == "__main__":
    asyncio.run(main())

