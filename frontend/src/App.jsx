import { useCallback, useEffect, useState } from "react";
import {
  askQuestion,
  deleteDocument,
  getHealth,
  ingestDocument,
  listDocuments,
} from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import AskPanel from "./components/AskPanel.jsx";
import Answer from "./components/Answer.jsx";
import Sources from "./components/Sources.jsx";

export default function App() {
  const [health, setHealth] = useState(null); // null = checking
  const [documents, setDocuments] = useState([]);
  const [scopeId, setScopeId] = useState(null); // restrict /query to one doc

  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(10);

  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);

  const flash = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2600);
  }, []);

  const refreshDocs = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
    } catch (e) {
      setError(e.message);
    }
  }, []);

  // Initial load + periodic health check.
  useEffect(() => {
    let alive = true;
    async function ping() {
      try {
        await getHealth();
        if (alive) setHealth("ok");
      } catch {
        if (alive) setHealth("down");
      }
    }
    ping();
    refreshDocs();
    const t = setInterval(ping, 15000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [refreshDocs]);

  async function handleUpload(file) {
    setError(null);
    setUploading(true);
    try {
      const res = await ingestDocument(file);
      await refreshDocs();
      flash(`Added “${res.filename}” — ${res.total_chunks} chunks`);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(doc) {
    setError(null);
    try {
      await deleteDocument(doc.id);
      if (scopeId === doc.id) setScopeId(null);
      await refreshDocs();
      flash(`Removed “${doc.filename}”`);
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleAsk() {
    const q = query.trim();
    if (!q) return;
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const res = await askQuestion({ query: q, documentId: scopeId, topK });
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const scopeName = scopeId
    ? documents.find((d) => d.id === scopeId)?.filename
    : null;

  return (
    <div className="app">
      <Sidebar
        health={health}
        documents={documents}
        scopeId={scopeId}
        onScope={setScopeId}
        onUpload={handleUpload}
        onDelete={handleDelete}
        uploading={uploading}
      />

      <main className="main">
        <AskPanel
          query={query}
          onQuery={setQuery}
          topK={topK}
          onTopK={setTopK}
          onAsk={handleAsk}
          loading={loading}
          scopeName={scopeName}
          onClearScope={() => setScopeId(null)}
        />

        {error && <div className="error">{error}</div>}

        {loading && (
          <div className="thinking">
            <div className="bar w1" />
            <div className="bar w2" />
            <div className="bar w3" />
            <div className="note">embedding · retrieving · reranking · generating…</div>
          </div>
        )}

        {!loading && result && (
          <>
            <Answer result={result} />
            <Sources sources={result.sources} />
          </>
        )}

        {!loading && !result && !error && (
          <div className="welcome">
            <h2>Ask your documents, see the receipts.</h2>
            <p>
              Every answer comes back with the exact chunks behind it, their
              retrieval and rerank scores, and how long each step took.
            </p>
            <ol>
              <li>Add a PDF, text, or Markdown file from the left.</li>
              <li>Type a question and press Enter.</li>
              <li>Open any evidence chunk to see what the model actually read.</li>
            </ol>
          </div>
        )}
      </main>

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
