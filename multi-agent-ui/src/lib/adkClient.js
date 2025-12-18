// src/lib/adkClient.js

function safeJsonParse(s) {
  try {
    return JSON.parse(s);
  } catch {
    return null;
  }
}

export function newMessage(role, text) {
  return { role, parts: [{ text }] };
}

// ✅ יוצרת Session בשרת ומחזירה sessionId אמיתי
export async function createSession({ appName = "main_agent", userId = "user" } = {}) {
  // ADK Web: POST /apps/{app_name}/users/{user_id}/sessions
  const url = `/adk/apps/${encodeURIComponent(appName)}/users/${encodeURIComponent(userId)}/sessions`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state: {} }),
  });

  const txt = await res.text().catch(() => "");
  if (!res.ok) throw new Error(`createSession failed: ${res.status} ${res.statusText} ${txt}`);

  const obj = safeJsonParse(txt);
  // ברוב הגרסאות זה מגיע כ-session_id. אם זה שונה אצלך, ניפול עם שגיאה ברורה.
  const sessionId = obj?.session_id || obj?.sessionId || obj?.id;
  if (!sessionId) throw new Error(`createSession: server did not return session id. Body: ${txt}`);

  return sessionId;
}

/**
 * POST SSE endpoint and stream events.
 */
export async function sendMessageSSE({ message, sessionId, onEvent }) {
  const appName = "main_agent";
  const userId = "user";

  const url = "/adk/run_sse";

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      "Cache-Control": "no-cache",
    },
    body: JSON.stringify({
      appName,
      userId,
      sessionId,
      newMessage: newMessage("user", message),
    }),
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`run_sse failed: ${res.status} ${res.statusText} ${txt}`);
  }

  if (!res.body) throw new Error("No response body (stream) from server.");

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      for (const line of part.split("\n")) {
        if (!line.startsWith("data:")) continue;

        const data = line.slice(5).trim();
        if (!data) continue;
        if (data === "[DONE]") return;

        const obj = safeJsonParse(data);
        if (obj) onEvent?.(obj);
        else onEvent?.({ text: data });
      }
    }
  }
}
