-- ============================================================
-- BigQuery Table Setup: encoded_clicks
-- Partition Strategy: DAY (DATE-based)
-- Data Volume: >100GB/day
-- ============================================================

-- DROP TABLE IF EXISTS `practicode-2025.clicks_data_prac.encoded_clicks`;

-- ============================================================
-- CLUSTERING OPTIONS - Choose ONE based on your use case
-- ============================================================

-- ============================================================
-- OPTION 1: BALANCED (RECOMMENDED)
-- Use when: Queries ask about media_source, app_id, partner, retargeting
-- Best for: General analysis, mixed query patterns
-- ============================================================
CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
  event_time TIMESTAMP NOT NULL,
  hr INT64,
  media_source STRING,
  app_id STRING,
  partner STRING,
  site_id STRING,
  engagement_type STRING,
  is_retargeting BOOLEAN,
  is_engaged_view BOOLEAN,
  total_events INT64
)
PARTITION BY DATE(event_time)
CLUSTER BY media_source, app_id, partner, is_retargeting
OPTIONS(
  require_partition_filter = TRUE,
  partition_expiration_days = 365,
  description = "Click events dataset - BALANCED clustering"
);

-- ============================================================
-- OPTION 2: MEDIA_SOURCE PRIORITY
-- Use when: Most queries ask "Which media_source...?" first
-- Best for: Traffic source analysis, top sources
-- ============================================================
-- CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
--   event_time TIMESTAMP NOT NULL,
--   hr INT64,
--   media_source STRING,
--   app_id STRING,
--   partner STRING,
--   site_id STRING,
--   engagement_type STRING,
--   is_retargeting BOOLEAN,
--   is_engaged_view BOOLEAN,
--   total_events INT64
-- )
-- PARTITION BY DATE(event_time)
-- CLUSTER BY media_source, app_id, is_retargeting, partner
-- OPTIONS(
--   require_partition_filter = TRUE,
--   partition_expiration_days = 365,
--   description = "Click events dataset - MEDIA_SOURCE priority clustering"
-- );

-- ============================================================
-- OPTION 3: APP PRIORITY
-- Use when: Most queries ask "Which app...?" first
-- Best for: App performance analysis, per-app breakdowns
-- ============================================================
-- CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
--   event_time TIMESTAMP NOT NULL,
--   hr INT64,
--   media_source STRING,
--   app_id STRING,
--   partner STRING,
--   site_id STRING,
--   engagement_type STRING,
--   is_retargeting BOOLEAN,
--   is_engaged_view BOOLEAN,
--   total_events INT64
-- )
-- PARTITION BY DATE(event_time)
-- CLUSTER BY app_id, media_source, partner, is_retargeting
-- OPTIONS(
--   require_partition_filter = TRUE,
--   partition_expiration_days = 365,
--   description = "Click events dataset - APP priority clustering"
-- );

-- ============================================================
-- OPTION 4: PARTNER PRIORITY
-- Use when: Most queries ask "Which partner...?" first
-- Best for: Partner performance, agency analysis
-- ============================================================
-- CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
--   event_time TIMESTAMP NOT NULL,
--   hr INT64,
--   media_source STRING,
--   app_id STRING,
--   partner STRING,
--   site_id STRING,
--   engagement_type STRING,
--   is_retargeting BOOLEAN,
--   is_engaged_view BOOLEAN,
--   total_events INT64
-- )
-- PARTITION BY DATE(event_time)
-- CLUSTER BY partner, app_id, media_source, is_retargeting
-- OPTIONS(
--   require_partition_filter = TRUE,
--   partition_expiration_days = 365,
--   description = "Click events dataset - PARTNER priority clustering"
-- );

-- ============================================================
-- OPTION 5: RETARGETING FIRST
-- Use when: Most queries filter by is_retargeting first
-- Best for: Retargeting vs UA analysis
-- ============================================================
-- CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
--   event_time TIMESTAMP NOT NULL,
--   hr INT64,
--   media_source STRING,
--   app_id STRING,
--   partner STRING,
--   site_id STRING,
--   engagement_type STRING,
--   is_retargeting BOOLEAN,
--   is_engaged_view BOOLEAN,
--   total_events INT64
-- )
-- PARTITION BY DATE(event_time)
-- CLUSTER BY is_retargeting, media_source, app_id, partner
-- OPTIONS(
--   require_partition_filter = TRUE,
--   partition_expiration_days = 365,
--   description = "Click events dataset - RETARGETING priority clustering"
-- );

-- ============================================================
-- OPTION 6: MINIMAL (2 COLUMNS ONLY)
-- Use when: Queries are mostly generic or time-based
-- Best for: Simplicity, less metadata overhead
-- ============================================================
-- CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
--   event_time TIMESTAMP NOT NULL,
--   hr INT64,
--   media_source STRING,
--   app_id STRING,
--   partner STRING,
--   site_id STRING,
--   engagement_type STRING,
--   is_retargeting BOOLEAN,
--   is_engaged_view BOOLEAN,
--   total_events INT64
-- )
-- PARTITION BY DATE(event_time)
-- CLUSTER BY media_source, app_id
-- OPTIONS(
--   require_partition_filter = TRUE,
--   partition_expiration_days = 365,
--   description = "Click events dataset - MINIMAL clustering (2 columns)"
-- );

-- ============================================================
-- OPTION 7: MAX (5+ COLUMNS)
-- Use when: Queries filter on many dimensions
-- Best for: Complex multi-dimensional analysis
-- ============================================================
-- CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
--   event_time TIMESTAMP NOT NULL,
--   hr INT64,
--   media_source STRING,
--   app_id STRING,
--   partner STRING,
--   site_id STRING,
--   engagement_type STRING,
--   is_retargeting BOOLEAN,
--   is_engaged_view BOOLEAN,
--   total_events INT64
-- )
-- PARTITION BY DATE(event_time)
-- CLUSTER BY media_source, app_id, partner, is_retargeting, site_id
-- OPTIONS(
--   require_partition_filter = TRUE,
--   partition_expiration_days = 365,
--   description = "Click events dataset - MAX clustering (5 columns)"
-- );

-- ============================================================
-- SINGLE COLUMN OPTIONS - Cluster by ONE dimension only
-- ============================================================

-- ============================================================
-- OPTION 8: ONLY MEDIA_SOURCE
-- Use when: Almost all queries are "Which media_source...?"
-- Best for: Traffic source focused analysis
-- ============================================================
-- CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
--   event_time TIMESTAMP NOT NULL,
--   hr INT64,
--   media_source STRING,
--   app_id STRING,
--   partner STRING,
--   site_id STRING,
--   engagement_type STRING,
--   is_retargeting BOOLEAN,
--   is_engaged_view BOOLEAN,
--   total_events INT64
-- )
-- PARTITION BY DATE(event_time)
-- CLUSTER BY media_source
-- OPTIONS(
--   require_partition_filter = TRUE,
--   partition_expiration_days = 365,
--   description = "Click events dataset - ONLY MEDIA_SOURCE clustering"
-- );

-- ============================================================
-- OPTION 9: ONLY APP_ID
-- Use when: Almost all queries are "Which app...?"
-- Best for: App-centric analysis
-- ============================================================
-- CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
--   event_time TIMESTAMP NOT NULL,
--   hr INT64,
--   media_source STRING,
--   app_id STRING,
--   partner STRING,
--   site_id STRING,
--   engagement_type STRING,
--   is_retargeting BOOLEAN,
--   is_engaged_view BOOLEAN,
--   total_events INT64
-- )
-- PARTITION BY DATE(event_time)
-- CLUSTER BY app_id
-- OPTIONS(
--   require_partition_filter = TRUE,
--   partition_expiration_days = 365,
--   description = "Click events dataset - ONLY APP_ID clustering"
-- );

-- ============================================================
-- OPTION 10: ONLY PARTNER
-- Use when: Almost all queries are "Which partner...?"
-- Best for: Partner/agency focused analysis
-- ============================================================
-- CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
--   event_time TIMESTAMP NOT NULL,
--   hr INT64,
--   media_source STRING,
--   app_id STRING,
--   partner STRING,
--   site_id STRING,
--   engagement_type STRING,
--   is_retargeting BOOLEAN,
--   is_engaged_view BOOLEAN,
--   total_events INT64
-- )
-- PARTITION BY DATE(event_time)
-- CLUSTER BY partner
-- OPTIONS(
--   require_partition_filter = TRUE,
--   partition_expiration_days = 365,
--   description = "Click events dataset - ONLY PARTNER clustering"
-- );

-- ============================================================
-- OPTION 11: ONLY IS_RETARGETING
-- Use when: Almost all queries are "Retargeting vs UA?"
-- Best for: Retargeting focused analysis
-- ============================================================
-- CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
--   event_time TIMESTAMP NOT NULL,
--   hr INT64,
--   media_source STRING,
--   app_id STRING,
--   partner STRING,
--   site_id STRING,
--   engagement_type STRING,
--   is_retargeting BOOLEAN,
--   is_engaged_view BOOLEAN,
--   total_events INT64
-- )
-- PARTITION BY DATE(event_time)
-- CLUSTER BY is_retargeting
-- OPTIONS(
--   require_partition_filter = TRUE,
--   partition_expiration_days = 365,
--   description = "Click events dataset - ONLY IS_RETARGETING clustering"
-- );

-- ============================================================
-- OPTION 12: ONLY SITE_ID
-- Use when: Almost all queries are "Which site...?"
-- Best for: Publisher/website focused analysis
-- ============================================================
-- CREATE TABLE `practicode-2025.clicks_data_prac.encoded_clicks` (
--   event_time TIMESTAMP NOT NULL,
--   hr INT64,
--   media_source STRING,
--   app_id STRING,
--   partner STRING,
--   site_id STRING,
--   engagement_type STRING,
--   is_retargeting BOOLEAN,
--   is_engaged_view BOOLEAN,
--   total_events INT64
-- )
-- PARTITION BY DATE(event_time)
-- CLUSTER BY site_id
-- OPTIONS(
--   require_partition_filter = TRUE,
--   partition_expiration_days = 365,
--   description = "Click events dataset - ONLY SITE_ID clustering"
-- );

-- ============================================================
-- WHY THIS PARTITION STRATEGY?
-- ============================================================
-- PARTITION BY DATE(event_time):
--   ✅ User queries mostly ask for a specific day ("תן לי את 23.12.2025")
--   ✅ Partition size: ~100GB/day ÷ 1 = manageable
--   ✅ Pruning: One query = read one partition only
--   ✅ TTL management: Easy to drop old partitions
--
-- CLUSTER BY media_source, app_id, partner, is_retargeting:
--   ✅ Most common filters: "Who sends most clicks?" (media_source)
--   ✅ Secondary filters: app breakdowns, partner analysis
--   ✅ Boolean filters: retargeting vs UA-only queries
--   ✅ Reduces I/O within each partition by 4-10x
--
-- require_partition_filter = TRUE:
--   ✅ Prevents accidental full-table scans
--   ✅ Forces all queries to have DATE filter
--   ✅ Protects from expensive mistakes
--
-- partition_expiration_days = 365:
--   ✅ Auto-delete partitions older than 1 year
--   ✅ Reduce storage costs for older data
--   ✅ (Optional: move to cold storage instead)

-- ============================================================
-- MONITORING: Check partition distribution
-- ============================================================
-- Run this weekly to monitor partition sizes:
--
-- SELECT
--   DATE(event_time) AS partition_date,
--   COUNT(*) AS row_count,
--   ROUND(SUM(total_events) / 1e9, 2) AS total_events_billions
-- FROM `practicode-2025.clicks_data_prac.encoded_clicks`
-- WHERE DATE(event_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
-- GROUP BY partition_date
-- ORDER BY partition_date DESC;

-- ============================================================
-- QUERY EXAMPLES: Leverage partition pruning
-- ============================================================

-- ✅ Query 1: Single day (reads 1 partition)
-- SELECT SUM(total_events)
-- FROM `practicode-2025.clicks_data_prac.encoded_clicks`
-- WHERE DATE(event_time) = '2025-12-23';

-- ✅ Query 2: Date range (reads 7 partitions)
-- SELECT 
--   DATE(event_time) AS day,
--   media_source,
--   SUM(total_events) AS total_clicks
-- FROM `practicode-2025.clicks_data_prac.encoded_clicks`
-- WHERE DATE(event_time) BETWEEN '2025-12-17' AND '2025-12-23'
-- GROUP BY day, media_source
-- ORDER BY day DESC, total_clicks DESC;

-- ✅ Query 3: Top media sources (with clustering benefit)
-- SELECT 
--   media_source,
--   SUM(total_events) AS total_clicks
-- FROM `practicode-2025.clicks_data_prac.encoded_clicks`
-- WHERE DATE(event_time) = '2025-12-23'
--   AND is_retargeting = FALSE
-- GROUP BY media_source
-- ORDER BY total_clicks DESC
-- LIMIT 10;

-- ============================================================
-- CODE INTEGRATION: Agent A in Python
-- ============================================================
-- Agent A (IntentAgent) already generates queries with:
--   WHERE DATE(event_time) = "..."
--   WHERE DATE(event_time) BETWEEN "..." AND "..."
--
-- This automatically leverages the partition pruning.
-- No changes needed to Agent A code!
--
-- See: main_agent/sub_agents/a_intent_agent/agent.py
--   Lines 96-104: Deterministic date extraction
--   Lines 249-250: DATE filter generation in prompt

-- ============================================================
-- OPTIONAL: MULTI-TABLE SETUP (separate names, run in addition)
-- ============================================================
-- Use this if you want more than one clustered layout simultaneously.
-- Each CREATE has a UNIQUE table name to avoid conflicts.
-- You can run all of them (they create different tables).

-- 1) DEFAULT DAILY (balanced) – keep existing name
--    practicode-2025.clicks_data_prac.encoded_clicks
--    Partition: DATE(event_time)
--    Cluster: media_source, app_id, partner, is_retargeting

-- 2) DAILY, APP-FOCUSED
CREATE TABLE IF NOT EXISTS `practicode-2025.clicks_data_prac.encoded_clicks_day_app` (
  event_time TIMESTAMP NOT NULL,
  hr INT64,
  media_source STRING,
  app_id STRING,
  partner STRING,
  site_id STRING,
  engagement_type STRING,
  is_retargeting BOOLEAN,
  is_engaged_view BOOLEAN,
  total_events INT64
)
PARTITION BY DATE(event_time)
CLUSTER BY app_id, media_source, partner, is_retargeting
OPTIONS(
  require_partition_filter = TRUE,
  partition_expiration_days = 365,
  description = "Click events dataset - APP-focused clustering"
);

-- 3) DAILY, MEDIA_SOURCE-FOCUSED
CREATE TABLE IF NOT EXISTS `practicode-2025.clicks_data_prac.encoded_clicks_day_source` (
  event_time TIMESTAMP NOT NULL,
  hr INT64,
  media_source STRING,
  app_id STRING,
  partner STRING,
  site_id STRING,
  engagement_type STRING,
  is_retargeting BOOLEAN,
  is_engaged_view BOOLEAN,
  total_events INT64
)
PARTITION BY DATE(event_time)
CLUSTER BY media_source, app_id, is_retargeting, partner
OPTIONS(
  require_partition_filter = TRUE,
  partition_expiration_days = 365,
  description = "Click events dataset - MEDIA_SOURCE-focused clustering"
);

-- 4) HOURLY, MEDIA_SOURCE-FOCUSED (use only if you truly need per-hour queries)
CREATE TABLE IF NOT EXISTS `practicode-2025.clicks_data_prac.encoded_clicks_hourly_source` (
  event_time TIMESTAMP NOT NULL,
  hr INT64,
  media_source STRING,
  app_id STRING,
  partner STRING,
  site_id STRING,
  engagement_type STRING,
  is_retargeting BOOLEAN,
  is_engaged_view BOOLEAN,
  total_events INT64
)
PARTITION BY TIMESTAMP_TRUNC(event_time, HOUR)
CLUSTER BY media_source, app_id
OPTIONS(
  require_partition_filter = TRUE,
  description = "Click events dataset - HOURLY, media_source-focused clustering"
);

-- ============================================================
-- ROUTING HINTS FOR AGENTS (manual logic to add in code)
-- ============================================================
-- Default: encoded_clicks (daily balanced)
-- If question mentions "by hour" / "per hour" / "לפי שעה": use encoded_clicks_hourly_source
-- If question focuses on app/top apps (and not media_source-first): use encoded_clicks_day_app
-- If question focuses on media_source/top sources: use encoded_clicks_day_source
-- Else: stay with encoded_clicks (balanced)
