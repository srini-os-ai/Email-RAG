# email-rag-mvp

Local MVP app to ingest one mailbox and search/ask questions over emails with **original emails as primary results** and **LLM response as secondary**.

## Stack
- Python 3.10+
- FastAPI
- Streamlit
- Ollama (`llama3.1:8b-instruct`, `nomic-embed-text`)
- SQLite (metadata + local vector store)

## Features
- Incremental indexing for append-only mailbox data (`processed_offset` tracking)
- Ingestion progress endpoint with ETA estimate (sample-based + live throughput)
- Confidence meter per result and overall answer confidence
- Local retrieval pipeline with SQLite vector storage
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
```bash
ollama pull llama3.1:8b-instruct
ollama pull nomic-embed-text
```

### 3) Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

## Ingest
```bash
python scripts/ingest.py --source data/sample.mbox --type mbox
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
- Ask

## API Endpoints
- `GET /health`
- `POST /ingest/start`
- `GET /ingest/status`
- `POST /query`

### Query behavior
- `mode=search`: returns email matches only
- `mode=ask`: returns email matches + LLM answer

Original emails are always returned as the primary evidence.

## Confidence Formula
Deterministic confidence for each result:
- `result_confidence = 0.7 * retrieval_score + 0.3 * evidence_coverage`

Overall answer confidence:
- `overall_confidence = 0.8 * average(result_confidences) + 0.2 * answer_coverage`

## ETA Estimation
- Initial estimate: sample mailbox bytes -> estimate messages remaining
- Live update: throughput (`emails/sec`) recalculates ETA while ingesting

## Test
```bash
pytest -q
```

## Notes
- Single mailbox focus for MVP.
- Vector search is local SQLite + cosine in Python over stored vectors (no cloud dependency).
- If Ollama is down, ingestion/query still work via deterministic local embedding fallback.

## Documentation
- Detailed setup/run guide: `docs/GETTING_STARTED.md`
- Product/architecture baseline + roadmap: `docs/SPEC.md`
