# import json
# from typing import Any, AsyncGenerator

# from google.adk.agents import BaseAgent
# from google.adk.events import Event, Content, Part


# # Sub-agents
# from main_agent.sub_agents.a_intent_agent.agent import intent_agent
# from main_agent.sub_agents.b_focus_agent.agent import focus_agent
# from main_agent.sub_agents.c_executor_agent.agent import executor_agent
# from main_agent.sub_agents.d_explanation_agent.agent import explainer_agent

# # Schemas
# from main_agent.sub_agents.a_intent_agent.schemas import AgentAOutput
# from main_agent.sub_agents.b_focus_agent.schemas import AgentBOutput
# from main_agent.sub_agents.c_executor_agent.schemas import AgentCOutput
# from main_agent.sub_agents.d_explanation_agent.schemas import ExplanationOutput


# # ------------------------------------------------------------
# # UTILITIES
# # ------------------------------------------------------------
# def parse_event_output(event, schema):
#     """Extract JSON string from LLM Event and parse it with schema."""
#     raw = event.content.parts[0].text
#     return schema.model_validate_json(raw)


# def make_event(output_obj):
#     """
#     Builds an ADK Event object manually (compatible with ADK 1.19).
#     """
#     json_str = output_obj.model_dump_json()
#     return Event(
#         content=Content(parts=[Part(text=json_str)]),
#         model_output=output_obj
#     )


# # ------------------------------------------------------------
# # ROOT AGENT
# # ------------------------------------------------------------
# class RootAgent(BaseAgent):

#     intent_agent: Any = None
#     focus_agent: Any = None
#     executor_agent: Any = None
#     explainer_agent: Any = None

#     def __init__(self, intent_agent, focus_agent, executor_agent, explainer_agent, **kwargs):
#         super().__init__(**kwargs)
#         self.intent_agent = intent_agent
#         self.focus_agent = focus_agent
#         self.executor_agent = executor_agent
#         self.explainer_agent = explainer_agent


#     async def _run_async_impl(self, state) -> AsyncGenerator:

#         # ---------------------------
#         # STEP 1: INTENT AGENT (A)
#         # ---------------------------
#         intent_raw = None
#         async for e in self.intent_agent.run_async(state):
#             intent_raw = e

#         intent_out = parse_event_output(intent_raw, AgentAOutput)

#         if intent_out.awaiting_user_input:
#             yield make_event(intent_out)
#             return

#         # ---------------------------
#         # LOOP A <-> B
#         # ---------------------------
#         while not intent_out.valid:

#             focus_input = {
#                 "original_question": intent_out.question,
#                 "reason": intent_out.reason or "Missing filters"
#             }

#             focus_raw = None
#             async for e in self.focus_agent.run_async(focus_input):
#                 focus_raw = e

#             focus_out = parse_event_output(focus_raw, AgentBOutput)

#             if focus_out.awaiting_user_input:
#                 yield make_event(focus_out)
#                 return

#             if focus_out.refined_question:
#                 intent_raw = None
#                 async for e in self.intent_agent.run_async(
#                     {"question": focus_out.refined_question}
#                 ):
#                     intent_raw = e

#                 intent_out = parse_event_output(intent_raw, AgentAOutput)

#             else:
#                 break

#         # ---------------------------
#         # STEP 2: SQL EXECUTION (C)
#         # ---------------------------
#         exec_input = {
#             "user_question": intent_out.question,
#             "sql": intent_out.sql
#         }

#         exec_raw = None
#         async for e in self.executor_agent.run_async(exec_input):
#             exec_raw = e

#         exec_out = parse_event_output(exec_raw, AgentCOutput)

#         # ---------------------------
#         # STEP 3: EXPLANATION (D)
#         # ---------------------------
#         expl_input = {
#             "user_question": exec_out.user_question,
#             "db_result": exec_out.db_result
#         }

#         expl_raw = None
#         async for e in self.explainer_agent.run_async(expl_input):
#             expl_raw = e

#         final_out = parse_event_output(expl_raw, ExplanationOutput)

#         yield make_event(final_out)



# root_agent = RootAgent(
#     intent_agent,
#     focus_agent,
#     executor_agent,
#     explainer_agent,
#     name="root_agent"
# )
