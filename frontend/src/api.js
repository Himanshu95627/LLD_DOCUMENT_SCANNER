// Single source of truth for talking to the RAG backend.
// Every call maps 1:1 to a route in backend/app/api/*.py.

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// File types the backend's /ingest endpoint accepts (see ingest.py SUPPORTED_TYPES).
export const SUPPORTED_TYPES = ["application/pdf", "text/plain", "text/markdown"];
export const SUPPORTED_HINT = ".pdf, .txt, .md";

async function parseError(res) {
  // FastAPI returns { detail: "..." } on HTTPException.
  try {
    const body = await res.json();
    if (body && body.detail) return body.detail;
  } catch {
    /* not JSON */
  }
  return `Request failed (${res.status})`;
}

// GET /health -> { status: "ok" }
export async function getHealth() {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

// GET /documents -> [{ id, filename, content_type, total_chunks, created_at }]
export async function listDocuments() {
  const res = await fetch(`${BASE}/documents`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

// POST /ingest (multipart, field name "file")
// -> { document_id, filename, total_chunks, message }
export async function ingestDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/ingest`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

// DELETE /documents/{id} -> 204
export async function deleteDocument(id) {
  const res = await fetch(`${BASE}/documents/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) throw new Error(await parseError(res));
  return true;
}

// POST /query { query, document_id?, top_k }
// -> { answer, query, sources[], chunks_retrieved, chunks_sent_to_llm,
//      retrieval_method, latency }
export async function askQuestion({ query, documentId = null, topK = 10 }) {
  const res = await fetch(`${BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      document_id: documentId,
      top_k: topK,
    }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}
