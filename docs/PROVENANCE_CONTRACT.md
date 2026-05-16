# Provenance Contract

Hypothesis Wiki borrows the strongest idea from `biorender-figure-compiler`: AI output is not trusted until it is anchored to verbatim source text.

## Rule

Every promoted scientific claim should carry:

```text
id
kind
text
source
source_url
paper_title
doi
scope_conditions
outcome
direction
evidence_type
evidence_span
evidence_start
evidence_end
evidence_span_valid
status
confidence
```

The span must be a literal substring of the source paper card's `source_text` or `abstract`.
`source_spans.validate_claims_against_cards()` enforces both the required fields
and the deterministic span offsets before claims are written or promoted.

## Extraction Pattern

Use a two-schema flow:

```text
model or curator emits:
  claim text
  kind
  outcome
  direction
  scope_conditions
  verbatim evidence_span

server computes:
  stable ID
  source metadata
  evidence_start
  evidence_end
  evidence_span_valid
```

Do not ask the model to compute offsets. Python computes offsets deterministically.

## Promotion Gate

`should_distill()` rejects a real extracted claim if it has an `evidence_span` but lacks validated offsets.

This preserves the Redis/Cognee split:

```text
unsupported candidate claim -> Redis only
validated evidence-backed claim -> Cognee graph
```

## Deterministic Real-Paper Fixtures

The repository keeps curated real-paper fixtures so tests can prove the ingestion
path without live API variance:

- `data/maude_2018_cart.json`: Maude 2018 NEJM CAR-T trial.
- `data/neelapu_2017_axi_cel.json`: Neelapu 2017 NEJM ZUMA-1 axi-cel trial.

Each fixture contains DOI / PMID metadata, source text, curated expected claims,
and exact evidence spans.

Generate candidate claims:

```bash
python3 ingest_real_research.py \
  --from-cards data/maude_2018_cart.json \
  --claims-out data/maude_2018_claims.json \
  --extractor curated

python3 ingest_real_research.py \
  --from-cards data/neelapu_2017_axi_cel.json \
  --claims-out data/neelapu_2017_claims.json \
  --extractor curated
```

This gives the wiki real scientific substance without introducing live API variance.
