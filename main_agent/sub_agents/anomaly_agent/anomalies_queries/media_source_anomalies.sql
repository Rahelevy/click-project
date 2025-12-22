CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.media_source_anomalies` AS

WITH base AS (
  -- טבלת בסיס: קליקים לפי תאריך, שעה ומקור מדיה
  -- event_ts משמש לסידור כרונולוגי מדויק (עדיף על day_date + hour)
  SELECT
    day_date,
    hour_of_day,
    media_source,
    total_clicks AS actual_events,
    TIMESTAMP(CONCAT(day_date, ' ', hour_of_day, ':00:00')) AS event_ts
  FROM `practicode-2025.clicks_data_prac.media_source_hourly_agg`
),

rolling AS (
  -- חישוב סטטיסטיקות על 6 השעות הקודמות לכל מקור מדיה:
  -- ממוצע וסטיית תקן (לא כולל השעה הנוכחית)
  SELECT
    *,
    AVG(actual_events) OVER (
      PARTITION BY media_source
      ORDER BY event_ts
      ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
    ) AS avg_last_6h,
    STDDEV(actual_events) OVER (
      PARTITION BY media_source
      ORDER BY event_ts
      ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
    ) AS std_last_6h
  FROM base
),

rolling_scored AS (
  -- חישוב Z-score לשעה הנוכחית
  -- נשמרים רק מקרים שבהם הערך בפועל גבוה מהממוצע
  SELECT
    *,
    (actual_events - avg_last_6h) / NULLIF(std_last_6h, 0) AS zRolling
  FROM rolling
  WHERE avg_last_6h IS NOT NULL
    AND std_last_6h IS NOT NULL
    AND actual_events > avg_last_6h
),

strong_candidates AS (
  -- בחירת חריגות קיצוניות באמת:
  -- יותר מ־5 סטיות תקן מעל הממוצע של 6 השעות האחרונות
  SELECT *
  FROM rolling_scored
  WHERE zRolling > 5
),

median_table AS (
  -- חישוב מדיאן קליקים לאותה שעה בדיוק,
  -- על בסיס ימים אחרים (לא היום החריג)
  -- זה מוודא שהשעה לא "חזקה טבעית"
  SELECT
    sc.day_date AS anomaly_day,
    sc.hour_of_day,
    sc.media_source,
    APPROX_QUANTILES(b.actual_events, 2)[OFFSET(1)] AS median_same_hour
  FROM strong_candidates sc
  JOIN base b
    ON sc.media_source = b.media_source
   AND sc.hour_of_day = b.hour_of_day
   AND b.day_date != sc.day_date
  GROUP BY anomaly_day, sc.media_source, sc.hour_of_day
),

validated AS (
  -- הצמדת המדיאן לכל אנומליה
  SELECT
    sc.day_date,
    sc.hour_of_day,
    sc.media_source,
    sc.actual_events,
    mt.median_same_hour
  FROM strong_candidates sc
  LEFT JOIN median_table mt
    ON sc.day_date = mt.anomaly_day
   AND sc.media_source = mt.media_source
   AND sc.hour_of_day = mt.hour_of_day
),

final_candidates AS (
  -- סינון סופי:
  -- 1. יש מדיאן להשוואה
  -- 2. מינימום נפח (100 קליקים)
  -- 3. לפחות פי 3 מהמדיאן של אותה שעה
  SELECT
    day_date,
    hour_of_day,
    media_source,
    actual_events,
    median_same_hour AS expected_events,
    (actual_events - median_same_hour) AS absolute_gap
  FROM validated
  WHERE median_same_hour IS NOT NULL
    AND actual_events >= 100
    AND actual_events > median_same_hour * 3
)

-- החזרת 5 האנומליות החזקות ביותר לפי פער מוחלט
SELECT *
FROM final_candidates
ORDER BY absolute_gap DESC
LIMIT 5;



/* =========================================================
   VERSION 1 – COMMENTED OUT
   Rolling 6h average + Z-score only
   ========================================================= */

-- CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.media_source_anomalies` AS
--
-- WITH base AS (
--   SELECT
--     day_date,
--     hour_of_day,
--     media_source,
--     total_clicks AS actual_events
--   FROM `practicode-2025.clicks_data_prac.media_source_hourly_agg`
-- ),
--
-- rolling AS (
--   SELECT
--     *,
--     COUNT(*) OVER (
--       PARTITION BY media_source
--       ORDER BY day_date, hour_of_day
--       ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
--     ) AS rows_back,
--
--     AVG(actual_events) OVER (
--       PARTITION BY media_source
--       ORDER BY day_date, hour_of_day
--       ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
--     ) AS avg_last_6h,
--
--     STDDEV(actual_events) OVER (
--       PARTITION BY media_source
--       ORDER BY day_date, hour_of_day
--       ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
--     ) AS std_last_6h
--   FROM base
-- ),
--
-- rolling_valid AS (
--   SELECT *
--   FROM rolling
--   WHERE rows_back = 6
--     AND avg_last_6h IS NOT NULL
--     AND std_last_6h IS NOT NULL
-- ),
--
-- rolling_scored AS (
--   SELECT
--     *,
--     (actual_events - avg_last_6h) / NULLIF(std_last_6h, 0) AS zRolling
--   FROM rolling_valid
--   WHERE actual_events > avg_last_6h
-- ),
--
-- strong_candidates AS (
--   SELECT
--     *,
--     avg_last_6h AS expected_events
--   FROM rolling_scored
--   WHERE zRolling > 5
-- ),
--
-- final_candidates AS (
--   SELECT
--     day_date,
--     hour_of_day,
--     media_source,
--     actual_events,
--     expected_events,
--     (actual_events - expected_events) AS absolute_gap,
--     actual_events / expected_events AS ratio
--   FROM strong_candidates
--   WHERE actual_events / expected_events >= 3
-- )
--
-- SELECT *
-- FROM final_candidates
-- QUALIFY ROW_NUMBER() OVER (
--     PARTITION BY media_source
--     ORDER BY absolute_gap DESC
-- ) = 1
-- ORDER BY absolute_gap DESC
-- LIMIT 5;
