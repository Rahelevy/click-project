export function isHebrew(text = "") {
  return /[\u0590-\u05FF]/.test(text);
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * חוזה שמדמה את RootAgent:
 * { stage: "awaiting_user_input"|"done", answer: string, state: object }
 */
export async function sendMessageMock({ message, sessionId }) {
  await sleep(550);

  const he = isHebrew(message);
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

    return {
      stage: "awaiting_user_input",
      answer: q,
      state: {
        reason: "too_broad",
        missing_fields: ["date"],
      },
    };
  }

  // תשובה "כאילו" מהמערכת (Done)
  const answer = he
    ? "סבבה — מצאתי תוצאות לפי הבקשה שלך. אם תרצי, אוכל גם לפלח לפי מקור/שותף או להציג Top 10."
    : "Done — I found results for your request. If you'd like, I can break it down by source/partner or show Top 10.";

  return {
    stage: "done",
    answer,
    state: {
      stage: "done",
      valid: true,
      session_id: sessionId,
    },
  };
}
