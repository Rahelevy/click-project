CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.media_source_hourly_agg` AS
SELECT
  DATE(event_time) AS day_date,      -- הופך את event_time ליום בלבד (ללא שעה)
  hr AS hour_of_day,                 -- השעה מתוך השדה hr שיש לך בטבלה המקורית
  media_source,                      -- מקור המדיה
  SUM(total_events) AS total_clicks  -- סכום הקליקים באותה שעה/יום/מדיה
FROM `practicode-2025.clicks_data_prac.encoded_clicks`
WHERE event_time >= '2025-10-24'
  AND event_time <  '2025-10-27'     -- כולל 24,25,26 באוקטובר (שלושה ימים מלאים)
GROUP BY
  day_date,
  hour_of_day,
  media_source
ORDER BY
  day_date,
  hour_of_day,
  media_source;