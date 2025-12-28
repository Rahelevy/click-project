export function isHebrew(text = "") {
  return /[\u0590-\u05FF]/.test(text);
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// Small memoization for `isHebrew` to avoid re-running the regex for repeated texts.
const _hebrewCache = new Map();
export function isHebrewMemo(text = "") {
  if (_hebrewCache.has(text)) return _hebrewCache.get(text);
  const v = isHebrew(text);
  _hebrewCache.set(text, v);
  return v;
}

// Simple in-memory cache + in-flight dedupe to avoid duplicate work when the UI
// re-sends the same message rapidly (common when components re-render).
const _responseCache = new Map();
const _inFlight = new Map();
const DEFAULT_DELAY = 350; // reduce default latency for snappier dev experience

/**
 * חוזה שמדמה את RootAgent:
 * { stage: "awaiting_user_input"|"done", answer: string, state: object }
 */
export async function sendMessageMock({ message, sessionId } = {}, options = {}) {
  const delay = options.delay ?? DEFAULT_DELAY;
  const forceRefresh = !!options.forceRefresh;
  const signal = options.signal;

  const key = `${sessionId || "_"}::${message || ""}`;

  if (!forceRefresh && _responseCache.has(key)) {
    return structuredClone(_responseCache.get(key));
  }

  if (_inFlight.has(key)) {
    return _inFlight.get(key);
  }

  const p = (async () => {
    if (signal && signal.aborted) throw new Error("aborted");
    await sleep(delay);

    const he = isHebrewMemo(message);
    const lower = (message || "").toLowerCase();

  // "רחב מדי" -> Focus
  const tooBroad =
    lower.includes("show me all") ||
    lower.includes("all clicks") ||
    lower.includes("everything") ||
    message.includes("תראי לי הכל") ||
    message.includes("כל הקליקים") ||
    message.includes("כל הדאטה");

  // דוגמה: אם יש תאריך + app_id -> Done
  const hasDate =
    /\b\d{4}-\d{2}-\d{2}\b/.test(message) || /\b\d{2}-\d{2}-\d{4}\b/.test(message);
  const hasApp =
    /app\s*id\s*\d+/i.test(message) ||
    /app_id_\d+/i.test(message) ||
    message.includes("אפליקציה") ||
    message.includes("app id");

    if (tooBroad && !(hasDate && hasApp)) {
      const q = he
        ? "כדי להראות קליקים, על איזה טווח תאריכים את רוצה להסתכל?"
        : "To show clicks, what time range are you interested in?";

      const res = {
        stage: "awaiting_user_input",
        answer: q,
        state: {
          reason: "too_broad",
          missing_fields: ["date"],
        },
      };
      _responseCache.set(key, structuredClone(res));
      return res;
    }

    // תשובה "כאילו" מהמערכת (Done)
    const answer = he
      ? "סבבה — מצאתי תוצאות לפי הבקשה שלך. אם תרצי, אוכל גם לפלח לפי מקור/שותף או להציג Top 10."
      : "Done — I found results for your request. If you'd like, I can break it down by source/partner or show Top 10.";

    const res = {
      stage: "done",
      answer,
      state: {
        stage: "done",
        valid: true,
        session_id: sessionId,
      },
    };

    _responseCache.set(key, structuredClone(res));
    return res;
  })();

  // store and ensure cleanup when done
  _inFlight.set(key, p.finally ? p.finally(() => _inFlight.delete(key)) : p.then(() => _inFlight.delete(key), () => _inFlight.delete(key)));
  return p;
}
