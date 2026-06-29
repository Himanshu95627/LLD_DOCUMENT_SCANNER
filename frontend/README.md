# Grounded — frontend for the RAG backend

A clean React UI for the `LLD_DOCUMENT_SCANNER` backend (a FastAPI RAG pipeline).
You upload documents, ask questions, and get answers that **show their evidence**:
the exact chunks used, their retrieval/rerank scores, and per-step latency.

## Quick start

```bash
npm install
cp .env.example .env     # point VITE_API_BASE_URL at your backend
npm run dev              # serves on http://localhost:3000
```

The dev server is pinned to **port 3000** on purpose: the backend
(`backend/app/main.py`) only allows CORS from `http://localhost:3000`. If you
serve the frontend from anywhere else, add that origin to `allow_origins` in the
backend.

Run the backend separately (from the `backend/` folder), e.g.:

```bash
uvicorn app.main:app --reload   # http://localhost:8000
```

## What it covers (every backend endpoint)

| UI surface            | Endpoint                  |
| --------------------- | ------------------------- |
| Backend status pulse  | `GET /health`             |
| Upload / dropzone      | `POST /ingest`            |
| Library + delete      | `GET /documents`, `DELETE /documents/{id}` |
| Ask + answer + evidence | `POST /query`           |

It surfaces the full `/query` response, not just the answer:

- **Pipeline rail** — proportional bar of real `embed / retrieve / rerank / llm`
  latency (hidden automatically if the backend has `track_latency=False`).
- **Funnel** — `chunks_retrieved → chunks_sent_to_llm`.
- **Method badge** — `hybrid` vs `vector`.
- **Evidence chunks** — every retrieved chunk with similarity + rerank meters;
  the ones that actually fed the answer (`passed_to_llm`) are highlighted and
  expanded by default.
- **Depth control** — `top_k` slider (1–50).
- **Scope** — click a document in the library to restrict a question to it
  (`document_id`).

## Structure

```
src/
  api.js                 # all five endpoint calls, one place
  App.jsx                # state + composition
  styles.css             # design tokens + styles
  components/
    Sidebar.jsx          # health, upload, library, scope
    AskPanel.jsx         # question box, top_k, scope chip
    Answer.jsx           # answer + metrics + pipeline rail + funnel
    Sources.jsx          # evidence chunks with score meters
```

## Notes

- The backend's `/query` returns the full answer at once (no token streaming),
  so the UI shows a brief loading state rather than a fake typewriter.
- No auth in the backend, so there's no login flow.
- Supported uploads: PDF, plain text, Markdown (per the backend's allowlist).
