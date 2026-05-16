import asyncio
import os
import sys
import types

import pytest

from backend.storage import (
    BackendUnavailableError,
    CogneeTrustedGraphStore,
    HypothesisMemoryBackend,
    InMemorySessionStore,
    InMemoryTrustedGraphStore,
    RedisSessionStore,
    create_in_memory_backend,
    create_memory_backend,
)


def run(coro):
    return asyncio.run(coro)


def _claim(**overrides):
    claim = {
        "id": "claim_ax17",
        "kind": "hypothesis",
        "text": "AX-17 improves retention below 40C with electrolyte E1.",
        "source": "paper_a",
        "scope_conditions": ["below 40C", "electrolyte E1"],
        "outcome": "retention",
        "direction": "improves",
        "status": "candidate",
    }
    claim.update(overrides)
    return claim


def test_session_writes_are_quarantined_from_trusted_graph():
    backend = HypothesisMemoryBackend(InMemorySessionStore(), InMemoryTrustedGraphStore())
    candidate = _claim()

    run(backend.remember(candidate, session_id="run_001"))

    assert run(backend.recall("AX-17", session_id="run_001")) == [candidate]
    assert run(backend.recall("AX-17")) == []
    assert backend.trusted_claims == []


def test_promote_candidate_runs_distillation_gate_before_graph_write():
    backend = HypothesisMemoryBackend(InMemorySessionStore(), InMemoryTrustedGraphStore())
    rejected = _claim(id="claim_missing_scope", scope_conditions=[])

    decision = run(backend.promote_candidate(rejected))

    assert decision.promote is False
    assert "scope" in decision.reason
    assert run(backend.recall("missing_scope")) == []

    accepted = _claim()
    decision = run(backend.promote_candidate(accepted))

    assert decision.promote is True
    trusted = run(backend.recall("AX-17"))
    assert trusted == [
        {
            **accepted,
            "status": "trusted",
            "distill_reason": "attributed, scoped, testable hypothesis",
            "distill_confidence": decision.confidence,
        }
    ]


def test_create_in_memory_backend_is_explicit_test_helper():
    backend = create_in_memory_backend()

    assert isinstance(backend.session_store, InMemorySessionStore)
    assert isinstance(backend.trusted_graph, InMemoryTrustedGraphStore)


def test_redis_session_store_routes_by_session_key():
    class FakeRedis:
        def __init__(self):
            self.lists = {}

        async def rpush(self, key, value):
            self.lists.setdefault(key, []).append(value)

        async def lrange(self, key, start, end):
            assert start == 0
            assert end == -1
            return self.lists.get(key, [])

    redis = FakeRedis()
    store = RedisSessionStore(redis)
    claim = _claim()

    run(store.remember(claim, "run_001"))
    run(store.remember(_claim(id="claim_other", text="Unrelated"), "run_002"))

    assert list(redis.lists) == [
        "hypothesis-wiki:session:run_001",
        "hypothesis-wiki:session:run_002",
    ]
    assert run(store.recall("AX-17", "run_001")) == [claim]


def test_cognee_trusted_graph_store_writes_without_session_id():
    class FakeCognee:
        def __init__(self):
            self.remembered = []

        async def remember(self, payload):
            self.remembered.append(payload)

        async def recall(self, query, **kwargs):
            return []

    cognee = FakeCognee()
    store = CogneeTrustedGraphStore(cognee)
    claim = _claim()

    run(store.remember(claim))

    assert len(cognee.remembered) == 1
    assert "session_id" not in cognee.remembered[0]
    assert run(store.recall("AX-17")) == []


def test_cognee_trusted_graph_store_recalls_only_from_cognee_dataset():
    class FakeCognee:
        def __init__(self):
            self.recalled = []

        async def remember(self, payload, **kwargs):
            pass

        async def recall(self, query, **kwargs):
            self.recalled.append((query, kwargs))
            return [{"text": "trusted graph result"}]

    cognee = FakeCognee()
    store = CogneeTrustedGraphStore(cognee, dataset_name="trusted-hypotheses")

    assert run(store.recall("AX-17")) == [{"text": "trusted graph result"}]
    assert cognee.recalled == [("AX-17", {"datasets": ["trusted-hypotheses"]})]


def test_create_memory_backend_requires_redis_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(BackendUnavailableError, match="REDIS_URL is required"):
        run(create_memory_backend(redis_url=None))


def test_create_memory_backend_requires_cognee(monkeypatch):
    monkeypatch.setitem(sys.modules, "redis", _fake_redis_module())

    with pytest.raises(BackendUnavailableError, match="Cognee trusted graph is required"):
        run(create_memory_backend(redis_url="redis://example", use_cognee=False))


def test_create_memory_backend_with_incompatible_cognee_api_raises(monkeypatch):
    fake_cognee = types.SimpleNamespace(
        remember=lambda payload: None,
        recall=lambda query: [],
    )
    monkeypatch.setitem(sys.modules, "redis", _fake_redis_module())
    monkeypatch.setitem(sys.modules, "cognee", fake_cognee)
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    with pytest.raises(BackendUnavailableError, match="compatible async remember"):
        run(create_memory_backend(redis_url="redis://example", use_cognee=True))


def test_create_memory_backend_requires_llm_key_for_local_cognee(monkeypatch):
    fake_cognee = types.SimpleNamespace(
        remember=_async_noop,
        recall=_async_empty,
    )
    monkeypatch.setitem(sys.modules, "redis", _fake_redis_module())
    monkeypatch.setitem(sys.modules, "cognee", fake_cognee)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("COGNEE_URL", raising=False)
    monkeypatch.delenv("COGNEE_API_KEY", raising=False)

    with pytest.raises(BackendUnavailableError, match="LLM_API_KEY is required"):
        run(create_memory_backend(redis_url="redis://example", use_cognee=True))


def test_create_memory_backend_requires_complete_cognee_cloud_config(monkeypatch):
    fake_cognee = types.SimpleNamespace(
        remember=_async_noop,
        recall=_async_empty,
    )
    monkeypatch.setitem(sys.modules, "redis", _fake_redis_module())
    monkeypatch.setitem(sys.modules, "cognee", fake_cognee)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(BackendUnavailableError, match="COGNEE_URL and COGNEE_API_KEY"):
        run(
            create_memory_backend(
                redis_url="redis://example",
                use_cognee=True,
                cognee_url="https://example.cognee.ai",
            )
        )


def test_create_memory_backend_maps_openai_key_for_local_cognee(monkeypatch):
    fake_cognee = types.SimpleNamespace(
        remembered=[],
        remember=_async_noop,
        recall=_async_empty,
    )
    monkeypatch.setitem(sys.modules, "redis", _fake_redis_module())
    monkeypatch.setitem(sys.modules, "cognee", fake_cognee)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    run(create_memory_backend(redis_url="redis://example", use_cognee=True))

    assert os.environ["LLM_API_KEY"] == "test-openai-key"


def test_create_memory_backend_uses_real_redis_and_cognee_interfaces(monkeypatch):
    class FakeCognee:
        def __init__(self):
            self.remembered = []

        async def remember(self, payload, **kwargs):
            self.remembered.append((payload, kwargs))

        async def recall(self, query):
            return []

    fake_cognee = FakeCognee()
    monkeypatch.setitem(sys.modules, "redis", _fake_redis_module())
    monkeypatch.setitem(sys.modules, "cognee", fake_cognee)
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    backend = run(
        create_memory_backend(
            redis_url="redis://example",
            use_cognee=True,
            cognee_dataset_name="trusted-hypotheses",
        )
    )
    claim = _claim()

    assert isinstance(backend.trusted_graph, CogneeTrustedGraphStore)
    run(backend.remember(claim))

    assert fake_cognee.remembered
    assert fake_cognee.remembered[0][1] == {"dataset_name": "trusted-hypotheses"}


async def _async_noop(*args, **kwargs):
    return None


async def _async_empty(*args, **kwargs):
    return []


def _fake_redis_module():
    class FakeRedisClient:
        def __init__(self):
            self.lists = {}

        async def ping(self):
            return True

        async def rpush(self, key, value):
            self.lists.setdefault(key, []).append(value)

        async def lrange(self, key, start, end):
            return self.lists.get(key, [])

    class FakeRedisAsyncio:
        @staticmethod
        def from_url(url, decode_responses=True):
            return FakeRedisClient()

    return types.SimpleNamespace(asyncio=FakeRedisAsyncio)
