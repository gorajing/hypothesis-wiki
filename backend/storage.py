from __future__ import annotations

import json
import os
from dataclasses import asdict
from inspect import iscoroutinefunction
from typing import Any, Protocol

from distillation_policy import DistillDecision, should_distill


SESSION_KEY_PREFIX = "benchmark-claim-wiki:session"


class BackendUnavailableError(RuntimeError):
    pass


class SessionStore(Protocol):
    async def remember(self, payload: dict[str, Any], session_id: str) -> None:
        ...

    async def recall(self, query: str, session_id: str) -> list[dict[str, Any]]:
        ...


class TrustedGraphStore(Protocol):
    async def remember(self, payload: dict[str, Any]) -> None:
        ...

    async def recall(self, query: str) -> list[dict[str, Any]]:
        ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def remember(self, payload: dict[str, Any], session_id: str) -> None:
        self.events.append({"session_id": session_id, "payload": dict(payload)})

    async def recall(self, query: str, session_id: str) -> list[dict[str, Any]]:
        return [
            event["payload"]
            for event in self.events
            if event["session_id"] == session_id and _matches_query(event["payload"], query)
        ]


class InMemoryTrustedGraphStore:
    def __init__(self) -> None:
        self.claims: list[dict[str, Any]] = []

    async def remember(self, payload: dict[str, Any]) -> None:
        self.claims.append(dict(payload))

    async def recall(self, query: str) -> list[dict[str, Any]]:
        return [claim for claim in self.claims if _matches_query(claim, query)]


class RedisSessionStore:
    def __init__(self, redis_client: Any, key_prefix: str = SESSION_KEY_PREFIX) -> None:
        self.redis = redis_client
        self.key_prefix = key_prefix

    async def remember(self, payload: dict[str, Any], session_id: str) -> None:
        await self.redis.rpush(self._key(session_id), json.dumps(payload, sort_keys=True))

    async def recall(self, query: str, session_id: str) -> list[dict[str, Any]]:
        values = await self.redis.lrange(self._key(session_id), 0, -1)
        decoded = [_decode_json(value) for value in values]
        return [payload for payload in decoded if _matches_query(payload, query)]

    def _key(self, session_id: str) -> str:
        return f"{self.key_prefix}:{session_id}"


class CogneeTrustedGraphStore:
    """Trusted graph adapter for Cognee's async memory API.

    API assumption: the installed Cognee module exposes coroutine functions
    `remember(payload: str)` and `recall(query: str)`. Session-scoped memory is
    intentionally not used here; Redis owns quarantine/session routing.
    """

    def __init__(self, cognee_module: Any, dataset_name: str | None = None) -> None:
        self.cognee = cognee_module
        self.dataset_name = dataset_name

    async def remember(self, payload: dict[str, Any]) -> None:
        kwargs = {"dataset_name": self.dataset_name} if self.dataset_name else {}
        await self.cognee.remember(json.dumps(payload, sort_keys=True), **kwargs)

    async def recall(self, query: str) -> list[dict[str, Any]]:
        kwargs = {"datasets": [self.dataset_name]} if self.dataset_name else {}
        return _normalize_recall(await self.cognee.recall(query, **kwargs))


class BenchmarkMemoryBackend:
    """Route untrusted session events separately from trusted graph claims."""

    def __init__(self, session_store: SessionStore, trusted_graph: TrustedGraphStore) -> None:
        self.session_store = session_store
        self.trusted_graph = trusted_graph
        self.trusted_claims: list[dict[str, Any]] = []
        self.retirements: list[dict[str, Any]] = []

    async def remember(self, payload: dict[str, Any], session_id: str | None = None) -> None:
        if session_id:
            await self.session_store.remember(payload, session_id)
            return
        await self._remember_trusted(payload)

    async def recall(self, query: str, session_id: str | None = None) -> list[dict[str, Any]]:
        if session_id:
            return await self.session_store.recall(query, session_id)
        return await self.trusted_graph.recall(query)

    async def promote_candidate(self, claim: dict[str, Any]) -> DistillDecision:
        decision = should_distill(claim, self)
        if decision.promote:
            await self._remember_trusted(
                {
                    **claim,
                    "status": "trusted",
                    "distill_reason": decision.reason,
                    "distill_confidence": decision.confidence,
                }
            )
        return decision

    def has_duplicate(self, claim: dict[str, Any]) -> bool:
        return any(existing.get("text") == claim.get("text") for existing in self.trusted_claims)

    def has_conflict(self, claim: dict[str, Any]) -> bool:
        if claim.get("direction") != "improves":
            return False
        return any(
            existing.get("kind") == "negative_result" and existing.get("outcome") == claim.get("outcome")
            for existing in self.trusted_claims
        )

    def retire(self, claim_id: str, reason: str, evidence_id: str) -> None:
        self.retirements.append({"claim_id": claim_id, "reason": reason, "evidence_id": evidence_id})

    async def _remember_trusted(self, payload: dict[str, Any]) -> None:
        await self.trusted_graph.remember(payload)
        self.trusted_claims.append(dict(payload))


async def create_memory_backend(
    redis_url: str | None = None,
    *,
    use_cognee: bool | None = None,
    cognee_url: str | None = None,
    cognee_api_key: str | None = None,
    cognee_dataset_name: str | None = None,
) -> BenchmarkMemoryBackend:
    session_store = await _create_session_store(redis_url)
    trusted_graph = await _create_trusted_graph(
        use_cognee,
        cognee_url=cognee_url,
        cognee_api_key=cognee_api_key,
        dataset_name=cognee_dataset_name,
    )
    return BenchmarkMemoryBackend(session_store, trusted_graph)


def create_in_memory_backend() -> BenchmarkMemoryBackend:
    return BenchmarkMemoryBackend(InMemorySessionStore(), InMemoryTrustedGraphStore())


async def _create_session_store(redis_url: str | None) -> SessionStore:
    url = redis_url or os.getenv("REDIS_URL")
    if not url:
        raise BackendUnavailableError("REDIS_URL is required for Redis session quarantine")

    try:
        from redis import asyncio as redis_asyncio
    except ImportError as exc:
        raise BackendUnavailableError("redis package is not installed") from exc

    try:
        client = redis_asyncio.from_url(url, decode_responses=True)
        await client.ping()
    except Exception as exc:
        raise BackendUnavailableError(f"Redis is not reachable at {url!r}: {exc}") from exc

    return RedisSessionStore(client)


async def _create_trusted_graph(
    use_cognee: bool | None,
    *,
    cognee_url: str | None = None,
    cognee_api_key: str | None = None,
    dataset_name: str | None = None,
) -> TrustedGraphStore:
    enabled = True if use_cognee is None else use_cognee
    if not enabled:
        raise BackendUnavailableError("Cognee trusted graph is required")

    try:
        import cognee
    except ImportError as exc:
        raise BackendUnavailableError("cognee package is not installed") from exc

    configured_cognee_url = cognee_url or os.getenv("COGNEE_URL")
    configured_cognee_api_key = cognee_api_key or os.getenv("COGNEE_API_KEY")

    _configure_local_cognee_llm_if_needed(
        cognee_url=configured_cognee_url,
        cognee_api_key=configured_cognee_api_key,
    )

    await _connect_cognee_cloud_if_configured(
        cognee,
        cognee_url=configured_cognee_url,
        cognee_api_key=configured_cognee_api_key,
    )

    if not _has_compatible_cognee_api(cognee):
        raise BackendUnavailableError(
            "Cognee does not expose compatible async remember(payload) and recall(query) calls"
        )

    return CogneeTrustedGraphStore(cognee, dataset_name=dataset_name or os.getenv("COGNEE_DATASET"))


def _configure_local_cognee_llm_if_needed(
    *,
    cognee_url: str | None,
    cognee_api_key: str | None,
) -> None:
    if bool(cognee_url) != bool(cognee_api_key):
        raise BackendUnavailableError("COGNEE_URL and COGNEE_API_KEY must be set together")
    if cognee_url and cognee_api_key:
        return
    if os.getenv("LLM_API_KEY"):
        return

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        os.environ["LLM_API_KEY"] = openai_api_key
        return

    raise BackendUnavailableError(
        "LLM_API_KEY is required for local Cognee graph writes "
        "(or set both COGNEE_URL and COGNEE_API_KEY for Cognee Cloud)"
    )


async def _connect_cognee_cloud_if_configured(
    cognee_module: Any,
    *,
    cognee_url: str | None,
    cognee_api_key: str | None,
) -> None:
    if not cognee_url and not cognee_api_key:
        return
    if not cognee_url or not cognee_api_key:
        raise BackendUnavailableError("COGNEE_URL and COGNEE_API_KEY must be set together")

    serve = getattr(cognee_module, "serve", None)
    if not iscoroutinefunction(serve):
        raise BackendUnavailableError("Cognee cloud configuration requires async cognee.serve()")

    await serve(url=cognee_url, api_key=cognee_api_key)


def _has_compatible_cognee_api(cognee_module: Any) -> bool:
    return all(
        iscoroutinefunction(getattr(cognee_module, name, None))
        for name in ("remember", "recall")
    )


def _matches_query(payload: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    haystack = json.dumps(payload, sort_keys=True).lower()
    return all(term in haystack for term in query.lower().split())


def _decode_json(value: bytes | str) -> dict[str, Any]:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return json.loads(value)


def _normalize_recall(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item if isinstance(item, dict) else {"value": item} for item in value]
    if isinstance(value, dict):
        return [value]
    return [{"value": value}]


def decision_to_dict(decision: DistillDecision) -> dict[str, Any]:
    return asdict(decision)
