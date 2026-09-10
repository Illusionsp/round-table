import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import Sidebar from "./components/Sidebar.jsx";
import ChatInterface from "./components/ChatInterface.jsx";
import Stage1 from "./components/Stage1.jsx";
import Stage2 from "./components/Stage2.jsx";
import Stage3 from "./components/Stage3.jsx";
import * as api from "./api.js";

export default function App() {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [conversation, setConversation] = useState(null);
  // metadata is ephemeral (per API design) — keyed by message index, since
  // it's only returned by the API for the message just sent, not on reload.
  const [metadataByIndex, setMetadataByIndex] = useState({});
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  const refreshList = async () => {
    setConversations(await api.listConversations());
  };

  useEffect(() => { refreshList(); }, []);

  const selectConversation = async (id) => {
    setActiveId(id);
    setMetadataByIndex({});
    setConversation(await api.getConversation(id));
  };

  const newConversation = async () => {
    const conv = await api.createConversation();
    setActiveId(conv.id);
    setConversation(conv);
    setMetadataByIndex({});
    await refreshList();
  };

  const handleSend = async (content) => {
    setError(null);
    let id = activeId;
    if (!id) {
      const conv = await api.createConversation();
      id = conv.id;
      setActiveId(id);
      await refreshList();
    }
    setSending(true);
    try {
      const result = await api.sendMessage(id, content);
      setConversation(result.conversation);
      const assistantIndex = result.conversation.messages.length - 1;
      setMetadataByIndex((prev) => ({ ...prev, [assistantIndex]: result.metadata }));
      await refreshList();
    } catch (e) {
      setError(e.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="app-layout">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConversation}
        onNew={newConversation}
      />
      <div className="main-panel">
        {(conversation?.messages || []).map((msg, i) => (
          <div className="message-block" key={i}>
            {msg.role === "user" ? (
              <div className="user-message markdown-content">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            ) : (
              <>
                <Stage1 responses={msg.stage1 || []} />
                <Stage2
                  rankings={msg.stage2 || []}
                  labelToModel={metadataByIndex[i]?.label_to_model}
                  aggregateRankings={metadataByIndex[i]?.aggregate_rankings}
                />
                <Stage3 content={msg.stage3} />
              </>
            )}
          </div>
        ))}
        {sending && <div className="loading-indicator">The council is deliberating…</div>}
        {error && <div className="loading-indicator" style={{ color: "crimson" }}>{error}</div>}
      </div>
      <div style={{ position: "fixed", bottom: 0, left: 260, right: 0 }}>
        <ChatInterface onSend={handleSend} disabled={sending} />
      </div>
    </div>
  );
}
