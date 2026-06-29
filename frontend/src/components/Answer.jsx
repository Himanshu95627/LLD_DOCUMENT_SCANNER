// Renders the answer plus everything the backend exposes about HOW it got there:
// retrieval method, per-step latency (the signature "pipeline rail"), and the
// chunks_retrieved -> chunks_sent_to_llm funnel.

const STEPS = [
  { key: "embed_ms", cls: "embed", name: "embed" },
  { key: "retrieve_ms", cls: "retrieve", name: "retrieve" },
  { key: "rerank_ms", cls: "rerank", name: "rerank" },
  { key: "llm_ms", cls: "llm", name: "llm" },
];

function PipelineRail({ latency }) {
  // latency can be null if the backend has track_latency=False.
  if (!latency) return null;

  const steps = STEPS.map((s) => ({ ...s, ms: latency[s.key] })).filter(
    (s) => s.ms != null
  );
  const sum = steps.reduce((a, s) => a + s.ms, 0) || 1;

  return (
    <div className="rail">
      <div className="rail-bar">
        {steps.map((s) => (
          <div
            key={s.key}
            className={`rail-seg ${s.cls}`}
            style={{ flexGrow: s.ms / sum }}
            title={`${s.name}: ${s.ms} ms`}
          >
            {s.ms / sum > 0.12 ? `${Math.round(s.ms)}ms` : ""}
          </div>
        ))}
      </div>
      <div className="rail-legend">
        {steps.map((s) => (
          <span className="li" key={s.key}>
            <span className={`sw rail-seg ${s.cls}`} />
            {s.name} {s.ms}ms
          </span>
        ))}
      </div>
    </div>
  );
}

export default function Answer({ result }) {
  const {
    answer,
    query,
    retrieval_method,
    chunks_retrieved,
    chunks_sent_to_llm,
    latency,
  } = result;

  return (
    <div className="answer-wrap">
      <div className="answer-q">you asked — {query}</div>
      <div className="answer">{answer}</div>

      <div className="metrics">
        <span className="metric method">
          <span className="k">method</span>
          <span className="v">{retrieval_method}</span>
        </span>
        {latency && (
          <span className="metric">
            <span className="k">total</span>
            <span className="v">{latency.total_ms} ms</span>
          </span>
        )}
        <span className="metric">
          <span className="k">retrieved</span>
          <span className="v">{chunks_retrieved}</span>
        </span>
        <span className="metric">
          <span className="k">used</span>
          <span className="v">{chunks_sent_to_llm}</span>
        </span>
      </div>

      <PipelineRail latency={latency} />

      <div className="funnel">
        <b>{chunks_retrieved}</b> retrieved
        <span className="arrow">→</span>
        reranked
        <span className="arrow">→</span>
        <b>{chunks_sent_to_llm}</b> fed the answer
      </div>
    </div>
  );
}
