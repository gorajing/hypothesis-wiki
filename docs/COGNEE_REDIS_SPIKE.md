# Cognee + Redis Spike

Run this before feature work in the hackathon environment.

## Goal

Prove the two memory paths:

```python
await redis.rpush(session_key, payload)  # session memory / Redis quarantine
await cognee.remember(payload)           # permanent memory / Cognee graph
```

## Command

Install dependencies and start Redis first:

```bash
python3 -m pip install -r requirements.txt
redis-server
```

Then configure:

```bash
export REDIS_URL=redis://localhost:6379
export LLM_API_KEY=...  # or set OPENAI_API_KEY
export COGNEE_DATASET=hypothesis-wiki-trusted
```

For Cognee Cloud, also set:

```bash
export COGNEE_URL=...
export COGNEE_API_KEY=...
```

Run the proof:

```bash
python3 cognee_redis_spike.py
```

## Success Criteria

The script should show:

```text
Session backend: RedisSessionStore
Trusted graph backend: CogneeTrustedGraphStore
session write ok
graph write ok
session recall returned data
graph recall returned data
```

The spike intentionally fails if Redis or Cognee is missing. There is no runtime
in-memory fallback in this proof path.

## What Not To Do

Do not debug rich extraction or skill improvement here. This spike only answers whether the judged Redis/Cognee memory split behaves as expected.
