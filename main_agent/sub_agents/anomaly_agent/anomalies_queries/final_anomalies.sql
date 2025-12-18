CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.final_anomalies` AS
SELECT
  'media_source_ultra_strict' AS anomaly_type,
  day_date,
  hour_of_day,
  media_source,
  actual_events,
  expected_events,
  ROUND(actual_events / NULLIF(expected_events,0), 2) AS strength_ratio
FROM `practicode-2025.clicks_data_prac.media_source_anomalies`
ORDER BY day_date, hour_of_day, media_source;
