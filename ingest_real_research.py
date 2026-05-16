import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from research_claim_extractor import extract_claims_from_cards
from source_spans import validate_claims_against_cards


SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch source records and extract wiki claims.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--query", help="Semantic Scholar query string")
    source.add_argument("--queries-file", help="JSON file with {topic, queries, limit_per_query}")
    source.add_argument("--from-cards", help="Use an existing source-card JSON file")
    parser.add_argument("--limit", type=int, default=8, help="Maximum source records per query")
    parser.add_argument("--cards-out", default="data/real_benchmark_cards.json")
    parser.add_argument("--claims-out", default="data/real_claims.json")
    parser.add_argument("--extractor", choices=["heuristic", "curated", "openai", "none"], default="heuristic")
    parser.add_argument("--model", help="OpenAI model for --extractor openai")
    args = parser.parse_args()

    if args.from_cards:
        cards = _read_json(Path(args.from_cards))
    else:
        queries, limit = _resolve_queries(args)
        cards = fetch_cards_for_queries(queries, limit=limit)
        _write_json(Path(args.cards_out), cards)

    claims = extract_claims_from_cards(cards, extractor=args.extractor, model=args.model)
    issues = validate_claims_against_cards(claims, cards)
    if issues:
        detail = "\n".join(f"- {issue.code}: {issue.claim_id}: {issue.message}" for issue in issues)
        raise RuntimeError(f"extracted claims failed provenance validation:\n{detail}")

    _write_json(Path(args.claims_out), claims)

    cards_location = args.from_cards or args.cards_out
    print(f"source_cards: {len(cards)} -> {cards_location}")
    print(f"claims:      {len(claims)} -> {args.claims_out}")
    print()
    print("Next: feed cards/claims into Redis session memory, then run should_distill() before Cognee promotion.")


def fetch_cards_for_queries(queries: list[str], *, limit: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    cards: list[dict[str, Any]] = []
    for query in queries:
        for paper in search_semantic_scholar(query, limit=limit):
            paper_id = paper.get("paperId")
            if not paper_id or paper_id in seen:
                continue
            seen.add(paper_id)
            card = paper_to_card(paper, query=query)
            if card.get("abstract"):
                cards.append(card)
    return cards


def search_semantic_scholar(query: str, *, limit: int) -> list[dict[str, Any]]:
    fields = ",".join(
        [
            "title",
            "year",
            "abstract",
            "authors",
            "url",
            "externalIds",
            "citationCount",
            "venue",
            "publicationTypes",
            "isOpenAccess",
            "openAccessPdf",
        ]
    )
    params = urllib.parse.urlencode({"query": query, "limit": limit, "fields": fields})
    request = urllib.request.Request(f"{SEMANTIC_SCHOLAR_SEARCH_URL}?{params}")
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        request.add_header("x-api-key", api_key)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Semantic Scholar request failed: {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Semantic Scholar request failed: {exc.reason}") from exc

    return payload.get("data", [])


def paper_to_card(paper: dict[str, Any], *, query: str) -> dict[str, Any]:
    external_ids = paper.get("externalIds") or {}
    authors = paper.get("authors") or []
    open_access_pdf = paper.get("openAccessPdf") or {}
    return {
        "paper_id": f"semanticscholar:{paper['paperId']}",
        "title": paper.get("title"),
        "year": paper.get("year"),
        "url": paper.get("url"),
        "doi": external_ids.get("DOI"),
        "abstract": paper.get("abstract"),
        "authors": [author.get("name") for author in authors if author.get("name")],
        "venue": paper.get("venue"),
        "citation_count": paper.get("citationCount"),
        "publication_types": paper.get("publicationTypes") or [],
        "is_open_access": paper.get("isOpenAccess"),
        "open_access_pdf": open_access_pdf.get("url"),
        "source_type": "semantic_scholar_abstract",
        "source_query": query,
    }


def _resolve_queries(args: argparse.Namespace) -> tuple[list[str], int]:
    if args.query:
        return [args.query], args.limit
    config = _read_json(Path(args.queries_file))
    queries = config.get("queries") or []
    if not queries:
        raise SystemExit("queries-file must include a non-empty 'queries' array")
    return queries, int(config.get("limit_per_query") or args.limit)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"file not found: {path}") from None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
