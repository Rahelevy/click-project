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
from main_agent.sub_agents.anomaly_agent.agent import AnomalyAgent
from main_agent.cache.bq_cache import get as bq_cache_get, set as bq_cache_set


logger = logging.getLogger("root_agent")
logger.debug("RootAgent module loaded")
class RootAgent(BaseAgent):
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
    def __repr__(self):
        return f"RootAgent(name={self.name})"
    def __init__(self, intent_agent, focus_agent, executor_agent, explainer_agent, anomaly_agent):
        super().__init__(
            name="main_agent_root",
            sub_agents=[intent_agent, focus_agent, executor_agent, explainer_agent],
        )
        # Store agents after Pydantic initialization
        object.__setattr__(self, "intent_agent", intent_agent)
        object.__setattr__(self, "focus_agent", focus_agent)
        object.__setattr__(self, "executor_agent", executor_agent)
        object.__setattr__(self, "explainer_agent", explainer_agent)
        # AnomalyAgent is a utility class, not a BaseAgent sub-agent
        object.__setattr__(self, "anomaly_agent", anomaly_agent)

    # ---------------------------
    # Note: Clarification messaging belongs to FocusAgent. Removed local helper.
    # ---------------------------

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

        # Combine previous context with the current user message to reduce back-and-forth
        def _extract_text_from_ctx(_ctx: InvocationContext) -> str:
            try:
                return getattr(_ctx.user_content.parts[0], "text", "") or ""
            except Exception:
                return str(getattr(_ctx, "user_content", ""))

        current_msg = _extract_text_from_ctx(ctx).strip()
        prev_q_candidates = [
            session_state.get("question"),
            session_state.get("user_question"),
            session_state.get("original_question"),
            session_state.get("refined_question"),
        ]
        base_prev_q = next((q for q in prev_q_candidates if isinstance(q, str) and q.strip()), "")
        combined_q = current_msg
        MAX_COMBINED_LENGTH = 500
        if base_prev_q and current_msg and current_msg not in base_prev_q:
            tentative_combined = f"{base_prev_q.strip()}\n{current_msg.strip()}"
            if len(tentative_combined) <= MAX_COMBINED_LENGTH:
                combined_q = tentative_combined
                logger.debug(f"[Root] Using combined question for analysis: {combined_q}")
            else:
                logger.debug(f"[Root] Combined question too long ({len(tentative_combined)} chars), using current only")

        # Initialize debug trace
        debug_trace = []
        debug_trace.append("User Input Received")

        # ---------- 1) Intent Agent (first pass) ----------
        try:
            # Prefer running Intent with combined question if available
            ctx_for_a = ctx
            if combined_q and combined_q != current_msg:
                try:
                    ctx_for_a = InvocationContext(user_content=Part(text=combined_q), session=ctx.session)
                except Exception:
                    class _FakePart:
                        def __init__(self, text):
                            self.text = text

                    class _FakeContent:
                        def __init__(self, text):
                            self.parts = [_FakePart(text)]

                    ctx_for_a = type("FakeCtx", (), {"user_content": _FakeContent(combined_q), "session": ctx.session})()

            a1 = self.intent_agent.run(ctx_for_a)
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
            # Delegate clarification to FocusAgent
            debug_trace.append("Waiting for User Input (Intent) → Delegating to FocusAgent")
            try:
                fb = self.focus_agent.run(intent_state)
                fstate = fb.get("state", {}) or {}
                q = fstate.get("question_to_user") or (
                    "אפשר לחדד את הבקשה?" if any("א" <= ch <= "ת" for ch in (intent_state.get("question") or "")) else
                    "Can you clarify your question?"
                )
            except Exception:
                logger.exception("FocusAgent.run failed during clarification delegation")
                fstate = {}
                q = "Can you clarify your question?"

            state_with_trace = dict(intent_state)
            state_with_trace.update({
                "_debug_trace": debug_trace,
                "intent_state": intent_state,
                "focus_state": fstate,
            })
            return {
                "stage": "awaiting_user_input",
                "answer": q,
                "state": state_with_trace,
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
                state_with_trace = dict(focus_state)
                state_with_trace["_debug_trace"] = debug_trace
                state_with_trace["intent_state"] = final_intent
                state_with_trace["focus_state"] = focus_state
                return {
                    "stage": "awaiting_user_input",
                    "answer": q,
                    "state": state_with_trace,
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
                    state_with_trace = dict(intent2_state)
                    state_with_trace["_debug_trace"] = debug_trace
                    state_with_trace["intent_state"] = intent2_state
                    state_with_trace["focus_state"] = focus_state
                    return {
                        "stage": "awaiting_user_input",
                        "answer": msg,
                        "state": state_with_trace,
                    }
                final_intent = intent2_state
                should_run_executor = a2.get("should_run_executor", final_intent.get("valid", False))
            else:
                final_intent = intent_state

        # ---------- 2.5) Anomaly Agent (heuristic routing) ----------
        q_lower = (final_intent.get("question") or "").lower()
        is_anomaly = ("anomaly" in q_lower) or ("anomalies" in q_lower) or ("אנומל" in (final_intent.get("question") or ""))
        if is_anomaly:
            logger.debug("[Root] Routing to AnomalyAgent based on question content")
            debug_trace.append("Anomaly Agent: Handling anomalies request")
            try:
                anomaly_answer = self.anomaly_agent.answer(final_intent.get("question") or "")
                final_state = {
                    "_debug_trace": debug_trace,
                    "intent_state": final_intent,
                    "anomaly_answer": anomaly_answer,
                }
                return {
                    "stage": "done",
                    "answer": anomaly_answer,
                    "state": final_state,
                }
            except Exception:
                logger.exception("AnomalyAgent.answer failed; falling back to normal pipeline")
                # fall-through to executor

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
                state_with_trace = dict(final_intent)
                state_with_trace["_debug_trace"] = debug_trace
                state_with_trace["intent_state"] = final_intent
                return {
                    "stage": "awaiting_user_input",
                    "answer": ask,
                    "state": state_with_trace,
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
        
        # Build answer with chart/table if available
        description = explain_state.get("description", "") if isinstance(explain_state, dict) else str(explain_state)
        render_type = explain_state.get("render_type") if isinstance(explain_state, dict) else None
        
        # Format answer based on render type with validation
        if render_type == "chart" and explain_state.get("chart_image"):
            chart_img = explain_state.get("chart_image")
            # Validate chart_image is proper markdown or data URI
            if chart_img and (chart_img.startswith("![") or chart_img.startswith("data:image") or "<img" in chart_img):
                answer = f"{description}\n\n{chart_img}"
            else:
                logger.warning(f"[Root] Invalid chart_image format (length={len(chart_img) if chart_img else 0}), skipping")
                answer = description
        elif render_type == "table" and explain_state.get("table_markdown"):
            answer = f"{description}\n\n{explain_state.get('table_markdown')}"
        else:
            answer = description
        
        # Preserve full pipeline state
        final_state = dict(explain_state) if isinstance(explain_state, dict) else {"description": str(explain_state)}
        final_state["_debug_trace"] = debug_trace
        final_state["intent_state"] = final_intent
        final_state["executor_state"] = exec_state
        
        return {
            "stage": "done",
            "answer": answer,
            "state": final_state,
        }
    # -----------------------------------------------------
    # ADK Async Wrapper
    # -----------------------------------------------------
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        session_state = ctx.session.state.get("root_state", {})
        logger.debug(f"[Root] Async start: {getattr(ctx, 'user_content', None)}")
        result = self.run_pipeline(ctx, session_state)
        logger.debug(f"[Root] Final Output = stage={result.get('stage')} answer={result.get('answer')}")
        
        # Build final answer (debug trace stored in state but not displayed to user)
        answer = result.get("answer", "No answer returned.")
        
        # Update session
        actions = EventActions(
            state_delta={
                "root_state": result["state"],
                "stage": result["stage"],
            }
        )
        msg = Content(
            role="assistant",
            parts=[Part(text=answer)],
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
    anomaly_agent=AnomalyAgent(),
)
