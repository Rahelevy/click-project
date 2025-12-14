# BigQuery Cache Design & Integration

This document describes the BigQuery-based caching plan and how the root pipeline should use the cache after the intent agent produces an SQL query.

## Purpose

- Avoid re-executing identical heavy BigQuery queries repeatedly.
- Return cached results when available to speed up responses and reduce scanning of large tables.

## Overview / Where to integrate

- After the IntentAgent produces the final SQL, the RootAgent should:
  1. Generate a deterministic cache key from the normalized SQL.
  2. Check the BigQuery cache table for an entry under that key.
  3. If an unexpired cached result exists: deserialize and return it immediately (skip Executor).
  4. If not present: run the Executor, store the result in the BigQuery cache, then continue to the Explainer.

## Architecture

- Pipeline: IntentAgent → (normalize + hash SQL) → Cache Check → Executor (if miss) → Save to Cache → Explainer
- Cache medium: BigQuery table `practicode-2025.cache.query_results` (persistent, searchable). This avoids adding Redis and leverages existing GCP credentials.

## Key Scheme

- Normalize SQL: remove redundant whitespace, canonicalize spacing, optionally lower-case keywords (apply with care).
- Hash: compute SHA256 of the normalized SQL → `query_hash`.
- Key format (conceptual): `sha256(normalize(sql))`

Example pseudocode:
```
key_input = normalize(sql)
query_hash = sha256(key_input)
```

## Recommended Table Schema

- Table id: `practicode-2025.cache.query_results`
- Columns:
  - `query_hash` STRING NOT NULL
  - `original_query` STRING
  - `result_data` JSON
  - `cached_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
  - `ttl_seconds` INT64
  - `expires_at` TIMESTAMP
  - `hit_count` INT64 DEFAULT 1
  - `last_accessed` TIMESTAMP
- Notes: `PRIMARY KEY(query_hash) NOT ENFORCED` is appropriate for BigQuery. Use partitioning/clustering if needed for scale.

Create table SQL:
```
CREATE TABLE IF NOT EXISTS `practicode-2025.cache.query_results` (
  query_hash STRING NOT NULL,
  original_query STRING,
  result_data JSON,
  cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  ttl_seconds INT64,
  expires_at TIMESTAMP,
  hit_count INT64 DEFAULT 1,
  last_accessed TIMESTAMP,
  PRIMARY KEY(query_hash) NOT ENFORCED
);
```

## TTL and Invalidation

- Default TTL: 3600 seconds (1 hour) recommended; tune according to freshness requirements.
- Set `expires_at = cached_at + INTERVAL ttl_seconds SECOND` when inserting.
- Explicit invalidation: provide `delete`/`update` functions when upstream data changes.
- Cleanup: optional periodic `DELETE` for expired rows, or rely on queries filtering by `expires_at`.

## Serialization

- Store `result_data` as JSON using `json.dumps()`.
- For very large results consider compressing (gzip) and storing base64-encoded compressed content, or store a pointer to a Cloud Storage object.
- Prefer caching the executor `exec_state` (the dict returned by the ExecutorAgent) so Explainer can continue unchanged.

## Cache Module API (recommended)

- `get(sql: str) -> Optional[dict]`
  - Returns the deserialized executor state (or `None` on miss).
- `set(sql: str, result: dict, ttl_seconds: int|None = None) -> bool`
  - Saves the result and returns `True` on success.
- `delete(sql: str) -> bool` (optional)
- `cleanup_expired() -> int` (optional) — returns number of rows removed.

Note: The implementation currently uses the normalized SQL text only to compute cache keys.
`params` support was intentionally removed to match the current `IntentAgent` behavior
which returns fully inlined, deterministic SQL. If you later switch to parameterized
SQL (placeholders + separate params), update the cache module to include `params` in the key.

## Implementation Plan (phased)

### Phase 1 — BigQuery table (one-time)
- Create the `practicode-2025.cache.query_results` table using the SQL above.
- Add environment variables to `.env`:
```
BQ_CACHE_TABLE_ID=practicode-2025.cache.query_results
BQ_CACHE_TTL_SECONDS=3600
BQ_CACHE_ENABLED=true
```

### Phase 2 — BigQuery cache module
- Add `main_agent/cache/bq_cache.py` implementing the API above.
- Reuse the existing BigQuery client in `main_agent/bq.py` if available, or instantiate `bigquery.Client(project="practicode-2025", location="EU")`.
- Implement:
  - `_normalize_sql(sql: str) -> str`
  - `_generate_cache_key(sql: str) -> str` (SHA256)
  - `get(sql)` which returns `exec_state` or `None` (also increment `hit_count`)
  - `set(sql, result, ttl_seconds)` to insert/update the cache row
  - `_update_hit_count(query_hash, new_count)` internal helper
  - `cleanup_expired()` optional helper

Implementation notes:
- Use parameterized queries (`bigquery.QueryJobConfig`) for cache table operations.
- Only cache successful executor results (e.g., `status == "success"`).

### Phase 3 — RootAgent integration
- Modify `main_agent/agent.py` to import the cache module.
 - After the IntentAgent produces the final SQL and before calling the Executor:
  - `cached = bq_cache.get(sql)`
  - If `cached`: set `exec_state = cached` and skip the Executor.
  - Else: run Executor; on success call `bq_cache.set(sql, exec_state)`.


### Phase 4 — Tests & instrumentation
- Add unit tests under `main_agent/tests/test_bq_cache.py`:
  - Normalization/hash determinism
  - `get` returns `None` on miss
  - `set` then `get` returns stored data
  - TTL expiry behavior
- Manual verification:
  1. Run a heavy query once → cache miss (long runtime)
  2. Run the same query again → cache hit (fast)
  3. After TTL expiry → cache miss again

## Performance considerations

- Cache lookup is a small BigQuery query (negligible compared to scanning a 7+ TB table).
- If sub-100ms lookups at high QPS are required, consider a hybrid approach:
  - L1: Redis (hot in-memory cache)
  - L2: BigQuery (persistent searchable cache)
- For large datasets (e.g., 7 TB), BigQuery cache gives large savings for repeated heavy queries.

## Env configuration

Add to `main_agent/.env`:
```
BQ_CACHE_TABLE_ID=practicode-2025.cache.query_results
BQ_CACHE_TTL_SECONDS=3600
BQ_CACHE_ENABLED=true
```

## Next steps

1. Create BigQuery table using the SQL above.
2. Implement `main_agent/cache/bq_cache.py`.
3. Integrate the cache check into `main_agent/agent.py`.
4. Add tests and perform manual verification.

