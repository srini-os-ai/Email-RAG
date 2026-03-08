# Getting Started (Detailed)

This guide gets you from zero to a working local email-search MVP on Mac.

## 0) What this MVP does

- Ingests one mailbox (MBOX first; text file mode also supported)
- Builds local metadata + vector index in SQLite
- Lets you:
  - **Search**: original emails shown first
- Computes confidence per hit + overall confidence
- Tracks ingestion progress and ETA
- Supports append-only incremental indexing

## 1) Prerequisites

- macOS (Apple Silicon tested target: M2)
- Python 3.10+
- Homebrew
- Ollama

## 2) Install dependencies

### 2.1 Install Ollama

```bash
brew install ollama
brew services start ollama
```

### 2.2 Pull local models

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 2.3 Create Python env

```bash
cd ~/Projects/email-rag-mvp
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e '.[dev]'
```

## 3) Add your mailbox data

Place your mailbox in a path like:

```bash
mkdir -p data
cp /path/to/your/mailbox.mbox data/mailbox.mbox
```

If using text files, place `.txt` files under a folder and pass type `text`.

## 4) Run ingestion

### MBOX

```bash
python scripts/ingest.py --source data/mailbox.mbox --type mbox
```

### Text files

```bash
python scripts/ingest.py --source /path/to/text-folder --type text
```

## 5) Start API + UI

### API

```bash
./scripts/run_api.sh
```

### Streamlit UI

In a second terminal:

```bash
cd ~/Projects/email-rag-mvp
source .venv/bin/activate
streamlit run scripts/streamlit_app.py
```

## 6) Verify with tests

```bash
cd ~/Projects/email-rag-mvp
source .venv/bin/activate
pytest -q
```

Expected baseline currently: all tests pass.

## 7) API quick reference

- `GET /health`
- `POST /ingest/start`
- `GET /ingest/status`
- `POST /query`

### Example query payload

```json
{
  "query": "emails about quarterly planning",
  "mode": "search",
  "top_k": 5
}
```

## 8) Troubleshooting

### Ollama not running

Symptoms: embeddings/LLM fallback path used or model call errors.

Fix:

```bash
brew services restart ollama
ollama list
```

### Port conflicts

If API/UI ports are occupied, stop existing process and restart.

### Slow ingest

- First run is expected to take longer.
- Incremental runs should be faster (append-only path).

### Rebuild embeddings from scratch

```bash
rm -f data/email_rag.db
python scripts/ingest.py --source data/mailbox.mbox --type mbox
```

### Confirm which embedding backend is being used

- Check `GET /ingest/status` fields: `embedding_backend`, `embedding_model`
- Query responses from `POST /query` also include `embedding_backend` and `embedding_model`

## 9) Where to look next

- Product + architecture baseline: `docs/SPEC.md`
- High-level project readme: `README.md`
