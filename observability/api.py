from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from observability.state import build_observability_state


STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_PATH = STATIC_DIR / "index.html"

app = FastAPI(title="Benchmark Claim Wiki Observability", version="1")
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="observability-assets")


@app.get("/", include_in_schema=False)
@app.get("/observability", include_in_schema=False)
def observability_page() -> HTMLResponse:
    return HTMLResponse(INDEX_PATH.read_text())


@app.get("/api/state")
def observability_state() -> dict:
    return build_observability_state()

