import React, { useState } from "react";
import ReactMarkdown from "react-markdown";

// Tab view of each council model's individual (Stage 1) response.
export default function Stage1({ responses }) {
  const available = responses.filter((r) => r.content);
  const [active, setActive] = useState(0);

  if (available.length === 0) {
    return <div className="stage-panel">All council models failed to respond in Stage 1.</div>;
  }

  return (
    <div className="stage-panel">
      <div className="stage-label">Stage 1 — Individual responses</div>
      <div className="tab-bar">
        {available.map((r, i) => (
          <button
            key={r.model}
            className={i === active ? "active" : ""}
            onClick={() => setActive(i)}
          >
            {r.model}
          </button>
        ))}
      </div>
      <div className="markdown-content">
        <ReactMarkdown>{available[active].content}</ReactMarkdown>
      </div>
    </div>
  );
}
