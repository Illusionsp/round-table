// Backend base URL. Update this alongside backend/main.py if you change
// the port (default: 8001, chosen to avoid clashing with other local apps).
const API_BASE = "http://localhost:8001/api";

async function handle(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function listConversations() {
  return handle(await fetch(`${API_BASE}/conversations`));
}

export async function createConversation() {
  return handle(await fetch(`${API_BASE}/conversations`, { method: "POST" }));
}

export async function getConversation(id) {
  return handle(await fetch(`${API_BASE}/conversations/${id}`));
}

export async function deleteConversation(id) {
  return handle(await fetch(`${API_BASE}/conversations/${id}`, { method: "DELETE" }));
}

export async function sendMessage(id, content) {
  return handle(
    await fetch(`${API_BASE}/conversations/${id}/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    })
  );
}
