import React, { useEffect, useMemo, useRef, useState } from "react";
import { isHebrew } from "./lib/mockApi";
import { sendMessageSSE, createSession } from "./lib/adkClient";

function cx(...arr) {
  return arr.filter(Boolean).join(" ");
}

function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

function formatTime(d = new Date()) {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function Chip({ children, onClick }) {
  return (
    <button
      onClick={onClick}
      className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/80 hover:bg-white/10"
      type="button"
    >
      {children}
    </button>
  );
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

export default function App() {
  // ✅ sessionId אמיתי שמגיע מהשרת (לא uid())
  const [sessionId, setSessionId] = useState(null);
  const [sessionError, setSessionError] = useState(null);

  const [showDebug, setShowDebug] = useState(true);

  const [convos, setConvos] = useState(() => [
    {
      id: uid(),
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
    },
  ]);

  const [activeId, setActiveId] = useState(convos[0].id);

  const active = useMemo(
    () => convos.find((c) => c.id === activeId),
    [convos, activeId]
  );

  const [input, setInput] = useState("");
  const [isLoading, setLoading] = useState(false);

  const listRef = useRef(null);

  const lastDebug = useMemo(() => {
    if (!active) return null;
    const last = [...active.messages].reverse().find((m) => m.role === "assistant");
    return last?.debugState || null;
  }, [active]);

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
    setConvos((prev) => [
      {
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
      },
      ...prev,
    ]);
    setActiveId(id);
    setInput("");
  }

  // ✅ יצירת Session אמיתי מהשרת פעם אחת כשהאפליקציה עולה
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

  // ✅ UPDATED: send() uses SSE streaming + extracts correct text from ADK payload
  async function send(text) {
    const msg = (text ?? input).trim();
    if (!msg || !active) return;

    // אם עוד אין sessionId אמיתי, לא שולחים
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

    // add user message
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

    // add empty assistant message
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
        },
      ],
    }));

    try {
      let lastText = "";

      await sendMessageSSE({
        message: msg,
        sessionId,
        onEvent: (evt) => {
          // ✅ הכי חשוב: לקחת טקסט אמיתי מה־ADK
          const chunk =
            evt?.answer ??
            evt?.text ??
            evt?.delta ??
            evt?.content?.parts?.[0]?.text ??
            evt?.content?.text ??
            "";

          // תמיד נעדכן debugState, אבל נוסיף טקסט רק אם יש chunk
          updateActive((c) => ({
            ...c,
            messages: c.messages.map((m) =>
              m.id === assistantId ? { ...m, debugState: evt } : m
            ),
          }));

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

      // mark done
      updateActive((c) => ({
        ...c,
        messages: c.messages.map((m) =>
          m.id === assistantId
            ? { ...m, debugState: { ...(m.debugState || {}), stage: "done" } }
            : m
        ),
      }));
    } catch (err) {
      updateActive((c) => ({
        ...c,
        messages: c.messages.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                text: "⚠️ Error: failed to stream response.",
                debugState: { stage: "error", error: String(err) },
              }
            : m
        ),
      }));
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }

  // Quick replies when awaiting input
  const quickReplies = useMemo(() => {
    const stage = lastDebug?.stage;
    if (stage !== "awaiting_user_input") return [];

    const he = isHebrew(active?.messages?.slice(-1)?.[0]?.text || "") || false;

    return he
      ? ["היום", "אתמול", "שבוע אחרון", "טווח תאריכים (YYYY-MM-DD עד YYYY-MM-DD)"]
      : ["Today", "Yesterday", "Last 7 days", "Date range (YYYY-MM-DD to YYYY-MM-DD)"];
  }, [lastDebug, active]);

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

          <div className="px-2 pb-3">
            <div className="mb-2 px-2 text-[11px] uppercase tracking-wider text-white/40">
              Chats
            </div>
            <div className="space-y-1">
              {convos.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setActiveId(c.id)}
                  className={cx(
                    "w-full rounded-xl px-3 py-2 text-left text-sm",
                    c.id === activeId
                      ? "bg-white/10 text-white"
                      : "text-white/70 hover:bg-white/5"
                  )}
                  type="button"
                >
                  <div className="truncate">{c.title}</div>
                </button>
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
                Stage: <span className="text-white/80">{lastDebug?.stage || "idle"}</span>
              </div>
            </div>

            {/* Messages */}
            <div ref={listRef} className="flex-1 overflow-auto px-4 py-6">
              <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
                {active?.messages?.map((m) => (
                  <Bubble key={m.id} role={m.role} text={m.text} meta={m.meta} />
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <Typing />
                  </div>
                )}

                {/* Quick replies */}
                {quickReplies.length > 0 && !isLoading && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {quickReplies.map((q) => (
                      <Chip key={q} onClick={() => send(q)}>
                        {q}
                      </Chip>
                    ))}
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

          {/* Debug Drawer */}
          {showDebug && (
            <aside className="hidden w-[360px] shrink-0 border-l border-white/10 bg-black/20 lg:block">
              <div className="border-b border-white/10 px-4 py-3">
                <div className="text-sm font-semibold text-white/90">Debug</div>
                <div className="text-xs text-white/50">
                  Last assistant state (mocked RootAgent output)
                </div>
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

                <div className="mt-4 text-[11px] text-white/50">
                  כשתחברי ל-backend אמיתי, פשוט נחליף את{" "}
                  <span className="font-mono">sendMessageMock</span> ב-fetch.
                </div>
              </div>
            </aside>
          )}
        </main>
      </div>
    </div>
  );
}
