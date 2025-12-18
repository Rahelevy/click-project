import logging
from typing import AsyncGenerator, Dict, Any

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai.types import Content, Part
from main_agent.sub_agents.a_intent_agent.agent import IntentAgent
from main_agent.sub_agents.b_focus_agent.agent import FocusAgent
from main_agent.sub_agents.c_executor_agent.agent import ExecutorAgent
from main_agent.sub_agents.d_explanation_agent.agent import ExplainerAgent
from main_agent.sub_agents.d_explanation_agent.schemas import (
    ExplanationInput,
    ExecutorResult,
)
from main_agent.cache.bq_cache import get as bq_cache_get, set as bq_cache_set


logger = logging.getLogger("root_agent")
logger.debug(":feu: RootAgent module loaded")
class RootAgent(BaseAgent):
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
    def __repr__(self):
        return f"RootAgent(name={self.name})"
    def __init__(self, intent_agent, focus_agent, executor_agent, explainer_agent):
        super().__init__(
            name="main_agent_root",
            intent_agent=intent_agent,
            focus_agent=focus_agent,
            executor_agent=executor_agent,
            explainer_agent=explainer_agent,
            sub_agents=[intent_agent, focus_agent, executor_agent, explainer_agent],
        )

    # ---------------------------
    # helper: build user message when A awaits input
    # ---------------------------
    @staticmethod
    def _msg_from_intent(intent_state: Dict[str, Any]) -> str:
        reason = intent_state.get("reason")
        missing = intent_state.get("missing_fields", []) or []
        q_text = intent_state.get("question") or ""

        is_hebrew = any("א" <= ch <= "ת" for ch in q_text)

        if reason == "missing_question" or "question" in missing:
            return "לא קיבלתי שאלה. תוכלי לנסח שוב בבקשה?" if is_hebrew else \
                   "I didn't get a question. Could you rephrase it?"
        if reason == "invalid_date" or "date" in missing:
            return "התאריך לא ברור/לא תקין. תוכלי לציין תאריך או טווח תאריכים?" if is_hebrew else \
                   "The date is unclear/invalid. Could you provide a date or date range?"
        if reason == "invalid_app_id" or "app_id" in missing:
            return "ה-app id לא בפורמט תקין (app_id_<number>). תוכלי לציין אחד כזה?" if is_hebrew else \
                   "The app id format is invalid (app_id_<number>). Please provide a valid one."

        # fallback כללי
        return "חסרים פרטים כדי להמשיך. תוכלי לחדד?" if is_hebrew else \
               "We're missing details to continue. Could you clarify?"

    @staticmethod
    def _format_debug_trace(trace_list):
        """Format debug trace as markdown list"""
        if not trace_list:
            return ""
        return "\n\n---\n**Debug Trace:**\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(trace_list))

    # -----------------------------------------------------
    # Main Pipeline (synchronous helper used by async wrapper)
    # -----------------------------------------------------
    def run_pipeline(self, ctx: InvocationContext, session_state: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"[Root] start run_pipeline, user_content={getattr(ctx, 'user_content', None)}")
        logger.debug(f"[Root] session_state keys = {list(session_state.keys())}")

        # Initialize debug trace
        debug_trace = []
        debug_trace.append("User Input Received")

        # ---------- 1) Intent Agent (first pass) ----------
        try:
            a1 = self.intent_agent.run(ctx)
        except Exception:
            logger.exception("IntentAgent.run failed on InvocationContext, attempting fallback with question string.")
            try:
                q = getattr(ctx.user_content.parts[0], "text", str(ctx.user_content))
            except Exception:
                q = str(ctx.user_content)
            a1 = self.intent_agent.run({"question": q})

        intent_state = a1.get("state", {}) or {}
        logger.debug(f"[Root] Intent-1 output = {intent_state}")
        debug_trace.append(f"Intent Agent Round 1: valid={intent_state.get('valid', False)}")

        # אם A מבקש קלט משתמש (בעיקר empty question) — עונים מיד, בלי B
        if intent_state.get("awaiting_user_input"):
            msg = self._msg_from_intent(intent_state)
            debug_trace.append("Stopped: Waiting for User Input (Intent Agent)")
            return {
                "stage": "awaiting_user_input",
                "answer": msg + self._format_debug_trace(debug_trace),
                "state": intent_state,
            }

        should_run_focus = a1.get("should_run_focus", not intent_state.get("valid", False))
        should_run_executor = a1.get("should_run_executor", intent_state.get("valid", False))
        final_intent = intent_state

        # ---------- 2) Focus Agent (if needed) ----------
        if should_run_focus:
            logger.debug("[Root] Running FocusAgent")
            debug_trace.append("Focus Agent: Clarifying question")
            try:
                b = self.focus_agent.run(intent_state)
            except Exception:
                logger.exception("FocusAgent.run failed when passed dict; attempting with wrapped object.")
                b = self.focus_agent.run({"question": intent_state.get("question")})

            focus_state = b.get("state", {}) or {}
            logger.debug(f"[Root] Focus output = {focus_state}")

            # Focus asks the user
            if focus_state.get("awaiting_user_input"):
                debug_trace.append("Stopped: Waiting for User Input (Focus Agent)")
                q = focus_state.get("question_to_user") or \
                    ("אפשר לחדד את הבקשה?" if any("א" <= ch <= "ת" for ch in (final_intent.get("question") or "")) else
                     "Can you clarify your question?")
                return {
                    "stage": "awaiting_user_input",
                    "answer": q + self._format_debug_trace(debug_trace),
                    "state": focus_state,
                }

            # If focus provided refined question -> call IntentAgent again
            if focus_state.get("refined_question"):
                refined_q = focus_state["refined_question"]
                logger.debug(f"[Root] Intent-2 with refined question = {refined_q}")
                debug_trace.append(f"Intent Agent Round 2: Refined question = '{refined_q}'")

                try:
                    ctx2 = InvocationContext(user_content=Part(text=refined_q), session=ctx.session)
                except Exception:
                    class _FakePart:
                        def __init__(self, text):
                            self.text = text

                    class _FakeContent:
                        def __init__(self, text):
                            self.parts = [_FakePart(text)]

                    fake_ctx2 = type("FakeCtx", (), {"user_content": _FakeContent(refined_q), "session": ctx.session})
                    ctx2 = fake_ctx2()

                try:
                    a2 = self.intent_agent.run(ctx2)
                except Exception:
                    logger.exception("IntentAgent.run failed on refined InvocationContext; falling back to dict input.")
                    a2 = self.intent_agent.run({"question": refined_q})

                intent2_state = a2.get("state", {}) or {}
                logger.debug(f"[Root] Intent-2 output = {intent2_state}")
                debug_trace.append(f"Intent Agent Round 2: valid={intent2_state.get('valid', False)}")
                if intent2_state.get("awaiting_user_input"):
                    msg = self._msg_from_intent(intent2_state)
                    debug_trace.append("Stopped: Waiting for User Input (Intent Agent Round 2)")
                    return {
                        "stage": "awaiting_user_input",
                        "answer": msg + self._format_debug_trace(debug_trace),
                        "state": intent2_state,
                    }
                final_intent = intent2_state
                should_run_executor = a2.get("should_run_executor", final_intent.get("valid", False))
            else:
                final_intent = intent_state

        # ---------- 3) Executor ----------
        if not should_run_executor:
            if not final_intent.get("valid"):
                logger.debug("[Root] No executor run possible — missing info.")
                debug_trace.append("Stopped: Executor Skipped (Missing info)")
                is_hebrew = any("א" <= ch <= "ת" for ch in (final_intent.get("question") or ""))
                ask = (
                    "נראה שחסרים פרטים כדי להריץ את השאילתה. אפשר למקד לפי אפליקציה, מקור או טווח תאריכים?"
                    if is_hebrew else
                    "It seems we're missing details to run the query. Could you narrow down by app, source or date range?"
                )
                return {
                    "stage": "awaiting_user_input",
                    "answer": ask + self._format_debug_trace(debug_trace),
                    "state": final_intent,
                }

        executor_input = {
            "user_question": final_intent.get("question"),
            "sql": final_intent.get("sql"),
        }
        logger.debug(f"[Root] Executor input = {executor_input}")
        debug_trace.append("Executor: Running SQL query")

        # Check cache first (if SQL present). If hit, skip calling the Executor.
        exec_state = None
        sql_for_cache = final_intent.get("sql")
        if sql_for_cache:
            try:
                logger.debug(f"[Root] Cache lookup for SQL: {sql_for_cache[:100]}")
                cached = bq_cache_get(sql_for_cache)
                if cached is not None:
                    logger.info("[Root] ✓ CACHE HIT - Using cached result")
                    debug_trace.append("Cache Hit: Using cached result")
                    exec_state = cached
                else:
                    logger.debug("[Root] Cache lookup returned None (MISS)")
            except Exception:
                logger.exception("Cache lookup failed — proceeding to executor")

        if exec_state is None:
            try:
                c = self.executor_agent.run(executor_input)
            except Exception:
                logger.exception("ExecutorAgent.run failed with dict; attempting to pass via keyword fallback.")
                c = self.executor_agent.run(user_question=executor_input.get("user_question"), sql=executor_input.get("sql"))
            exec_state = c.get("state", {}) or {}
            logger.debug(f"[Root] Executor output = {exec_state}")
            debug_trace.append("Executor: Query completed")

            # Only cache successful executor results (best-effort): store if exec_state non-empty
            try:
                if sql_for_cache and exec_state:
                    logger.debug(f"[Root] Attempting cache write for SQL: {sql_for_cache[:80]}")
                    cache_ok = bq_cache_set(sql_for_cache, exec_state)
                    if cache_ok:
                        logger.info(f"[Root] ✓ Cache write successful for SQL: {sql_for_cache[:80]}")
                    else:
                        logger.warning(f"[Root] ✗ Cache write failed (returned False) for SQL: {sql_for_cache[:80]}")
                else:
                    logger.debug(f"[Root] Skipping cache write: sql_for_cache={bool(sql_for_cache)}, exec_state_empty={not bool(exec_state)}")
            except Exception:
                logger.exception("Failed to write cache for query")
        # ---------- 4) Explainer ----------
        # Explainer expects ExplanationInput pydantic. build it defensively.
        debug_trace.append("Explainer: Generating friendly response")
        logger.debug(f"[Root] exec_state keys: {exec_state.keys() if isinstance(exec_state, dict) else 'not a dict'}")
        logger.debug(f"[Root] exec_state type: {type(exec_state)}")
        try:
            incoming = exec_state.get("incoming", {})
            logger.debug(f"[Root] incoming type: {type(incoming)}, value: {incoming}")
            explain_input = ExplanationInput(
                user_question=exec_state.get("user_question") or executor_input.get("user_question"),
                incoming=ExecutorResult(
                    status=incoming.get("status") if isinstance(incoming, dict) else incoming.status,
                    description=incoming.get("description") if isinstance(incoming, dict) else incoming.description,
                ),
                db_result=exec_state.get("db_result"),
                sql=final_intent.get("sql"),
            )
        except Exception as e:
            logger.exception(f"[Root] Failed to build ExplanationInput: {e}")
            # last-resort: pass a simple dict to explainer_agent.run
            explain_input = {
                "user_question": exec_state.get("user_question") or executor_input.get("user_question"),
                "incoming": exec_state.get("incoming"),
                "db_result": exec_state.get("db_result"),
                "sql": final_intent.get("sql"),
            }
        try:
            d = self.explainer_agent.run(explain_input)
        except Exception as e:
            logger.exception(f"[Root] ExplainerAgent.run failed: {e}; attempting with dict input.")
            d = self.explainer_agent.run(explain_input if isinstance(explain_input, dict) else explain_input.model_dump())
        explain_state = d.get("state", {}) or {}
        logger.debug(f"[Root] Explainer output = {explain_state}")
        debug_trace.append("Pipeline Complete")
        # Convert Pydantic -> dict if needed
        if hasattr(explain_state, "model_dump"):
            explain_state = explain_state.model_dump()
        
        answer_text = explain_state.get("description", "") if isinstance(explain_state, dict) else str(explain_state)
        
        return {
            "stage": "done",
            "answer": answer_text + self._format_debug_trace(debug_trace),
            "state": explain_state,
        }
    # -----------------------------------------------------
    # ADK Async Wrapper
    # -----------------------------------------------------
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        session_state = ctx.session.state.get("root_state", {})
        logger.debug(f"[Root] Async start: {getattr(ctx, 'user_content', None)}")
        result = self.run_pipeline(ctx, session_state)
        logger.debug(f"[Root] Final Output = stage={result.get('stage')} answer={result.get('answer')}")
        # Update session
        actions = EventActions(
            state_delta={
                "root_state": result["state"],
                "stage": result["stage"],
            }
        )
        msg = Content(
            role="assistant",
            parts=[Part(text=result.get("answer", "No answer returned."))],
        )
        yield Event(
            author=self.name,
            content=msg,
            actions=actions,
        )
root_agent = RootAgent(
    intent_agent=IntentAgent(),
    focus_agent=FocusAgent(),
    executor_agent=ExecutorAgent(),
    explainer_agent=ExplainerAgent(),
)
