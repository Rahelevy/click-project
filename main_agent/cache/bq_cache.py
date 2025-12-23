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
        # preserve integer-y decimals as int when possible
        try:
            if o % 1 == 0:
                return int(o)
        except Exception:
            pass
        return float(o)
    # fallback: stringify unknown types
    return str(o)


def _parse_iso_datetime(s: str) -> datetime.datetime | str:
    """Try to parse ISO 8601 datetime string; return original string if parse fails."""
    if not isinstance(s, str):
        return s
    # Simple ISO 8601 pattern: YYYY-MM-DDTHH:MM:SS[.ffffff][+HH:MM|Z]
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', s):
        try:
            # Python 3.7+ supports fromisoformat
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
    """Normalize SQL query to handle semantically equivalent queries.
    
    This function:
    1. Formats SQL consistently (keywords uppercase, consistent spacing)
    2. Normalizes quotes (standardizes to single quotes)
    3. Sorts WHERE clause conditions alphabetically for consistent ordering
    
    Returns:
        Normalized SQL string for cache key generation
    """
    if not sql:
        return ""
    
    try:
        # Step 1: Format SQL with consistent formatting using sqlparse
        formatted = sqlparse.format(
            sql,
            keyword_case='upper',
            strip_comments=True,
            reindent=False,
            use_space_around_operators=True
        )
        
        # Step 2: Normalize quotes - replace double quotes with single quotes for string literals
        # Match strings enclosed in double quotes (not backticks)
        def normalize_quotes(match):
            content = match.group(1)
            # Escape any single quotes that might be inside
            content = content.replace("'", "''")
            return f"'{content}'"
        
        # Replace "string" with 'string' but preserve `identifiers`
        formatted = re.sub(r'"([^"]*)"', normalize_quotes, formatted)
        
        # Step 3: Sort WHERE clause conditions alphabetically
        # Use regex to find WHERE clause content and the following keyword
        def sort_where_conditions(match):
            where_keyword = match.group(1)  # WHERE (with proper case)
            where_content = match.group(2)  # Everything between WHERE and next keyword
            following_keyword = match.group(3)  # The following keyword (e.g., LIMIT, GROUP BY)
            
            where_clause = where_content.strip()
            
            # Split by AND (case-insensitive) to get individual conditions
            conditions = re.split(r'\s+AND\s+', where_clause, flags=re.IGNORECASE)
            
            if len(conditions) > 1:
                # Normalize each condition: strip whitespace and collapse internal spaces
                normalized_conditions = []
                for cond in conditions:
                    normalized_cond = ' '.join(cond.strip().split())
                    normalized_conditions.append(normalized_cond)
                
                # Sort conditions alphabetically
                normalized_conditions.sort()
                
                # Reconstruct with sorted conditions
                new_where_clause = ' AND '.join(normalized_conditions)
                return f" {where_keyword} {new_where_clause} {following_keyword}"
            else:
                # If no AND conditions, return as-is
                return match.group(0)
        
        # Pattern: Find WHERE clause followed by next major keyword or end of string
        # Group 1: WHERE keyword
        # Group 2: Conditions between WHERE and next keyword
        # Group 3: Next keyword or empty if end of string
        pattern = r'(\bWHERE\b)\s+(.*?)\s+(\b(?:GROUP|ORDER|HAVING|LIMIT|OFFSET|UNION|INTERSECT|EXCEPT)\b|$)'
        formatted = re.sub(pattern, sort_where_conditions, formatted, flags=re.IGNORECASE | re.DOTALL)
        
        # Step 4: Final cleanup - collapse multiple spaces into one and trim
        formatted = ' '.join(formatted.split()).strip()
        
        return formatted
        
    except Exception as e:
        # If normalization fails, fall back to simple whitespace normalization
        logging.warning(f"SQL normalization failed, using simple normalization: {e}")
        return " ".join(sql.split()) if sql else ""


def _generate_cache_key(sql: str) -> str:
    """Generate a SHA256 cache key from the normalized SQL only.
    """
    key_input = _normalize_sql(sql)
    return hashlib.sha256(key_input.encode("utf-8")).hexdigest()


def _update_hit_count(query_hash: str) -> None:
    try:
        # Use MERGE instead of UPDATE to avoid "rows in the streaming buffer" errors
        # This approach is safe even if the row is very recently inserted
        q = f"""
        MERGE INTO `{BQ_CACHE_TABLE_ID}` t
        USING (SELECT @hash AS query_hash) s
        ON t.query_hash = s.query_hash
        WHEN MATCHED THEN
          UPDATE SET 
            hit_count = IFNULL(hit_count, 0) + 1,
            last_accessed = CURRENT_TIMESTAMP()
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("hash", "STRING", query_hash)]
        )
        CLIENT.query(q, job_config=job_config).result()
    except Exception:
        # Log but don't fail - hit count is not critical for cache correctness
        logging.debug("Could not update hit_count for cache key %s (non-critical)", query_hash)


def get(sql: str) -> Optional[Dict[str, Any]]:
    """Return cached result_data (deserialized) for given SQL+params, or None on miss.

    This only returns rows that are not expired (expires_at is null or in the future).
    """
    if not BQ_CACHE_ENABLED:
        return None

    query_hash = _generate_cache_key(sql)
    logging.debug(f"[Cache] Normalized SQL: {_normalize_sql(sql)[:80]}")
    logging.debug(f"[Cache] Query hash: {query_hash[:16]}...")
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
            # BigQuery JSON column returns as string, deserialize it
            if isinstance(rd, str):
                try:
                    rd = json.loads(rd)
                    # Restore datetime objects from ISO strings
                    rd = _restore_datetimes(rd)
                except Exception:
                    logging.exception("Failed to deserialize result_data from JSON")
                    return None
            
            # Skip cached errors - always re-execute failed queries
            if isinstance(rd, dict):
                incoming = rd.get('incoming', {})
                if isinstance(incoming, dict) and incoming.get('status') == 'error':
                    logging.info(f"Cache HIT but result is ERROR - skipping cache: query_hash={query_hash[:16]}...")
                    return None
            
            # asynchronously update hit_count (best-effort)
            try:
                _update_hit_count(query_hash)
            except Exception:
                pass

            logging.info(f"✓ Cache HIT: query_hash={query_hash[:16]}...")
            return rd
    except Exception:
        logging.exception("BigQuery cache get failed for key %s", query_hash)
    logging.debug(f"Cache MISS: query_hash={query_hash[:16]}...")


def set(sql: str, result: Any, ttl_seconds: Optional[int] = None) -> bool:
    """Store result in the cache table. `result` must be JSON-serializable.

    Uses `insert_rows_json` which will insert a row. If a row with the same
    `query_hash` already exists, this will create a duplicate unless the
    table has constraints. For idempotency, users can run an UPSERT via
    a MERGE query instead (not implemented here).
    """
    if not BQ_CACHE_ENABLED:
        return False

    query_hash = _generate_cache_key(sql)
    ttl = ttl_seconds if ttl_seconds is not None else BQ_CACHE_TTL_SECONDS

    expires_at_iso = None
    # Skip caching error results - they shouldn't be cached
    if isinstance(result, dict):
        incoming = result.get('incoming', {})
        if isinstance(incoming, dict) and incoming.get('status') == 'error':
            logging.info(f"Skipping cache write for error result: query_hash={query_hash[:16]}...")
            return False

    if ttl:
        expires_at = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=ttl)
        expires_at_iso = expires_at.isoformat()

    # Serialize result to JSON string to ensure proper handling by BigQuery JSON column
    try:
        result_json_str = json.dumps(result, default=_json_default, ensure_ascii=False)
    except Exception:
        logging.exception("Failed to serialize result to JSON")
        return False

    row = {
        "query_hash": query_hash,
        "original_query": _normalize_sql(sql),
        # Store as JSON string for JSON column type
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
