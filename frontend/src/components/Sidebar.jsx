import { useRef, useState } from "react";
import { FileText, Trash2, UploadCloud } from "lucide-react";
import { SUPPORTED_HINT, SUPPORTED_TYPES } from "../api.js";

function HealthPulse({ status }) {
  const cls = status === "ok" ? "ok" : status === "down" ? "down" : "";
  const text =
    status === "ok" ? "backend online" : status === "down" ? "backend offline" : "checking…";
  return (
    <span className={`pulse ${cls}`}>
      <span className="led" />
      {text}
    </span>
  );
}

export default function Sidebar({
  health,
  documents,
  scopeId,
  onScope,
  onUpload,
  onDelete,
  uploading,
}) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);

  function pick(files) {
    const file = files && files[0];
    if (!file) return;
    onUpload(file);
  }

  function onDrop(e) {
    e.preventDefault();
    setDrag(false);
    pick(e.dataTransfer.files);
  }

  return (
    <aside className="sidebar">
      <div>
        <div className="brand">
          <span className="dot" />
          <h1>Grounded</h1>
        </div>
        <div className="tag" style={{ marginTop: 4 }}>
          answers tied to your sources
        </div>
        <div style={{ marginTop: 12 }}>
          <HealthPulse status={health} />
        </div>
      </div>

      <div>
        <p className="label">Add a document</p>
        <div
          className={`dropzone${drag ? " drag" : ""}${uploading ? " busy" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        >
          <UploadCloud size={26} strokeWidth={1.5} />
          <div>
            {uploading ? (
              <strong>Reading & embedding…</strong>
            ) : (
              <>
                <strong>Drop a file</strong> or click to browse
              </>
            )}
            <span className="hint">{SUPPORTED_HINT}</span>
          </div>
          <input
            ref={inputRef}
            type="file"
            hidden
            accept={SUPPORTED_TYPES.join(",")}
            onChange={(e) => pick(e.target.files)}
          />
        </div>
      </div>

      <div>
        <p className="label">
          Library{documents.length ? ` · ${documents.length}` : ""}
        </p>

        {documents.length === 0 ? (
          <p className="empty">No documents yet. Add one above to start asking questions.</p>
        ) : (
          <>
            {documents.map((d) => {
              const active = scopeId === d.id;
              return (
                <div key={d.id} className={`doc${active ? " active" : ""}`}>
                  <FileText size={16} className="doc-icon" />
                  <button
                    className="doc-body"
                    style={{ border: "none", background: "transparent", padding: 0, cursor: "pointer" }}
                    onClick={() => onScope(active ? null : d.id)}
                    title={active ? "Searching only this document — click to clear" : "Search only this document"}
                  >
                    <div className="name">{d.filename}</div>
                    <div className="meta">
                      {d.total_chunks} chunks · {new Date(d.created_at).toLocaleDateString()}
                    </div>
                    {active && <div className="scope-note">questions scoped here</div>}
                  </button>
                  <button
                    className="del"
                    aria-label={`Delete ${d.filename}`}
                    title="Delete document"
                    onClick={() => onDelete(d)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              );
            })}
          </>
        )}
      </div>
    </aside>
  );
}
