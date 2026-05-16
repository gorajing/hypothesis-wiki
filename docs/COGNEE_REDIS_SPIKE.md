# Cognee + Redis Spike

Run this before feature work in the hackathon environment.

## Goal

Prove the two memory paths:

```python
await cognee.remember(payload, session_id=run_id)  # session memory / Redis
await cognee.remember(payload)                     # permanent memory / Cognee graph
```

## Command

```bash
python3 cognee_redis_spike.py
```

## Success Criteria

The script should show:

```text
session write ok
graph write ok
session recall returned data
graph recall returned data
```

## Decision

If session memory stays separate from graph memory:

```text
Use cognee.remember(..., session_id=run_id) for Redis quarantine.
```

If session memory auto-promotes into the graph:

```text
Use direct redis-py for quarantine and reserve cognee.remember(...) for promoted claims.
```

## What Not To Do

Do not debug rich extraction or skill improvement here. This spike only answers whether the judged Redis/Cognee memory split behaves as expected.

