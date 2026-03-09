# email-rag-mvp

Local MVP app to ingest one mailbox and search emails with **original emails as primary results**.

## Stack
- Python 3.10+
- FastAPI
- Streamlit
- Ollama (`llama3.1:8b`, `nomic-embed-text`)
- SQLite (metadata + local vector store)

## Features
- Incremental indexing for append-only mailbox data (`processed_offset` tracking)
- Ingestion progress endpoint with ETA estimate (sample-based + live throughput)
- Confidence meter per result and overall confidence
- Query rewriting via LLM system prompt before retrieval (configurable)
- Local retrieval pipeline with SQLite vector storage
- Embedding + rewrite debug visibility in API/UI (backend/model, rewritten query, rewrite prompt)
- Fallback local hash embedding if Ollama is unavailable

## Project Structure
- `app/`: core app logic and API
- `scripts/`: CLI and app run entrypoints
- `tests/`: pytest coverage
- `data/`: local data files

## Setup (Mac, M2-friendly)

### 1) Install Ollama
```bash
brew install ollama
brew services start ollama
```

### 2) Pull required models

You can browse the latest available models/tags in the Ollama library:
- <https://ollama.com/library>

Useful local checks:
```bash
ollama list
ollama show llama3.1:8b
```

Then pull the models used by this MVP:
```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 3) Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e '.[dev]'
```

> zsh note: quote `'.[dev]'` so the shell does not treat `[]` as a glob pattern.


## Ingest
```bash
python scripts/ingest.py --source data/sample.mbox --type mbox
```

## Query rewrite configuration (optional)

```bash
export EMAIL_RAG_REWRITE_ENABLED=1
export EMAIL_RAG_REWRITE_MODEL=llama3.1:8b
export EMAIL_RAG_REWRITE_SYSTEM_PROMPT="You are a search-query rewriting assistant..."
```

## Run API
```bash
./scripts/run_api.sh
```

## Run Streamlit UI
```bash
streamlit run scripts/streamlit_app.py
```

UI pages:
- Ingest
- Search

## API Endpoints
- `GET /health`
- `POST /ingest/start`
- `GET /ingest/status`
- `POST /query`

### Query behavior
- `mode=search`: returns email matches only
- query responses include:
  - `embedding_backend` + `embedding_model`
  - `rewritten_query`
  - `llm_prompt_used` (query-rewrite prompt sent to LLM)

Original emails are always returned as the primary evidence.

## Confidence Formula
Deterministic confidence for each result:
- `result_confidence = 0.7 * retrieval_score + 0.3 * evidence_coverage`

Overall confidence:
- `overall_confidence = average(result_confidences)`

## ETA Estimation
- Initial estimate: sample mailbox bytes -> estimate messages remaining
- Live update: throughput (`emails/sec`) recalculates ETA while ingesting

## Test
```bash
pytest -q
```

## Clear existing index (for re-embedding tests)

If you want to rebuild embeddings from scratch (for example after changing embedding model), delete the local DB and re-ingest:

```bash
rm -f data/email_rag.db
python scripts/ingest.py --source data/sample.mbox --type mbox
```

If your data is elsewhere, keep the same command but point `--source` to your mailbox path.

## Notes
- Single mailbox focus for MVP.
- Vector search is local SQLite + cosine in Python over stored vectors (no cloud dependency).
- If Ollama is down, ingestion/query still work via deterministic local embedding fallback.

## Documentation
- Detailed setup/run guide: `docs/GETTING_STARTED.md`
- Product/architecture baseline + roadmap: `docs/SPEC.md`
