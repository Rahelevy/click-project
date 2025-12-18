from google.cloud import bigquery
import os

PROJECT = "practicode-2025"
DATASET = "clicks_data_prac"
QUERY_PATH = os.path.join(os.path.dirname(__file__), "anomalies_queries")

client = bigquery.Client(project=PROJECT)

def run_sql_file(filename):
    path = os.path.join(QUERY_PATH, filename)
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    print(f"\nRunning {filename}...")
    job = client.query(sql)
    job.result()
    print(f"Completed: {filename}")

def run_pipeline():
    sql_files = [
        # "hourly_metrics.sql",
        # "hourly_media_metrics.sql",
        # "hourly_anomalies.sql",
        # "media_source_hourly_agg.sql",
        "media_source_anomalies.sql",
        "final_anomalies.sql",
    ]

    for file in sql_files:
        run_sql_file(file)

    print("\n🎉 Pipeline completed! All anomaly tables are built.\n")

if __name__ == "__main__":
    run_pipeline()
