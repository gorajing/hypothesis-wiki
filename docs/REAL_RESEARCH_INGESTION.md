# Real Research Ingestion

The deterministic AX-17 corpus proves the mechanism. The real research lane makes the wiki reflect actual scientific substance.

## Data Source

Use Semantic Scholar first. It gives fast access to paper metadata and abstracts. Optional API key:

```bash
export SEMANTIC_SCHOLAR_API_KEY=...
```

## Fetch Real Paper Cards

```bash
python3 ingest_real_research.py \
  --queries-file data/research_queries.json \
  --cards-out data/real_paper_cards.json \
  --claims-out data/real_claims.json \
  --extractor heuristic
```

This writes:

```text
data/real_paper_cards.json
data/real_claims.json
```

Before `claims-out` is written, the ingestion command validates every claim
against the provenance contract: required metadata fields, a verbatim
`evidence_span`, deterministic `evidence_start` / `evidence_end`, and
`evidence_span_valid: true`.

## Use The Real Maude 2018 Fixture

For the first real-paper demo, use the curated Maude 2018 CAR-T fixture borrowed from the BioRender FigureSpec work:

```bash
python3 ingest_real_research.py \
  --from-cards data/maude_2018_cart.json \
  --claims-out data/maude_2018_claims.json \
  --extractor curated
```

This path is deterministic but substantive: every claim points to a real paper identifier and a verbatim evidence span.

The second deterministic fixture exercises the same path on the Neelapu 2017
ZUMA-1 axi-cel trial:

```bash
python3 ingest_real_research.py \
  --from-cards data/neelapu_2017_axi_cel.json \
  --claims-out data/neelapu_2017_claims.json \
  --extractor curated
```

## Extract With OpenAI

OpenAI extraction is optional. It is useful for better claim structure, but it is not required for the demo path.

```bash
export OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-5.2

python3 ingest_real_research.py \
  --from-cards data/real_paper_cards.json \
  --claims-out data/real_claims.openai.json \
  --extractor openai
```

The OpenAI path uses the Responses API with JSON Schema structured outputs. It must only extract from title and abstract, and it must preserve scope conditions, negative results, and uncertainty.

## Why Abstracts First

For the hackathon, abstracts are the right first substrate:

- real scientific content
- source-attributed
- small enough for fast demos
- no PDF parsing risk
- compatible with Semantic Scholar search

PMC Open Access full text can be added later for deeper evidence. Do not scrape random PDFs during the hackathon.

## Claim Contract

Every real extracted claim must include:

```text
source
source_url
paper_title
doi
evidence_span
evidence_start
evidence_end
evidence_span_valid
kind
text
outcome
direction
scope_conditions
confidence
```

The critical integrity rule:

```text
The claim text must be grounded in an evidence_span from the abstract.
```

If the extractor cannot find an evidence-bearing sentence, it should emit no claim rather than invent one.
