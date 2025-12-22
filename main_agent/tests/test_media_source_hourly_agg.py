from google.cloud import bigquery

client = bigquery.Client(project="practicode-2025")

query = """
SELECT
  day_date,
  hour_of_day,
  media_source,
  total_clicks
FROM `practicode-2025.clicks_data_prac.media_source_hourly_agg`
ORDER BY day_date, hour_of_day, media_source
LIMIT 200
"""

rows = client.query(query).result()

print("\n📊 media_source_hourly_agg – דוגמה לנתונים בטבלה:\n")
for row in rows:
    print(dict(row))