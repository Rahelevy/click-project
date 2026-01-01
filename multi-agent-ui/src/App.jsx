import React, { useEffect, useMemo, useRef, useState } from "react";
import { sendMessageSSE, createSession } from "./lib/adkClient";
import { TableRenderer } from "./components/renderers/TableRenderer";
import { ChartRenderer } from "./components/renderers/ChartRenderer";
import { isHebrew } from "./lib/mockApi";

function cx(...arr) {
  return arr.filter(Boolean).join(" ");
}
function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}
function formatTime(d = new Date()) {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function Bubble({ role, text, meta }) {
  const isUser = role === "user";
  return (
    <div className={cx("flex w-full", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cx(
          "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
          isUser
            ? "bg-sky-600/90 text-white"
            : "bg-white/5 text-white/90 border border-white/10"
        )}
      >
        <div className="whitespace-pre-wrap [unicode-bidi:plaintext]">
          {String(text ?? "")
            .split("\n")
            .map((line, i) => (
              <div key={i} dir="auto">
                {line}
              </div>
            ))}
        </div>

        {meta?.time && (
          <div
            className={cx(
              "mt-2 text-[10px] opacity-70",
              isUser ? "text-white/80" : "text-white/60"
            )}
          >
            {meta.time}
          </div>
        )}
      </div>
    </div>
  );
}

function Typing() {
  return (
    <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/70">
      <span className="inline-flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-white/40 [animation-delay:-0.2s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-white/40 [animation-delay:-0.1s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-white/40" />
      </span>
      <span>Thinking…</span>
    </div>
  );
}

const LS_KEY_CONVOS = "multi_agent_ui_convos_v1";
const LS_KEY_ACTIVE = "multi_agent_ui_active_id_v1";

export default function App() {
  const didInitRef = useRef(false); // ✅ Guard for StrictMode double-run

  const [sessionId, setSessionId] = useState(null);
  const [sessionError, setSessionError] = useState(null);
  const [showDebug, setShowDebug] = useState(true);

  const [convos, setConvos] = useState(() => {
    try {
      const raw = localStorage.getItem(LS_KEY_CONVOS);
      if (raw) return JSON.parse(raw);
    } catch {}
    return [];
  });

  const [activeId, setActiveId] = useState(() => {
    try {
      const raw = localStorage.getItem(LS_KEY_ACTIVE);
      return raw || null;
    } catch {
      return null;
    }
  });

  // ✅ One-time init that NEVER creates multiple chats
  useEffect(() => {
    if (didInitRef.current) return;
    didInitRef.current = true;

    // If no convos exist, create exactly one
    if (!convos || convos.length === 0) {
      const id = uid();
      const firstChat = {
        id,
        title: "New chat",
        messages: [
          {
            id: uid(),
            role: "assistant",
            text: "היי! מה תרצה לדעת?\nHi! What would you like to know?",
            meta: { time: formatTime() },
            debugState: { stage: "idle" },
          },
        ],
      };
      setConvos([firstChat]);
      setActiveId(id);
      return;
    }

    // If convos exist, ensure activeId valid
    const exists = convos.some((c) => c.id === activeId);
    if (!activeId || !exists) setActiveId(convos[0].id);
  }, []); // ✅ IMPORTANT: empty deps

  // ✅ Persist to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(LS_KEY_CONVOS, JSON.stringify(convos));
      localStorage.setItem(LS_KEY_ACTIVE, String(activeId || ""));
    } catch {}
  }, [convos, activeId]);

  const active = useMemo(
    () => convos.find((c) => c.id === activeId),
    [convos, activeId]
  );

  const [input, setInput] = useState("");
  const [isLoading, setLoading] = useState(false);
  const listRef = useRef(null);

  const lastAssistant = useMemo(() => {
    if (!active) return null;
    return [...active.messages].reverse().find((m) => m.role === "assistant");
  }, [active]);

  const lastDebug = useMemo(() => lastAssistant?.debugState || null, [lastAssistant]);

  function scrollToBottom() {
    requestAnimationFrame(() => {
      const el = listRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    });
  }

  function updateActive(updater) {
    setConvos((prev) => prev.map((c) => (c.id === activeId ? updater(c) : c)));
  }

  function newChat() {
    const id = uid();
    const chat = {
      id,
      title: "New chat",
      messages: [
        {
          id: uid(),
          role: "assistant",
          text: "היי! מה תרצה לדעת?\nHi! What would you like to know?",
          meta: { time: formatTime() },
          debugState: { stage: "idle" },
        },
      ],
    };
    setConvos((prev) => [chat, ...prev]);
    setActiveId(id);
    setInput("");
  }

  function deleteChat(chatId) {
    setConvos((prev) => prev.filter((c) => c.id !== chatId));
    if (chatId === activeId) {
      setTimeout(() => {
        const remaining = convos.filter((c) => c.id !== chatId);
        setActiveId(remaining[0]?.id || null);
      }, 0);
    }
  }

  function clearHistory() {
    const ok = window.confirm(
      "Are you sure you want to delete all chats? This cannot be undone."
    );
    if (!ok) return;
    localStorage.removeItem(LS_KEY_CONVOS);
    localStorage.removeItem(LS_KEY_ACTIVE);
    didInitRef.current = false;
    setConvos([]);
    setActiveId(null);
    setTimeout(() => window.location.reload(), 50);
  }

  // ✅ create session once
  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const sid = await createSession({ appName: "main_agent", userId: "user" });
        if (!cancelled) setSessionId(sid);
      } catch (e) {
        if (!cancelled) setSessionError(String(e));
      }
    }
    boot();
    return () => {
      cancelled = true;
    };
  }, []);

  async function send(text) {
    const msg = (text ?? input).trim();
    if (!msg || !active) return;

    if (!sessionId) {
      updateActive((c) => ({
        ...c,
        messages: [
          ...c.messages,
          {
            id: uid(),
            role: "assistant",
            text: "⚠️ עדיין מתחברת לשרת (Session). נסי שוב עוד רגע.",
            meta: { time: formatTime() },
            debugState: { stage: "error", error: "session_not_ready" },
          },
        ],
      }));
      return;
    }

    setLoading(true);

    updateActive((c) => ({
      ...c,
      title:
        c.title === "New chat"
          ? msg.slice(0, 24) + (msg.length > 24 ? "…" : "")
          : c.title,
      messages: [
        ...c.messages,
        { id: uid(), role: "user", text: msg, meta: { time: formatTime() } },
      ],
    }));

    setInput("");
    scrollToBottom();

    const assistantId = uid();
    updateActive((c) => ({
      ...c,
      messages: [
        ...c.messages,
        {
          id: assistantId,
          role: "assistant",
          text: "",
          meta: { time: formatTime() },
          debugState: { stage: "streaming" },
          uiState: null,
        },
      ],
    }));

    try {
      let lastText = "";

      await sendMessageSSE({
        message: msg,
        sessionId,
        onEvent: (evt) => {
          const chunk =
            evt?.answer ??
            evt?.text ??
            evt?.delta ??
            evt?.content?.parts?.[0]?.text ??
            evt?.content?.text ??
            "";

          const rootState = evt?.actions?.stateDelta?.root_state;

          const stage =
            evt?.stage ??
            evt?.actions?.stateDelta?.stage ??
            rootState?.stage ??
            null;

          const questionToUser =
            rootState?.focus_state?.question_to_user ??
            null;

          updateActive((c) => ({
            ...c,
            messages: c.messages.map((m) =>
              m.id === assistantId
                ? { ...m, debugState: evt, uiState: rootState ?? m.uiState }
                : m
            ),
          }));

          if (stage === "awaiting_user_input" && questionToUser) {
            updateActive((c) => ({
              ...c,
              messages: c.messages.map((m) =>
                m.id === assistantId
                  ? { ...m, text: questionToUser, debugState: evt }
                  : m
              ),
            }));
            return;
          }

          if (!chunk) return;
          lastText += chunk;

          updateActive((c) => ({
            ...c,
            messages: c.messages.map((m) =>
              m.id === assistantId ? { ...m, text: lastText, debugState: evt } : m
            ),
          }));
        },
      });
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }

  return (
    <div className="h-full w-full bg-[#0b0f14] text-white">
      <div className="flex h-full">
        {/* Sidebar */}
        <aside className="hidden w-[280px] flex-col border-r border-white/10 bg-black/20 md:flex">
          <div className="flex items-center justify-between px-4 py-4">
            <div className="text-sm font-semibold tracking-wide text-white/90">
              Multi-Agent UI
            </div>
            <button
              onClick={newChat}
              className="rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/80 hover:bg-white/10"
              type="button"
            >
              New chat
            </button>
          </div>

          <div className="px-4 pb-3">
            <button
              onClick={clearHistory}
              className="w-full rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-200 hover:bg-red-500/20"
              type="button"
            >
              Clear History
            </button>
          </div>

          <div className="px-2 pb-3">
            <div className="mb-2 px-2 text-[11px] uppercase tracking-wider text-white/40">
              Chats
            </div>
            <div className="space-y-1">
              {convos.map((c) => (
                <div
                  key={c.id}
                  className={cx(
                    "group flex items-center justify-between rounded-xl px-3 py-2",
                    c.id === activeId
                      ? "bg-white/10 text-white"
                      : "text-white/70 hover:bg-white/5"
                  )}
                >
                  <button
                    onClick={() => setActiveId(c.id)}
                    className="min-w-0 flex-1 truncate text-left text-sm"
                    type="button"
                  >
                    {c.title}
                  </button>

                  <button
                    onClick={() => {
                      const ok = window.confirm(
                        isHebrew(c.title)
                          ? "בטוחה שאת רוצה למחוק את הצ׳אט הזה?"
                          : "Are you sure you want to delete this chat?"
                      );
                      if (ok) deleteChat(c.id);
                    }}
                    className="ml-2 hidden rounded-md px-2 py-1 text-xs text-white/40 hover:bg-white/10 hover:text-white group-hover:block"
                    type="button"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-auto border-t border-white/10 p-4">
            <div className="text-[11px] text-white/50">
              Session:{" "}
              <span className="font-mono">
                {sessionId ? `${sessionId.slice(0, 10)}…` : "connecting…"}
              </span>
            </div>
            {sessionError && (
              <div className="mt-2 text-[11px] text-red-300">
                Session error: {sessionError}
              </div>
            )}
          </div>
        </aside>

        {/* Main */}
        <main className="flex min-w-0 flex-1">
          <div className="flex min-w-0 flex-1 flex-col">
            {/* Top bar */}
            <div className="flex items-center justify-between border-b border-white/10 bg-black/10 px-4 py-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowDebug((s) => !s)}
                  className="rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/80 hover:bg-white/10"
                  type="button"
                >
                  {showDebug ? "Hide debug" : "Show debug"}
                </button>
                <div className="text-xs text-white/50">
                  Bilingual: Hebrew/English auto-detect
                </div>
              </div>
              <div className="text-xs text-white/50">
                Stage:{" "}
                <span className="text-white/80">{lastDebug?.stage || "idle"}</span>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-auto px-4 py-6">
              <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
                {active?.messages?.map((m) => {
                  if (m.role === "assistant" && m.uiState?.render_type === "table") {
                    return (
                      <div key={m.id} className="flex justify-start">
                        <TableRenderer state={m.uiState} />
                      </div>
                    );
                  }
                  if (m.role === "assistant" && m.uiState?.render_type === "chart") {
                    return (
                      <div key={m.id} className="flex justify-start">
                        <ChartRenderer state={m.uiState} />
                      </div>
                    );
                  }
                  return <Bubble key={m.id} role={m.role} text={m.text} meta={m.meta} />;
                })}
                {isLoading && (
                  <div className="flex justify-start">
                    <Typing />
                  </div>
                )}
              </div>
            </div>

            {/* Composer */}
            <div className="border-t border-white/10 bg-black/20 px-4 py-4">
              <div className="mx-auto flex w-full max-w-3xl items-end gap-3">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send();
                    }
                  }}
                  placeholder="Type a message… (עברית / English)"
                  className="min-h-[52px] flex-1 resize-none rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/90 outline-none placeholder:text-white/40 focus:border-white/20"
                />
                <button
                  onClick={() => send()}
                  disabled={isLoading || !input.trim() || !sessionId}
                  className={cx(
                    "rounded-2xl px-4 py-3 text-sm font-medium",
                    isLoading || !input.trim() || !sessionId
                      ? "bg-white/10 text-white/40"
                      : "bg-sky-600/90 text-white hover:bg-sky-600"
                  )}
                  type="button"
                >
                  Send
                </button>
              </div>
              <div className="mx-auto mt-2 w-full max-w-3xl text-[11px] text-white/40">
                Enter לשליחה • Shift+Enter לשורה חדשה
              </div>
            </div>
          </div>

          {/* Debug */}
          {showDebug && (
            <aside className="hidden w-[360px] shrink-0 border-l border-white/10 bg-black/20 lg:block">
              <div className="border-b border-white/10 px-4 py-3">
                <div className="text-sm font-semibold text-white/90">Debug</div>
              </div>
              <div className="p-4">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                  <div className="mb-2 text-xs font-semibold text-white/80">
                    Raw payload
                  </div>
                  <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap break-words rounded-xl bg-black/30 p-3 text-[11px] text-white/70">
                    {JSON.stringify(lastDebug, null, 2)}
                  </pre>
                </div>
              </div>
            </aside>
          )}
        </main>
      </div>
    </div>
  );
}
