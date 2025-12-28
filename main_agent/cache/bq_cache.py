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
import decimal
import re

from google.cloud import bigquery
import sqlparse

try:
    # prefer existing BQ client wrapper in the project
    from main_agent.bq import BQClient
except Exception:
    BQClient = None  # type: ignore


BQ_CACHE_TABLE_ID = os.getenv(
    "BQ_CACHE_TABLE_ID", "practicode-2025.cache.query_results"
)
BQ_CACHE_TTL_SECONDS = int(os.getenv("BQ_CACHE_TTL_SECONDS", "2592000"))  # 30 days
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


def _json_default(o):
    """Convert common non-JSON types to JSON-serializable values."""
    if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
        try:
            return o.isoformat()
        except Exception:
            return str(o)
    if isinstance(o, decimal.Decimal):
        try:
            if o % 1 == 0:
                return int(o)
        except Exception:
            pass
        return float(o)
    return str(o)


def _parse_iso_datetime(s: str) -> datetime.datetime | str:
    """Try to parse ISO 8601 datetime string; return original string if parse fails."""
    if not isinstance(s, str):
        return s
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', s):
        try:
            return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
        except Exception:
            return s
    return s


def _restore_datetimes(obj: Any) -> Any:
    """Recursively walk a deserialized JSON object and restore datetime objects from ISO strings."""
    if isinstance(obj, dict):
        return {k: _restore_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_restore_datetimes(item) for item in obj]
    elif isinstance(obj, str):
        return _parse_iso_datetime(obj)
    return obj


def _normalize_sql(sql: str) -> str:
    """Normalize SQL query to handle semantically equivalent queries."""
    if not sql:
        return ""
    try:
        formatted = sqlparse.format(
            sql,
            keyword_case='upper',
            strip_comments=True,
            reindent=False,
            use_space_around_operators=True
        )
        formatted = ' '.join(formatted.split()).strip()
        return formatted
    except Exception as e:
        logging.warning(f"SQL normalization failed, using simple normalization: {e}")
        return " ".join(sql.split()) if sql else ""


def _generate_cache_key(sql: str) -> str:
    """Generate a SHA256 cache key from the normalized SQL only."""
    key_input = _normalize_sql(sql)
    return hashlib.sha256(key_input.encode("utf-8")).hexdigest()


def get(sql: str) -> Optional[Dict[str, Any]]:
    """Return cached result_data (deserialized) for given SQL, or None on miss."""
    if not BQ_CACHE_ENABLED:
        return None

    query_hash = _generate_cache_key(sql)
    logging.debug(f"[Cache] Normalized SQL: {_normalize_sql(sql)[:80]}")
    logging.debug(f"[Cache] Query hash: {query_hash[:16]}...")

    q = f"""
    SELECT query_hash, result_data, cached_at, expires_at
    FROM `{BQ_CACHE_TABLE_ID}`
    WHERE query_hash = @hash
      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP())
    ORDER BY cached_at DESC
    LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("hash", "STRING", query_hash)]
    )
    try:
        rows = CLIENT.query(q, job_config=job_config).result()
        for row in rows:
            rd = getattr(row, "result_data", None)

            if isinstance(rd, str):
                try:
                    rd = json.loads(rd)
                    rd = _restore_datetimes(rd)
                except Exception:
                    logging.exception("Failed to deserialize result_data from JSON")
                    return None

            if isinstance(rd, dict):
                incoming = rd.get('incoming', {})
                if isinstance(incoming, dict) and incoming.get('status') == 'error':
                    logging.info(f"Cache HIT but result is ERROR - skipping cache: query_hash={query_hash[:16]}...")
                    return None

            logging.info(f"✓ Cache HIT: query_hash={query_hash[:16]}...")
            return rd
    except Exception:
        logging.exception("BigQuery cache get failed for key %s", query_hash)

    logging.debug(f"Cache MISS: query_hash={query_hash[:16]}...")
    return None  # ✅ THIS IS THE ONLY FIX


def set(sql: str, result: Any, ttl_seconds: Optional[int] = None) -> bool:
    """Store result in the cache table. `result` must be JSON-serializable."""
    if not BQ_CACHE_ENABLED:
        return False

    query_hash = _generate_cache_key(sql)
    ttl = ttl_seconds if ttl_seconds is not None else BQ_CACHE_TTL_SECONDS

    if isinstance(result, dict):
        incoming = result.get('incoming', {})
        if isinstance(incoming, dict) and incoming.get('status') == 'error':
            logging.info(f"Skipping cache write for error result: query_hash={query_hash[:16]}...")
            return False

    expires_at_iso = None
    if ttl:
        expires_at = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=ttl)
        expires_at_iso = expires_at.isoformat()

    try:
        result_json_str = json.dumps(result, default=_json_default, ensure_ascii=False)
    except Exception:
        logging.exception("Failed to serialize result to JSON")
        return False

    row = {
        "query_hash": query_hash,
        "original_query": _normalize_sql(sql),
        "result_data": result_json_str,
        "cached_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
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
        logging.info(f"✓ Cache insert successful: query_hash={query_hash[:16]}...")
        return True
    except Exception:
        logging.exception("Failed to insert cache row for key %s", query_hash)
        return False


def delete(sql: str) -> bool:
    if not BQ_CACHE_ENABLED:
        return False
    query_hash = _generate_cache_key(sql)
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
    if not BQ_CACHE_ENABLED:
        return 0
    q = f"""
    DELETE FROM `{BQ_CACHE_TABLE_ID}` WHERE expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP()
    """
    try:
        CLIENT.query(q).result()
        return 0
    except Exception:
        logging.exception("Failed to cleanup expired cache rows")
        return 0


__all__ = ["get", "set", "delete", "cleanup_expired"]
