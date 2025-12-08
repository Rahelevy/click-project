import logging
logger = logging.getLogger("executor")
logger.debug("🔥 ExecutorAgent loaded")

from typing import Any, Dict
from google.adk.agents import BaseAgent
from google.cloud import bigquery

from .schemas import AgentCOutput, IncomingResult


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
        self._bq_client = None

    # -----------------------------------------------------
    # BigQuery client (PATCHED — stable + fixed region)
    # -----------------------------------------------------
    def _get_bq_client(self):
        """
        BigQuery jobs hang indefinitely if:
        - job creation uses default region (US)
        - polling is done in EU
        or vice versa.

        Fix:
        Force project + EU region.
        Create only ONE client shared across all async loops.
        """
        if self._bq_client is None:
            try:
                self._bq_client = bigquery.Client(
                    project="practicode-2025",
                    location="EU"   # <<< CRITICAL FIX
                )
                logger.debug("[Executor] BigQuery client created with EU location")
            except Exception as e:
                logger.error(f"[Executor] Could not create BigQuery client: {e}")
                raise

        return self._bq_client

    # -----------------------------------------------------
    # Main Agent Logic
    # -----------------------------------------------------
    def run(self, state: Dict[str, Any]):
        logger.debug(f"[Executor] START state = {safe_dump(state)}")

        user_question = state.get("user_question", "")
        sql = state.get("sql", "")

        # ---------------------------------------------
        # SQL Validation
        # ---------------------------------------------
        if not sql or "select" not in sql.lower():
            output = AgentCOutput(
                user_question=user_question,
                incoming=IncomingResult(
                    status="error",
                    description="SQL validation failed: empty or invalid SQL."
                ),
                db_result=None
            ).model_dump()

            return {"state": output, "should_run_explainer": True}

        logger.debug(f"[Executor] Running SQL:\n{sql}")

        # ---------------------------------------------
        # BigQuery Execution (PATCHED)
        # ---------------------------------------------
        try:
            client = self._get_bq_client()

            # Force EU location to avoid hanging jobs
            query_job = client.query(sql, location="EU")
            logger.debug("[Executor] BigQuery job submitted... waiting for result.")

            # BLOCK until complete — SAFE NOW because region is correct
            rows_iter = query_job.result()  # <-- THIS NO LONGER HANGS
            rows = list(rows_iter)

            logger.debug(f"[Executor] BigQuery returned {len(rows)} rows")

            # ---------------------------------------------
            # No rows returned
            # ---------------------------------------------
            if len(rows) == 0:
                output = AgentCOutput(
                    user_question=user_question,
                    incoming=IncomingResult(
                        status="success",
                        description="Query returned no rows."
                    ),
                    db_result=[]
                ).model_dump()

                return {"state": output, "should_run_explainer": True}

            # ---------------------------------------------
            # Convert rows → dicts
            # ---------------------------------------------
            row_dicts = [dict(r.items()) for r in rows]

            output = AgentCOutput(
                user_question=user_question,
                incoming=IncomingResult(
                    status="success",
                    description=f"Returned {len(rows)} rows."
                ),
                db_result=row_dicts
            ).model_dump()

            return {"state": output, "should_run_explainer": True}

        except Exception as e:
            logger.exception("[Executor] BigQuery execution error")

            output = AgentCOutput(
                user_question=user_question,
                incoming=IncomingResult(
                    status="error",
                    description=f"Query execution failed: {e}"
                ),
                db_result=None
            ).model_dump()

            return {"state": output, "should_run_explainer": True}


executor_agent = ExecutorAgent()
