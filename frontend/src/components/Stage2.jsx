import React, { useState } from "react";
import ReactMarkdown from "react-markdown";

// De-anonymization happens CLIENT-SIDE only, for display purposes.
// The models themselves only ever saw "Response A/B/C..." labels when
// producing these evaluations — labelToModel is not sent to them.
function deAnonymize(text, labelToModel) {
  if (!text || !labelToModel) return text;
  let result = text;
  for (const [label, model] of Object.entries(labelToModel)) {
    // Bold the model name in place of the raw label, readability only.
    result = result.split(label).join(`**${model}** (${label})`);
  }
  return result;
}

export default function Stage2({ rankings, labelToModel, aggregateRankings }) {
  const evaluated = (rankings || []).filter((r) => r.raw_text);
  const [active, setActive] = useState(0);

  if (evaluated.length === 0) {
    return (
      <div className="stage-panel">
        <div className="stage-label">Stage 2 — Peer review</div>
        <div>Not enough responses were available to run peer ranking.</div>
      </div>
    );
  }

  return (
    <div className="stage-panel">
      <div className="stage-label">Stage 2 — Peer review</div>
      <p className="disclaimer">
        Each model evaluated the responses under anonymous labels (Response A, B, C…) so it
        couldn't recognize or favor its own answer. Model names shown in <strong>bold</strong>{" "}
        below are added here purely for your readability — the evaluating model never saw them.
      </p>

      <div className="tab-bar">
        {evaluated.map((r, i) => (
          <button key={r.model} className={i === active ? "active" : ""} onClick={() => setActive(i)}>
            {r.model}
          </button>
        ))}
      </div>

      <div className="markdown-content">
        <ReactMarkdown>{deAnonymize(evaluated[active].raw_text, labelToModel)}</ReactMarkdown>
      </div>

      <div className="extracted-ranking">
        <strong>Extracted ranking:</strong>{" "}
        {evaluated[active].parsed_ranking.length > 0
          ? evaluated[active].parsed_ranking
              .map((label) => (labelToModel && labelToModel[label] ? `${labelToModel[label]} (${label})` : label))
              .join(" > ")
          : "could not parse a ranking from this response"}
      </div>

      {aggregateRankings && aggregateRankings.length > 0 && (
        <div className="aggregate-rankings">
          <strong>Aggregate ranking (avg. position across all evaluators):</strong>
          {aggregateRankings.map((a, i) => (
            <div className="aggregate-row" key={a.label}>
              <span>#{i + 1} — {a.model}</span>
              <span>
                {a.avg_position !== null ? `avg ${a.avg_position.toFixed(2)}` : "unranked"} ({a.vote_count} votes)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
