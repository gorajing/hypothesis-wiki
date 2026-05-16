# Benchmark Claim Wiki Observability

This read-only dashboard exposes the live demo state as an inspectable UI:

- Run 1 vs. Run 2 answer and critic scorecards.
- Redis quarantine candidates, distillation-gate decisions, and promoted Cognee trusted nodes.
- Provenance drill-down for promoted benchmark claims, including the precomputed source-span highlight.

The browser does not compute scores, deltas, or provenance matches. It fetches a backend state projection from `/api/state` and renders that JSON.

## Run

```bash
cd /Users/jinchoi/Code/Memory/hypothesis-wiki
.venv/bin/uvicorn observability.api:app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/observability
```

## Related checks

```bash
python3 -m pytest -q
python3 demo.py
REDIS_URL=redis://localhost:6379 COGNEE_DATASET=benchmark-claim-wiki-trusted .venv/bin/python cognee_redis_spike.py
```

