import pandas as pd
import matplotlib.pyplot as plt
from google.cloud import bigquery

client = bigquery.Client(project="practicode-2025")

# 1️⃣ שליפת כל האנומליות מהטבלה media_source_anomalies
df_anomalies = client.query("""
SELECT
  day_date,
  hour_of_day,
  media_source,
  actual_events,
  expected_events,
  absolute_gap
FROM `practicode-2025.clicks_data_prac.media_source_anomalies`
ORDER BY absolute_gap DESC
""").to_dataframe()

print(f"🔍 Found {len(df_anomalies)} media source anomalies.")

if df_anomalies.empty:
    print("No anomalies to plot.")
    exit()

# 2️⃣ יצירת גרף עבור כל אנומליה בנפרד
for idx, row in df_anomalies.iterrows():
    media = row["media_source"]
    day = row["day_date"]
    hour = row["hour_of_day"]
    actual = row["actual_events"]

    print(f"📊 Creating graph for {media} — {day} hour {hour}")

    # שליפת כל השעות של אותו media_source (כל הנתונים הקיימים, 3 ימים)
    df_all = client.query(f"""
    SELECT
      day_date,
      hour_of_day,
      total_clicks
    FROM `practicode-2025.clicks_data_prac.media_source_hourly_agg`
    WHERE media_source = '{media}'
    ORDER BY day_date, hour_of_day
    """).to_dataframe()

    if df_all.empty:
        print(f"No data for {media}, skipping.")
        continue

    # יצירת timestamp
    df_all["timestamp"] = pd.to_datetime(
        df_all["day_date"].astype(str) + " " + df_all["hour_of_day"].astype(str) + ":00"
    )

    # יצירת timestamp לאנומליה
    anomaly_ts = pd.to_datetime(str(day) + f" {hour}:00")

    # 3️⃣ ציור הגרף
    plt.figure(figsize=(14, 5))
    plt.plot(df_all["timestamp"], df_all["total_clicks"], label="Clicks per Hour")

    # לא מסמנים נקודה אדומה - האנומליה תראה כעלייה טבעית בגרף

    plt.title(f"Media Source: {media} (Anomaly on {day} at hour {hour}, Gap: {row['absolute_gap']})", fontsize=16)
    plt.xlabel("Time")
    plt.ylabel("Clicks")
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # 4️⃣ שמירת הגרף
    file_name = f"media_anomaly_{media}_{day}_h{hour}.png"
    plt.savefig(file_name)

    print(f"💾 Saved: {file_name}")

    plt.close()

print("🎉 All media source anomaly graphs created!")