import { useState } from "react";
import { ChevronRight } from "lucide-react";

function ChunkCard({ chunk }) {
  const [open, setOpen] = useState(chunk.passed_to_llm);

  // similarity_score is cosine (~0..1) for vector, or an RRF score for hybrid;
  // either way clamp to 0..1 for the meter so the bar stays sane.
  const simPct = Math.max(0, Math.min(1, chunk.similarity_score)) * 100;
  const rerPct =
    chunk.rerank_score != null
      ? Math.max(0, Math.min(1, chunk.rerank_score)) * 100
      : null;

  const pos =
    chunk.page_number != null
      ? `p.${chunk.page_number} · #${chunk.chunk_index}`
      : `#${chunk.chunk_index}`;

  return (
    <div className={`chunk${chunk.passed_to_llm ? " used" : ""}`}>
      <button className="chunk-head" onClick={() => setOpen((o) => !o)}>
        <ChevronRight size={16} className={`chev${open ? " open" : ""}`} />
        <span className="src">
          {chunk.filename}
          <span className="pos">{pos}</span>
        </span>

        <span className="scores">
          <span className="score">
            <span>
              sim <span className="num">{chunk.similarity_score.toFixed(3)}</span>
            </span>
            <span className="meter sim">
              <i style={{ width: `${simPct}%` }} />
            </span>
          </span>
          {rerPct != null && (
            <span className="score">
              <span>
                rerank <span className="num">{chunk.rerank_score.toFixed(3)}</span>
              </span>
              <span className="meter rer">
                <i style={{ width: `${rerPct}%` }} />
              </span>
            </span>
          )}
        </span>

        {chunk.passed_to_llm && <span className="used-tag">used</span>}
      </button>

      {open && <div className="chunk-body">{chunk.content}</div>}
    </div>
  );
}

export default function Sources({ sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="sources">
      <p className="label">Evidence · {sources.length} chunks retrieved</p>
      {sources.map((c) => (
        <ChunkCard key={c.chunk_id} chunk={c} />
      ))}
    </div>
  );
}
