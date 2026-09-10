import React from "react";

export default function Sidebar({ conversations, activeId, onSelect, onNew }) {
  return (
    <div className="sidebar">
      <button className="new-chat" onClick={onNew}>+ New conversation</button>
      {conversations.map((c) => (
        <div
          key={c.id}
          className={`conversation-item ${c.id === activeId ? "active" : ""}`}
          onClick={() => onSelect(c.id)}
        >
          {c.preview || "New conversation"}
        </div>
      ))}
    </div>
  );
}
