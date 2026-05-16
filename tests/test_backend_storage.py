import asyncio
import sys
import types

import pytest

from backend.storage import (
    CogneeTrustedGraphStore,
    HypothesisMemoryBackend,
    InMemorySessionStore,
    InMemoryTrustedGraphStore,
    RedisSessionStore,
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


def test_create_memory_backend_uses_in_memory_fallback_without_services():
    backend = run(create_memory_backend(redis_url=None, use_cognee=False))

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

        async def recall(self, query):
            return []

    cognee = FakeCognee()
    store = CogneeTrustedGraphStore(cognee)
    claim = _claim()

    run(store.remember(claim))

    assert len(cognee.remembered) == 1
    assert "session_id" not in cognee.remembered[0]
    assert run(store.recall("AX-17")) == [claim]


def test_enabled_cognee_with_incompatible_api_warns_and_falls_back(monkeypatch):
    fake_cognee = types.SimpleNamespace(
        remember=lambda payload: None,
        recall=lambda query: [],
    )
    monkeypatch.setitem(sys.modules, "cognee", fake_cognee)

    with pytest.warns(RuntimeWarning, match="falling back to InMemoryTrustedGraphStore"):
        backend = run(create_memory_backend(redis_url=None, use_cognee=True))

    assert isinstance(backend.trusted_graph, InMemoryTrustedGraphStore)
