# Provenance Contract

Hypothesis Wiki borrows the strongest idea from `biorender-figure-compiler`: AI output is not trusted until it is anchored to verbatim source text.

## Rule

Every promoted scientific claim should carry:

```text
evidence_span
evidence_start
evidence_end
evidence_span_valid
```

The span must be a literal substring of the source paper card's `source_text` or `abstract`.

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

## Maude 2018 Fixture

`data/maude_2018_cart.json` is the first real-paper fixture. It contains DOI / PMID / PMCID metadata, source text, curated expected claims, and exact evidence spans.

Generate candidate claims:

```bash
python3 ingest_real_research.py \
  --from-cards data/maude_2018_cart.json \
  --claims-out data/maude_2018_claims.json \
  --extractor curated
```

This gives the wiki real scientific substance without introducing live API variance.

