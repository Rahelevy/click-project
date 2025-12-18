CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.hourly_anomalies` AS
WITH base AS (
  SELECT
    h1.day_date,
    h1.hour_of_day,
    h1.events AS actual_events,
    AVG(h2.events) AS expected_events,
    STDDEV(h2.events) AS std_events
  FROM `practicode-2025.clicks_data_prac.hourly_metrics` h1
  JOIN `practicode-2025.clicks_data_prac.hourly_metrics` h2
    ON h1.hour_of_day = h2.hour_of_day
   AND h1.day_date != h2.day_date
  GROUP BY 1,2,3
),
scored AS (
  SELECT
    *,
    (actual_events - expected_events) / NULLIF(std_events,0) AS z_score,
    (actual_events - expected_events) / NULLIF(expected_events,0) AS rel_diff
  FROM base
)
SELECT *
FROM scored
WHERE ABS(z_score) > 2.5
  AND ABS(rel_diff) > 0.3;
