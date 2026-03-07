# Email RAG MVP Spec (Baseline + Target)

## 1) Context

This document captures:

1. **Where we started** (problem + constraints)
2. **What was built in MVP v0**
3. **What we want next** (roadmap)

Primary user requirement: **show original email results first; LLM response is secondary**.

---

## 2) Problem Statement

Need a local Mac app/service that can:

- ingest large local email datasets (starting with one mailbox)
- answer user questions over that corpus
- keep answers trustworthy by prioritizing original source emails
- support incremental append-only updates
- expose confidence and ingestion ETA/progress

Privacy-first: local-first stack, no cloud dependency required for core operation.

---

## 3) MVP Scope (what we built)

### In-scope

- One mailbox focus
- Input support:
  - MBOX
  - text files/folders
- Local storage/indexing:
  - SQLite metadata tables
  - local vector storage + cosine retrieval path
- Query modes:
  - Search mode (email evidence results)
  - Ask mode (email evidence + secondary LLM answer)
- Confidence:
  - per-result confidence
  - overall answer confidence
- Ingestion status:
  - progress endpoint
  - ETA estimate (sample-based + live throughput)
- Incremental indexing (append-only assumption)
- Test suite and git history

### Out-of-scope (for current MVP)

- Multi-mailbox orchestration
- Full attachment extraction/OCR pipeline
- Native macOS app packaging
- Enterprise auth/roles
- Background daemonized scheduler

---

## 4) Architecture (MVP)

```text
Streamlit UI
  ├─ Ingest page
  ├─ Search page
  └─ Ask page
      │
      ▼
FastAPI service
  ├─ /ingest/start
  ├─ /ingest/status
  ├─ /query
  └─ /health
      │
      ▼
Core modules (app/)
  ├─ ingest.py      (parse + incremental ingest + progress)
  ├─ embedding.py   (ollama embeddings + local fallback)
  ├─ retrieval.py   (vector retrieval + scoring)
  ├─ answer.py      (LLM answer as secondary output)
  ├─ db.py          (SQLite schema/access)
  └─ api/main.py    (HTTP endpoints)
```

---

## 5) Data/Ranking Behavior

### Email-first display contract

1. Retrieval returns top evidence emails/chunks
2. UI/API returns these as primary results
3. LLM synthesis is generated after evidence retrieval and shown as secondary

### Confidence (deterministic)

Per result:

- `result_confidence = 0.7 * retrieval_score + 0.3 * evidence_coverage`

Overall answer:

- `overall_confidence = 0.8 * avg(result_confidence) + 0.2 * answer_coverage`

---

## 6) Incremental Indexing Contract

Append-only assumption:

- emails only added, existing content unchanged
- ingestion tracks processed boundary (offset/checkpoint)
- subsequent runs process only newly appended messages

This enables large mailbox operation without full re-index on every run.

---

## 7) Current Repository State (baseline)

- Project root: `~/Projects/email-rag-mvp`
- Tests: present and passing
- Initial commits include scaffold + test-compat refinements

---

## 8) Known Constraints / Risks

- Quality depends on chunking strategy and embedding quality.
- ETA estimates can drift on highly variable email sizes.
- Pure-SQLite vector retrieval is simple and local but not optimized for very large corpora.

---

## 9) Next Milestones (target state)

### Milestone 1 — harden MVP

- better parser coverage (HTML-heavy, malformed MIME)
- richer metadata filters (date/from/subject/thread)
- improve confidence calibration with validation set

### Milestone 2 — scale

- optional high-performance vector backend abstraction
- batched/parallel embedding pipeline with safe throttling
- larger corpus benchmarking (10GB/30GB datasets)

### Milestone 3 — UX + productization

- richer query UX, citation navigation, thread timeline
- stronger ingest dashboard (remaining chunks/sec, completion windows)
- packaging path toward desktop app shell (Tauri/SwiftUI wrapper)

---

## 10) Definition of Done (for current MVP)

Done =

1. local install works on Mac with Ollama
2. can ingest one mailbox
3. can search and ask
4. originals shown first, LLM answer second
5. confidence + ETA visible
6. tests pass
7. code committed

This condition is currently met for baseline MVP scaffold.
