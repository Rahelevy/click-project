from google.cloud import bigquery

def main():
    client = bigquery.Client(project="practicode-2025")

    query = """
    SELECT
      day_date,
      hour_of_day,
      media_source,
      actual_events,
      expected_events,
      ratio
    FROM practicode-2025.clicks_data_prac.media_source_anomalies
    ORDER BY day_date, hour_of_day, media_source
    """

    rows = client.query(query).result()

    print("\n===============================")
    print("🔥 ULTRA STRICT ANOMALY REPORT")
    print("===============================\n")

    found = False

    for row in rows:
        found = True
        print(f"📌 On {row.day_date} at {row.hour_of_day}:00")
        print(f"   👉 Media Source: {row.media_source}")
        print(f"   👉 Actual Clicks: {row.actual_events}")
        print(f"   👉 Expected (Median): {row.expected_events}")
        print(f"   👉 Strength: {row.ratio}x above normal")
        print("--------------------------------------------------")

    if not found:
        print("🎉 No ULTRA STRICT anomalies detected.\n")
    else:
        print("\n✨ End of ULTRA STRICT anomaly report ✨\n")

if __name__ == "__main__":
    main()
