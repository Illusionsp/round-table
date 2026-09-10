import React, { useState } from "react";

export default function ChatInterface({ onSend, disabled }) {
  const [value, setValue] = useState("");

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="chat-input-bar">
      <textarea
        rows={3}
        value={value}
        placeholder="Ask the council something... (Enter to send, Shift+Enter for a new line)"
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
      />
      <button onClick={submit} disabled={disabled}>Send</button>
    </div>
  );
}
