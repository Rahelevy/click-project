"""BigQuery-backed cache module.

Implements a small API: get, set, delete, cleanup_expired using the
`practicode-2025.cache.query_results` table by default (configurable via
`BQ_CACHE_TABLE_ID` env var).

This module prefers the existing `main_agent.bq.BQClient` when available.
"""
from __future__ import annotations

import os
import json
import hashlib
import logging
from typing import Any, Dict, Optional
import datetime

from google.cloud import bigquery

try:
    # prefer existing BQ client wrapper in the project
    from main_agent.bq import BQClient
except Exception:
    BQClient = None  # type: ignore


BQ_CACHE_TABLE_ID = os.getenv(
    "BQ_CACHE_TABLE_ID", "practicode-2025.cache.query_results"
)
BQ_CACHE_TTL_SECONDS = int(os.getenv("BQ_CACHE_TTL_SECONDS", "3600"))
BQ_CACHE_ENABLED = os.getenv("BQ_CACHE_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)


def _get_client() -> bigquery.Client:
    if BQClient is not None:
        try:
            return BQClient().bq_client
        except Exception:
            logging.warning("Failed to instantiate project BQClient, falling back to default bigquery.Client")
    return bigquery.Client()


CLIENT = _get_client()


def _normalize_sql(sql: str) -> str:
    # simple normalization: collapse whitespace and trim
    return " ".join(sql.split()) if sql else ""


def _generate_cache_key(sql: str, params: Optional[Dict[str, Any]] = None) -> str:
    key_input = _normalize_sql(sql) + "|" + json.dumps(params or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(key_input.encode("utf-8")).hexdigest()


def _update_hit_count(query_hash: str) -> None:
    try:
        q = f"""
        UPDATE `{BQ_CACHE_TABLE_ID}`
        SET hit_count = IFNULL(hit_count, 0) + 1,
            last_accessed = CURRENT_TIMESTAMP()
        WHERE query_hash = @hash
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("hash", "STRING", query_hash)]
        )
        CLIENT.query(q, job_config=job_config).result()
    except Exception:
        logging.exception("Failed to update hit_count for cache key %s", query_hash)


def get(sql: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Return cached result_data (deserialized) for given SQL+params, or None on miss.

    This only returns rows that are not expired (expires_at is null or in the future).
    """
    if not BQ_CACHE_ENABLED:
        return None

    query_hash = _generate_cache_key(sql, params)
    q = f"""
    SELECT query_hash, original_query, result_data, cached_at, ttl_seconds, expires_at, hit_count, last_accessed
    FROM `{BQ_CACHE_TABLE_ID}`
    WHERE query_hash = @hash
      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP())
    LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("hash", "STRING", query_hash)]
    )
    try:
        rows = CLIENT.query(q, job_config=job_config).result()
        for row in rows:
            rd = getattr(row, "result_data", None)
            # BigQuery JSON column may come back as native Python structures
            if isinstance(rd, str):
                try:
                    rd = json.loads(rd)
                except Exception:
                    # leave as-is if not JSON
                    pass

            # asynchronously update hit_count (best-effort)
            try:
                _update_hit_count(query_hash)
            except Exception:
                pass

            return rd
    except Exception:
        logging.exception("BigQuery cache get failed for key %s", query_hash)
    return None


def set(sql: str, result: Any, params: Optional[Dict[str, Any]] = None, ttl_seconds: Optional[int] = None) -> bool:
    """Store result in the cache table. `result` must be JSON-serializable.

    Uses `insert_rows_json` which will insert a row. If a row with the same
    `query_hash` already exists, this will create a duplicate unless the
    table has constraints. For idempotency, users can run an UPSERT via
    a MERGE query instead (not implemented here).
    """
    if not BQ_CACHE_ENABLED:
        return False

    query_hash = _generate_cache_key(sql, params)
    ttl = ttl_seconds if ttl_seconds is not None else BQ_CACHE_TTL_SECONDS

    expires_at_iso = None
    if ttl:
        expires_at = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=ttl)
        expires_at_iso = expires_at.isoformat()

    row = {
        "query_hash": query_hash,
        "original_query": _normalize_sql(sql),
        # BigQuery client will convert Python dict/list to JSON for a JSON column
        "result_data": result,
        "ttl_seconds": ttl,
        "expires_at": expires_at_iso,
        "hit_count": 1,
        "last_accessed": None,
    }

    try:
        errors = CLIENT.insert_rows_json(BQ_CACHE_TABLE_ID, [row])
        if errors:
            logging.error("Errors inserting cache row: %s", errors)
            return False
        return True
    except Exception:
        logging.exception("Failed to insert cache row for key %s", query_hash)
        return False


def delete(sql: str, params: Optional[Dict[str, Any]] = None) -> bool:
    if not BQ_CACHE_ENABLED:
        return False
    query_hash = _generate_cache_key(sql, params)
    q = f"""
    DELETE FROM `{BQ_CACHE_TABLE_ID}` WHERE query_hash = @hash
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("hash", "STRING", query_hash)]
    )
    try:
        CLIENT.query(q, job_config=job_config).result()
        return True
    except Exception:
        logging.exception("Failed to delete cache row for key %s", query_hash)
        return False


def cleanup_expired() -> int:
    """Remove expired rows from the cache table. Returns number of deleted rows
    (best-effort; BigQuery doesn't return affected-rows count reliably from client).
    """
    if not BQ_CACHE_ENABLED:
        return 0
    q = f"""
    DELETE FROM `{BQ_CACHE_TABLE_ID}` WHERE expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP()
    """
    try:
        CLIENT.query(q).result()
        # BigQuery python client doesn't return row count for DELETE in a simple way
        return 0
    except Exception:
        logging.exception("Failed to cleanup expired cache rows")
        return 0


__all__ = ["get", "set", "delete", "cleanup_expired"]
