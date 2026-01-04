# מערכת טבלאות מותאמות - Optimized Partitioned Tables System

## 📊 סקירה כללית

המערכת כוללת 6 טבלאות מפורטשות שונות, כל אחת מותאמת לסוג שאלות מסוים:

| טבלה | ייעוד | Clustering | מתי להשתמש |
|------|-------|-----------|------------|
| `encoded_clicks_partitioned` | כללי מאוזן | media_source, app_id, partner, is_retargeting | שאלות מעורבות, ניתוח כללי |
| `encoded_clicks_by_app` | מיקוד באפליקציות | **app_id**, media_source, partner, is_retargeting | "איזה אפ הכי טוב?", "ביצועי אפליקציות" |
| `encoded_clicks_by_media` | מיקוד במקורות תעבורה | **media_source**, app_id, is_retargeting, partner | "איזה מקור מדיה?", "ניתוח תעבורה" |
| `encoded_clicks_by_partner` | מיקוד בשותפים | **partner**, app_id, media_source, is_retargeting | "ביצועי שותפים", "ניתוח סוכנויות" |
| `encoded_clicks_by_retargeting` | מיקוד בריטרגטינג | **is_retargeting**, media_source, app_id, partner | "רק ריטרגטינג", "UA לעומת ריטרגטינג" |
| `encoded_clicks_by_site` | מיקוד באתרים | **site_id**, media_source, app_id, is_retargeting | "איזה אתר?", "ביצועי מפרסמים" |

## 🚀 יצירת הטבלאות

### שלב 1: הרצת הסקריפט ב-BigQuery

```bash
# בטרמינל או ב-BigQuery UI, הריצי את הקובץ:
```

הקובץ: `main_agent/create_optimized_tables.sql`

או הדביקי ישירות ב-BigQuery Query Editor והריצי את כל השאילתות.

**⏱️ זמן ריצה משוער:** 5-10 דקות (כל טבלה ~2 דקות)

**💾 נפח אחסון:** כל טבלה תופסת כמו המקור (אם יש לך 800GB, סה"כ יהיה ~4.8TB)

### שלב 2: אימות

```sql
-- בדיקה שכל הטבלאות נוצרו:
SELECT 
  table_name,
  ROUND(size_bytes/1024/1024/1024, 2) AS size_gb,
  row_count
FROM `practicode-2025.clicks_data_prac.__TABLES__`
WHERE table_name LIKE 'encoded_clicks_%'
ORDER BY table_name;
```

אמורות להופיע 6 טבלאות עם אותו מספר שורות.

## 🧠 בחירה אוטומטית של טבלה

הקוד כבר עודכן להשתמש ב-`table_router.py` שבוחר אוטומטית את הטבלה הנכונה:

### דוגמאות לבחירה אוטומטית:

| שאלה | טבלה נבחרת | סיבה |
|------|------------|------|
| "איזה אפליקציה הכי טובה ב-24/10?" | `encoded_clicks_by_app` | זיהוי מילת מפתח "אפליקציה" + "איזה" |
| "מה המקורות מדיה הכי טובים?" | `encoded_clicks_by_media` | זיהוי "מקורות מדיה" |
| "ביצועי השותף XYZ" | `encoded_clicks_by_partner` | זיהוי "שותף" |
| "רק ריטרגטינג" | `encoded_clicks_by_retargeting` | זיהוי "ריטרגטינג" |
| "איזה אתר הכי טוב?" | `encoded_clicks_by_site` | זיהוי "אתר" + "איזה" |
| "כמה קליקים היו ב-24/10?" | `encoded_clicks_partitioned` | שאלה כללית |

## 🔧 בדיקת הניתוב

```bash
# בדיקה של הניתוב:
cd main_agent
python table_router.py
```

זה יריץ בדיקות אוטומטיות ויראה איזו טבלה נבחרת לכל סוג שאלה.

## 📈 ביצועים צפויים

### לפני (טבלה ישנה ללא פרטישן):
- **Bytes scanned:** 811 GB
- **Duration:** 7-23 שניות
- **Cost:** $4 לשאילתה (811GB × $5/TB)

### אחרי (טבלאות מפורטשות מותאמות):
- **Bytes scanned:** 270 GB (שליש!)
- **Duration:** 1-3 שניות
- **Cost:** $1.35 לשאילתה (67% הנחה!)

### שיפור נוסף עם Clustering נכון:
כשהשאלה מתאימה לטבלה (למשל שאלה על app ב-`encoded_clicks_by_app`):
- **Bytes scanned:** 50-100 GB (עד 90% פחות!)
- **Duration:** 0.5-1 שניות
- **Cost:** $0.25-0.50 לשאילתה

## 🧹 ניקוי Cache

אחרי יצירת הטבלאות החדשות, נקי את ה-cache:

```bash
python clear_cache.py
```

## 🔄 עדכון עתידי של נתונים

כשמעלים נתונים חדשים, צריך לעדכן את כל 6 הטבלאות:

```sql
-- אופציה 1: INSERT חדש (מוסיף רק שורות חדשות)
INSERT INTO `practicode-2025.clicks_data_prac.encoded_clicks_by_app`
SELECT * FROM `practicode-2025.clicks_data_prac.encoded_clicks_partitioned`
WHERE DATE(event_time) >= '2025-10-27';  -- תאריכים חדשים

-- אופציה 2: יצירה מחדש של הטבלה
CREATE OR REPLACE TABLE `practicode-2025.clicks_data_prac.encoded_clicks_by_app`
...
AS SELECT * FROM `practicode-2025.clicks_data_prac.encoded_clicks_partitioned`;
```

## 🎯 המלצות

1. **השתמשי בטבלאות החדשות:** הקוד כבר מנתב אוטומטית
2. **עקבי אחר עלויות:** ב-BigQuery Console → Billing
3. **נטרי ביצועים:** בדקי Job History אחרי כל שאילתה
4. **שמרי על סנכרון:** עדכני את כל הטבלאות ביחד

## 📞 תמיכה

אם יש בעיות:
1. בדקי שכל 6 הטבלאות קיימות (שאילתת אימות למעלה)
2. ודאי ש-`table_router.py` מזהה נכון את סוג השאלה (הריצי בדיקות)
3. נקי cache ונסי שוב
4. בדקי לוגים: `[IntentAgent] Selected table: ...`
