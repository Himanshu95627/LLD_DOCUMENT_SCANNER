import { ArrowRight, X } from "lucide-react";

export default function AskPanel({
  query,
  onQuery,
  topK,
  onTopK,
  onAsk,
  loading,
  scopeName,
  onClearScope,
}) {
  function onKeyDown(e) {
    // Enter submits, Shift+Enter makes a newline.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (query.trim() && !loading) onAsk();
    }
  }

  return (
    <div className="ask">
      <div className="row">
        <textarea
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask anything about your documents…"
          maxLength={1000}
          rows={1}
        />
        <button className="send" onClick={onAsk} disabled={!query.trim() || loading}>
          {loading ? "Thinking…" : "Ask"}
          {!loading && <ArrowRight size={17} />}
        </button>
      </div>

      <div className="controls">
        <label className="topk">
          depth (top_k)
          <input
            type="range"
            min={1}
            max={50}
            value={topK}
            onChange={(e) => onTopK(Number(e.target.value))}
          />
          <span className="val">{topK}</span>
        </label>

        {scopeName && (
          <span className="scope-chip">
            scope: {scopeName}
            <button onClick={onClearScope} aria-label="Search all documents">
              <X size={13} />
            </button>
          </span>
        )}
      </div>
    </div>
  );
}
