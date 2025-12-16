# import logging
# logger = logging.getLogger("executor")
# logger.debug("🔥 ExecutorAgent loaded")

# from typing import Any, Dict, List
# from google.adk.agents import BaseAgent
# from google.cloud import bigquery

# from .schemas import AgentCOutput, IncomingResult


# def safe_dump(obj):
#     """Safe logging helper that avoids recursion problems."""
#     try:
#         if hasattr(obj, "model_dump"):
#             return obj.model_dump()
#         return obj
#     except Exception:
#         return str(obj)


# class ExecutorAgent(BaseAgent):
#     model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

#     def __repr__(self):
#         return f"ExecutorAgent(name={self.name})"

#     def __init__(self):
#         super().__init__(name="executor_agent")
#         self._bq_client: bigquery.Client | None = None

#     # -----------------------------------------------------
#     # BigQuery client (single shared client, fixed region)
#     # -----------------------------------------------------
#     def _get_bq_client(self) -> bigquery.Client:
#         """
#         Create a single shared BigQuery client for the agent,
#         pinned to the practicode-2025 project and EU location.
#         """
#         if self._bq_client is None:
#             try:
#                 self._bq_client = bigquery.Client(
#                     project="practicode-2025",
#                     location="EU",
#                 )
#                 logger.debug("[Executor] BigQuery client created with EU location")
#             except Exception as e:
#                 logger.error(f"[Executor] Could not create BigQuery client: {e}")
#                 raise

#         return self._bq_client

#     # -----------------------------------------------------
#     # Main Agent Logic
#     # -----------------------------------------------------
#     def run(self, state: Dict[str, Any]):
#         logger.debug(f"[Executor] START state = {safe_dump(state)}")

#         user_question = state.get("user_question", "")
#         sql = state.get("sql", "")

#         # ---------------------------------------------
#         # SQL Validation
#         # ---------------------------------------------
#         if not sql or "select" not in sql.lower():
#             output = AgentCOutput(
#                 user_question=user_question,
#                 incoming=IncomingResult(
#                     status="error",
#                     description="SQL validation failed: empty or invalid SQL.",
#                 ),
#                 db_result=None,
#             ).model_dump()

#             return {"state": output, "should_run_explainer": True}

#         logger.debug(f"[Executor] Running SQL:\n{sql}")

#         # ---------------------------------------------
#         # BigQuery Execution
#         # ---------------------------------------------
#         try:
#             client = self._get_bq_client()

#             # Submit query (explicit EU location for safety)
#             query_job = client.query(sql, location="EU")
#             logger.debug("[Executor] BigQuery job submitted... waiting for result.")

#             # Single blocking call – consume the entire iterator ONCE
#             rows_iter = query_job.result(timeout=120)
#             rows: List[dict] = [dict(row.items()) for row in rows_iter]

#             logger.debug(f"[Executor] BigQuery returned {len(rows)} rows")

#             # No rows ⇒ still success, just empty result
#             if len(rows) == 0:
#                 desc = "Query returned no rows."
#             else:
#                 desc = f"Returned {len(rows)} rows."

#             output = AgentCOutput(
#                 user_question=user_question,
#                 incoming=IncomingResult(
#                     status="success",
#                     description=desc,
#                 ),
#                 db_result=rows,
#             ).model_dump()

#             return {"state": output, "should_run_explainer": True}

#         except Exception as e:
#             logger.exception("[Executor] BigQuery execution error")

#             output = AgentCOutput(
#                 user_question=user_question,
#                 incoming=IncomingResult(
#                     status="error",
#                     description=f"Query execution failed: {e}",
#                 ),
#                 db_result=None,
#             ).model_dump()

#             return {"state": output, "should_run_explainer": True}


# executor_agent = ExecutorAgent()


import logging
logger = logging.getLogger("executor")
logger.debug("🔥 ExecutorAgent loaded")

from typing import Any, Dict, List
from google.adk.agents import BaseAgent
from google.cloud import bigquery

from .schemas import AgentCOutput, IncomingResult

# NEW: aggregation imports
from .aggregations import build_aggregated_sql, AggregationSpec


def safe_dump(obj):
    """Safe logging helper that avoids recursion problems."""
    try:
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return obj
    except Exception:
        return str(obj)


class ExecutorAgent(BaseAgent):
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __repr__(self):
        return f"ExecutorAgent(name={self.name})"

    def __init__(self):
        super().__init__(name="executor_agent")
        self._bq_client: bigquery.Client | None = None

    # -----------------------------------------------------
    # BigQuery client (single shared client, fixed region)
    # -----------------------------------------------------
    def _get_bq_client(self) -> bigquery.Client:
        """
        Create a single shared BigQuery client for the agent,
        pinned to the practicode-2025 project and EU location.
        """
        if self._bq_client is None:
            try:
                self._bq_client = bigquery.Client(
                    project="practicode-2025",
                    location="EU",
                )
                logger.debug("[Executor] BigQuery client created with EU location")
            except Exception as e:
                logger.error(f"[Executor] Could not create BigQuery client: {e}")
                raise

        return self._bq_client

    def _add_limit_if_missing(self, sql: str, limit: int = 50000) -> str:
        """
        Add a LIMIT clause to SQL if one doesn't already exist.
        This prevents BigQuery buffer allocation errors on large result sets.
        """
        sql_upper = sql.upper().strip()
        
        # Check if LIMIT already exists
        if "LIMIT" in sql_upper:
            return sql
        
        # Add LIMIT clause
        return f"{sql.rstrip(';')} LIMIT {limit}"

    # -----------------------------------------------------
    # Main Agent Logic
    # -----------------------------------------------------
    def run(self, state: Dict[str, Any]):
        logger.debug(f"[Executor] START state = {safe_dump(state)}")

        user_question = state.get("user_question", "")
        sql = state.get("sql", "")

        # ---------------------------------------------
        # SQL Validation (basic)
        # ---------------------------------------------
        if not sql or "select" not in sql.lower():
            output = AgentCOutput(
                user_question=user_question,
                incoming=IncomingResult(
                    status="error",
                    description="SQL validation failed: empty or invalid SQL.",
                ),
                db_result=None,
            ).model_dump()

            return {"state": output, "should_run_explainer": True}

        # ---------------------------------------------
        # NEW: Apply aggregation if spec exists
        # ---------------------------------------------
        agg_spec_dict = state.get("aggregation_spec")
        if agg_spec_dict:
            try:
                # Expecting dict like:
                # {"group_by": ["partner"], "metric_alias": "clicks", "top_n": 10, ...}
                spec = AggregationSpec(**agg_spec_dict)
                sql = build_aggregated_sql(sql, spec)
                logger.debug(f"[Executor] Aggregated SQL:\n{sql}")
            except Exception as e:
                output = AgentCOutput(
                    user_question=user_question,
                    incoming=IncomingResult(
                        status="error",
                        description=f"Aggregation failed: {e}",
                    ),
                    db_result=None,
                ).model_dump()

                return {"state": output, "should_run_explainer": True}

        # Add LIMIT to prevent buffer overflow at BigQuery level
        sql_with_limit = self._add_limit_if_missing(sql, limit=50000)
        logger.debug(f"[Executor] Running SQL:\n{sql_with_limit}")

        # ---------------------------------------------
        # BigQuery Execution
        # ---------------------------------------------
        try:
            client = self._get_bq_client()

            # Submit query (explicit EU location for safety)
            query_job = client.query(sql_with_limit, location="EU")
            logger.debug("[Executor] BigQuery job submitted... waiting for result.")

            # Set a reasonable row limit to prevent memory overflow
            MAX_ROWS = 10000
            rows_iter = query_job.result(timeout=600, max_results=MAX_ROWS)
            
            # Load rows in batches to avoid memory issues
            rows: List[dict] = []
            row_count = 0
            truncated = False
            
            try:
                for row in rows_iter:
                    rows.append(dict(row.items()))
                    row_count += 1
                    if row_count >= MAX_ROWS:
                        truncated = True
                        logger.warning(f"[Executor] Result truncated at {MAX_ROWS} rows")
                        break
            except Exception as iter_error:
                logger.error(f"[Executor] Error during row iteration: {iter_error}")
                # If we have some rows, continue with what we have
                if rows:
                    logger.info(f"[Executor] Continuing with {len(rows)} rows collected before error")
                    truncated = True
                else:
                    raise

            logger.debug(f"[Executor] BigQuery returned {len(rows)} rows")
            if rows:
                logger.debug(f"[Executor] First row sample: {rows[0]}")

            # No rows ⇒ still success, just empty result
            if len(rows) == 0:
                desc = "Query returned no rows."
            elif truncated:
                desc = f"Returned {len(rows)} rows (result limited to first {MAX_ROWS} rows due to size)."
            else:
                desc = f"Returned {len(rows)} rows."

            output = AgentCOutput(
                user_question=user_question,
                incoming=IncomingResult(
                    status="success",
                    description=desc,
                ),
                db_result=rows,
            ).model_dump()

            return {"state": output, "should_run_explainer": True}

        except Exception as e:
            logger.exception("[Executor] BigQuery execution error")

            output = AgentCOutput(
                user_question=user_question,
                incoming=IncomingResult(
                    status="error",
                    description=f"Query execution failed: {e}",
                ),
                db_result=None,
            ).model_dump()

            return {"state": output, "should_run_explainer": True}


executor_agent = ExecutorAgent()
