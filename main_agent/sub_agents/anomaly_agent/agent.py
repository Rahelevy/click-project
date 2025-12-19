from google.cloud import bigquery

PROJECT = "practicode-2025"
DATASET = "clicks_data_prac"
TABLE = f"{PROJECT}.{DATASET}.final_anomalies"

client = bigquery.Client(project=PROJECT)

class AnomalyAgent:

    def get_all_anomalies(self):
        sql = f"""
        SELECT *
        FROM `{TABLE}`
        ORDER BY ABS(z_score) DESC
        LIMIT 200
        """
        return list(client.query(sql).result())

    def get_media_source_anomalies(self, media_source):
        sql = f"""
        SELECT *
        FROM `{TABLE}`
        WHERE media_source = '{media_source}'
        ORDER BY ABS(z_score) DESC
        """
        return list(client.query(sql).result())

    def get_anomalies_by_hour(self, day, hour):
        sql = f"""
        SELECT *
        FROM `{TABLE}`
        WHERE day_date = '{day}'
          AND hour_of_day = {hour}
        ORDER BY ABS(z_score) DESC
        """
        return list(client.query(sql).result())

    def answer(self, question: str):
        q = question.lower()

        if "כל" in q or "all" in q:
            return self.format_results(self.get_all_anomalies())

        if "media" in q:
            # נניח שהשאלה מכילה את שם ה-media
            parts = q.split()
            for p in parts:
                if "media" in p:
                    return self.format_results(self.get_media_source_anomalies(p))
            return "לא זיהיתי שם media source."

        if "שעה" in q or "hour" in q:
            return "⚠️ ניתוח שאלות פר שעה יתווסף בעוד רגע — צריך דוגמה לשאלה שלך."

        return "לא הבנתי את השאלה."

    def format_results(self, rows):
        if not rows:
            return "לא נמצאו אנומליות."

        text = "🔥 אנומליות שנמצאו:\n\n"
        
        for r in rows:
            text += (
                f"• מקור {r['media_source']} ביום {r['day_date']} "
                f"שעה {r['hour_of_day']}: "
                f"Actual={r['actual_events']}, Expected={r['expected_events']}, "
                f"Deviation={r['deviation']}, z={r['z_score']:.2f}\n"
            )

        return text
