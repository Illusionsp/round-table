import React from "react";
import ReactMarkdown from "react-markdown";

export default function Stage3({ content }) {
  return (
    <div className="stage3-panel">
      <div className="stage-label">Final answer</div>
      <div className="markdown-content">
        {content ? <ReactMarkdown>{content}</ReactMarkdown> : <em>The chairman model failed to produce a synthesis.</em>}
      </div>
    </div>
  );
}
