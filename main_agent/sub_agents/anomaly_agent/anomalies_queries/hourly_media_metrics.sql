CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.hourly_media_metrics` AS
SELECT
  DATE(event_time) AS day_date,
  hr AS hour_of_day,
  media_source,
  SUM(total_events) AS events
FROM `practicode-2025.clicks_data_prac.encoded_clicks`
WHERE event_time >= '2025-10-24'
  AND event_time <  '2025-10-27'
GROUP BY 1,2,3;
