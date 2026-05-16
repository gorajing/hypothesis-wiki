import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4

from backend.storage import (
    create_memory_backend,
    decision_to_dict,
)


RUN_ID = f"benchmark-claim-wiki-spike-{uuid4().hex[:8]}"


async def main() -> None:
    raw_candidate = {
        "id": "spike_mlperf_claim_001",
        "kind": "evidence",
        "text": "MI325X reached 34,520.4 samples/s on llama2-70b-99 in MLPerf Offline.",
        "source": "mlperf_v5_1_spike",
        "scope_conditions": ["MLPerf Inference v5.1", "llama2-70b-99", "Offline scenario", "8x AMD Instinct MI325X"],
        "outcome": "llama2-70b throughput",
        "direction": "observes",
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
    session_result = await backend.recall("MLPerf MI325X Llama2", session_id=RUN_ID)
    print("session recall returned data")
    print(_preview(session_result))

    print("Recalling from graph memory...")
    graph_result = await backend.recall("MLPerf MI325X Llama2")
    print("graph recall returned data")
    print(_preview(graph_result))

    print()
    print("Spike complete. Session memory is routed separately from trusted graph memory.")
    print("RedisSessionStore and CogneeTrustedGraphStore are required for this spike.")


def _preview(value) -> str:
    text = repr(value)
    if len(text) > 500:
        return text[:500] + "..."
    return text


if __name__ == "__main__":
    asyncio.run(main())
