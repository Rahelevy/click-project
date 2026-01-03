import logging
logger = logging.getLogger("executor")
logger.debug("🔥 ExecutorAgent loaded")

from typing import Any, Dict, List
from datetime import datetime, date, time
from google.adk.agents import BaseAgent
from google.cloud import bigquery
import os

from .schemas import AgentCOutput, IncomingResult

# NEW: aggregation imports
from .aggregations import build_aggregated_sql, AggregationSpec

# ============================================
# RESULT SIZE CONFIGURATION
# ============================================
# Controls maximum rows returned and LIMIT clause in BigQuery
# Adjust these based on your UI/memory constraints
SQL_LIMIT_CLAUSE = int(os.getenv("SQL_LIMIT_CLAUSE", "500000"))  # LIMIT clause in SQL to prevent BigQuery buffer issues
MAX_ROWS_RETURNED = int(os.getenv("MAX_ROWS_RETURNED", "100000"))  # Maximum rows returned to frontend
MAX_ROWS_AGGREGATED = int(os.getenv("MAX_ROWS_AGGREGATED", "50000"))  # Max rows for aggregated queries

logger.info(f"[ExecutorAgent Config] SQL_LIMIT_CLAUSE={SQL_LIMIT_CLAUSE}, MAX_ROWS_RETURNED={MAX_ROWS_RETURNED}, MAX_ROWS_AGGREGATED={MAX_ROWS_AGGREGATED}")


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

    @staticmethod
    def _coerce_scalar(val):
        """Convert non-JSON-serializable scalars (datetime/date/time) to strings."""
        if isinstance(val, datetime):
            return val.isoformat()
        if isinstance(val, date):
            return val.isoformat()
        if isinstance(val, time):
            return val.isoformat()
        return val

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

    def _add_limit_if_missing(self, sql: str, limit: int = None) -> str:
        """
        Add a LIMIT clause to SQL if one doesn't already exist.
        This prevents BigQuery buffer allocation errors on large result sets.
        Uses SQL_LIMIT_CLAUSE by default, or the specified limit.
        """
        sql_upper = sql.upper().strip()
        
        # Check if LIMIT already exists
        if "LIMIT" in sql_upper:
            return sql
        
        if limit is None:
            limit = SQL_LIMIT_CLAUSE
        
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
        # SQL Validation
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
                logger.info(f"[Executor] Applying aggregation spec: {agg_spec_dict}")
                logger.info(f"[Executor] Base SQL before aggregation:\n{sql}")
                spec = AggregationSpec(**agg_spec_dict)
                sql = build_aggregated_sql(sql, spec)
                logger.info(f"[Executor] Aggregated SQL:\n{sql}")
            except Exception as e:
                logger.exception(f"[Executor] Aggregation failed with exception: {e}")
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
        sql_with_limit = self._add_limit_if_missing(sql)
        logger.info(f"[Executor] Running SQL:\n{sql_with_limit}")

        # Determine appropriate row limit based on whether aggregation was applied
        is_aggregated = agg_spec_dict is not None
        max_rows = MAX_ROWS_AGGREGATED if is_aggregated else MAX_ROWS_RETURNED
        logger.info(f"[Executor] Using max_rows={max_rows} (aggregated={is_aggregated})")

        # ---------------------------------------------
        # BigQuery Execution
        # ---------------------------------------------
        try:
            client = self._get_bq_client()
            query_job = client.query(sql_with_limit, location="EU")
            logger.debug("[Executor] BigQuery job submitted... waiting for result.")
            # Set a reasonable row limit to prevent memory overflow
            rows_iter = query_job.result(timeout=600, max_results=max_rows)
            
            # Load rows in batches to avoid memory issues
            rows: List[dict] = []
            row_count = 0
            truncated = False
            
            try:
                for row in rows_iter:
                    coerced = {k: self._coerce_scalar(v) for k, v in dict(row.items()).items()}
                    rows.append(coerced)
                    row_count += 1
                    if row_count >= max_rows:
                        truncated = True
                        logger.warning(f"[Executor] Result truncated at {max_rows} rows")
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
            # if rows:
            #     logger.debug(f"[Executor] First row sample: {rows[0]}")

            # No rows ⇒ still success, just empty result
            if len(rows) == 0:
                desc = "Query returned no rows."
            elif truncated:
                desc = f"Returned {len(rows)} rows (result limited to first {max_rows} rows due to size)."
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
