-- ============================================================
-- Creating Multiple Optimized Partitioned Tables
-- Each table is optimized for different query patterns
-- ============================================================

-- ============================================================
-- TABLE 1: General Balanced (already exists as encoded_clicks_partitioned)
-- Use: Mixed queries, general analysis
-- Priority: media_source, app_id, partner, is_retargeting
-- ============================================================

-- ============================================================
-- TABLE 2: APP-OPTIMIZED
-- Use when: "Which app...", "Top apps...", "App performance..."
-- Best for: Questions starting with app analysis
-- ============================================================
CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.encoded_clicks_by_app`
PARTITION BY DATE(event_time)
CLUSTER BY app_id, media_source, partner, is_retargeting
OPTIONS(
  require_partition_filter = TRUE,
  partition_expiration_days = 365,
  description = "APP-optimized: Best for app-focused queries"
)
AS
SELECT * FROM `practicode-2025.clicks_data_prac.encoded_clicks_partitioned`;

-- ============================================================
-- TABLE 3: MEDIA_SOURCE-OPTIMIZED
-- Use when: "Which media source...", "Top sources...", "Traffic sources..."
-- Best for: Questions about media sources, traffic analysis
-- ============================================================
CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.encoded_clicks_by_media`
PARTITION BY DATE(event_time)
CLUSTER BY media_source, app_id, is_retargeting, partner
OPTIONS(
  require_partition_filter = TRUE,
  partition_expiration_days = 365,
  description = "MEDIA_SOURCE-optimized: Best for traffic source queries"
)
AS
SELECT * FROM `practicode-2025.clicks_data_prac.encoded_clicks_partitioned`;

-- ============================================================
-- TABLE 4: PARTNER-OPTIMIZED
-- Use when: "Which partner...", "Partner performance...", "Agency analysis..."
-- Best for: Questions about partners/agencies
-- ============================================================
CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.encoded_clicks_by_partner`
PARTITION BY DATE(event_time)
CLUSTER BY partner, app_id, media_source, is_retargeting
OPTIONS(
  require_partition_filter = TRUE,
  partition_expiration_days = 365,
  description = "PARTNER-optimized: Best for partner/agency queries"
)
AS
SELECT * FROM `practicode-2025.clicks_data_prac.encoded_clicks_partitioned`;

-- ============================================================
-- TABLE 5: RETARGETING-OPTIMIZED
-- Use when: "Retargeting vs UA...", "Only retargeting...", "Non-retargeting..."
-- Best for: Questions filtering by retargeting first
-- ============================================================
CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.encoded_clicks_by_retargeting`
PARTITION BY DATE(event_time)
CLUSTER BY is_retargeting, media_source, app_id, partner
OPTIONS(
  require_partition_filter = TRUE,
  partition_expiration_days = 365,
  description = "RETARGETING-optimized: Best for retargeting analysis"
)
AS
SELECT * FROM `practicode-2025.clicks_data_prac.encoded_clicks_partitioned`;

-- ============================================================
-- TABLE 6: SITE-OPTIMIZED
-- Use when: "Which site...", "Top sites...", "Publisher performance..."
-- Best for: Questions about sites/publishers
-- ============================================================
CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.encoded_clicks_by_site`
PARTITION BY DATE(event_time)
CLUSTER BY site_id, media_source, app_id, is_retargeting
OPTIONS(
  require_partition_filter = TRUE,
  partition_expiration_days = 365,
  description = "SITE-optimized: Best for site/publisher queries"
)
AS
SELECT * FROM `practicode-2025.clicks_data_prac.encoded_clicks_partitioned`;

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- Check all tables exist:
SELECT 
  table_name,
  ROUND(size_bytes/1024/1024/1024, 2) AS size_gb,
  row_count
FROM `practicode-2025.clicks_data_prac.__TABLES__`
WHERE table_name LIKE 'encoded_clicks_%'
ORDER BY table_name;

-- Check partitions per table:
SELECT 
  table_name,
  partition_id,
  ROUND(total_rows/1000000, 2) AS million_rows
FROM `practicode-2025.clicks_data_prac.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_name LIKE 'encoded_clicks_%'
  AND partition_id IS NOT NULL
ORDER BY table_name, partition_id;
