# System Architecture - UML Diagram

```
                              User (React UI)
                                    │
                                    ▼
                    Main Agent - RootAgent (Controller)
                    ┌─────────────────────────────────┐
                    │ - Manages conversation context  │
                    │ - Routes through pipeline       │
                    │ - Handles errors & caching      │
                    │ - Multi-turn state management   │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │ Intent Agent (Agent 1)          │
                    │ - Validates question            │
                    │ - Checks if complete           │
                    │ - Extracts: app_id, dates       │
                    │ - Detects query_type (anomaly)  │
                    │ - Generates SQL with routing    │
                    │ - Returns: valid=true/false     │
                    └─────────────────┬───────────────┘
                                      │
                          ┌───────────┴────────────┐
                          │                        │
         Is ANOMALY question?         Regular question
         (query_type="anomaly")                    │
                          │                        │
                          ▼                        ▼
         ┌──────────────────────────────┐ ┌─────────────────────┐
         │ ✅ Anomaly Agent (Integrated)│ │ Focus Agent (Ag 2)  │
         │ - Hourly anomaly aggregation │ │ - Ask clarification │
         │ - Media source analysis      │ │ - Refine question   │
         │ - Z-score detection          │ │ - Update SQL        │
         │ - Chart visualization        │ │ - Loop if needed    │
         │ - Returns directly to user   │ └──────────┬──────────┘
         └──────────────┬───────────────┘            │
                        │                            ▼
                        │              ┌─────────────────────────┐
                        │              │ Table Router            │
                        │              │ - Select optimal table  │
                        │              │ - By app/media/partner  │
                        │              └──────────┬──────────────┘
                        │                         │
                        │                         ▼
                        │              ┌─────────────────────────┐
                        │              │ BigQuery Cache          │
                        │              │ - Normalize SQL         │
                        │              │ - Check if cached       │
                        │              │ - 30-day TTL            │
                        │              └──────────┬──────────────┘
                        │                         │
                        │                         ▼
                        │              ┌─────────────────────────┐
                        │              │ Executor Agent (Ag 3)   │
                        │              │ - Execute SQL           │
                        │              │ - Aggregation support   │
                        │              │ - Cache write (MERGE)   │
                        │              └──────────┬──────────────┘
                        │                         │
                        │                         ▼
                        │              ┌─────────────────────────┐
                        │              │ Explanation Agent (Ag 4)│
                        │              │ - Formats data          │
                        │              │ - Detects language      │
                        │              │ - Auto chart detection  │
                        │              │ - Matplotlib rendering  │
                        │              │ - Render: text/table/ch │
                        │              └──────────┬──────────────┘
                        │                         │
                        └────────────┬────────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │ React UI (SSE)      │
                          │ - TableRenderer     │
                          │ - ChartRenderer     │
                          │ - LocalStorage      │
                          │ - RTL/LTR Support   │
                          └─────────────────────┘
                                     │
                                     ▼
                          User (Final Response)
```

---

## � Workflow Diagram (תרשים זרימת עבודה)

```
                    ┌─────────────────────┐
                    │  User Input         │
                    │  (שאלה בשפה טבעית)  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  RootAgent          │
                    │  קבלת הודעה         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Intent Agent       │
                    │  ניתוח השאלה        │
                    └──────────┬──────────┘
                               │
                      ┌────────┴────────┐
                      │  Decision       │
                      │  סוג השאלה?     │
                      └────────┬────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        [ANOMALY]        [INCOMPLETE]      [REGULAR]
              │                │                │
              │                ▼                │
              │    ┌─────────────────────┐     │
              │    │  Focus Agent        │     │
              │    │  בקשת הבהרה         │     │
              │    └──────────┬──────────┘     │
              │               │                │
              │        ┌──────┴──────┐         │
              │        │  Decision   │         │
              │        │  מספיק מידע? │         │
              │        └──────┬──────┘         │
              │               │                │
              │       ┌───────┴────────┐       │
              │       │                │       │
              │      לא               כן      │
              │       │                │       │
              │       │                ▼       │
              │       │      ┌─────────────────────┐
              │       │      │  BigQuery Cache     │
              │       │      │  בדיקת מטמון        │
              │       │      └──────────┬──────────┘
              │       │                 │
              │       │        ┌────────┴────────┐
              │       │        │  Decision       │
              │       │        │  נמצא במטמון?   │
              │       │        └────────┬────────┘
              │       │                 │
              │       │        ┌────────┴────────┐
              │       │        │                 │
              │       │       כן                לא
              │       │        │                 │
              │       │        │                 ▼
              │       │        │    ┌─────────────────────┐
              │       │        │    │  Executor Agent     │
              │       │        │    │  הרצת SQL           │
              │       │        │    │  BigQuery           │
              │       │        │    └──────────┬──────────┘
              │       │        │               │
              │       │        │               ▼
              │       │        │    ┌─────────────────────┐
              │       │        │    │  שמירה במטמון       │
              │       │        │    └──────────┬──────────┘
              │       │        │               │
              │       │        └───────────────┘
              │       │                 │
              │       │                 ▼
              │       │      ┌─────────────────────┐
              │       │      │  Explanation Agent  │
              │       │      │  עיצוב התוצאות      │
              │       │      │  (text/table/chart) │
              │       │      └──────────┬──────────┘
              │       │                 │
              │       └────►Loop back to Focus Agent
              │                         │
              ▼                         │
   ┌─────────────────────┐             │
   │  Anomaly Agent      │             │
   │  זיהוי אנומליות     │             │
   │  ניתוח hourly       │             │
   │  ייצור גרף          │             │
   │  החזרת תשובה ישירה  │             │
   └──────────┬──────────┘             │
              │                        │
              └────────────┬───────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  User Response      │
                │  תשובה למשתמש       │
                └─────────────────────┘
```

---

## 📋 Workflow Steps (שלבי התהליך)

### 1️⃣ קבלת שאלה
- המשתמש כותב שאלה בשפה טבעית (עברית/אנגלית)
- RootAgent קולט את השאלה

### 2️⃣ ניתוח כוונה (Intent Agent)
- זיהוי סוג השאלה: רגילה / אנומליה
- חילוץ פרמטרים: app_id, תאריכים, media_source
- בדיקת תקינות

### 3️⃣ ניתוב לפי סוג

**A. אנומליה** → ישירות ל-Anomaly Agent
   - ניתוח אנומליות לפי media source
   - זיהוי שעות חריגות
   - ייצור visualization
   - החזרת תשובה מלאה

**B. שאלה לא מלאה** → Focus Agent
   - בקשת הבהרה מהמשתמש
   - Loop עד קבלת מידע מלא
   - עדכון SQL

**C. שאלה רגילה תקינה** → המשך לביצוע

### 4️⃣ Cache Check
- בדיקה האם התשובה קיימת במטמון
- נורמליזציה של SQL query
- אם כן → החזרת תשובה מהירה
- אם לא → המשך לביצוע

### 5️⃣ ביצוע Query (Executor Agent)
- הרצת SQL על BigQuery (EU location)
- טיפול באגרגציות
- שמירת תוצאות במטמון (MERGE statement)

### 6️⃣ עיצוב תשובה (Explanation Agent)
- זיהוי שפה (עברית/אנגלית)
- זיהוי אוטומטי של בקשות לגרף
- בחירה חכמה של עמודות ל-X/Y axis
- ייצור גרפים עם matplotlib (PNG base64)
- בחירת סוג תצוגה: text / table / chart
- יצירת הסבר ידידותי למשתמש

### 7️⃣ החזרת תשובה
- הצגת התוצאות למשתמש בפורמט המתאים
- React UI מעבד: TableRenderer / ChartRenderer
- שמירה ב-LocalStorage

---

## 🔑 Key Components (רכיבים מרכזיים)

### Table Router
- בחירה אוטומטית של הטבלה האופטימלית
- 6 טבלאות מבוססות partition:
  - `encoded_clicks_partitioned` (ברירת מחדל)
  - `encoded_clicks_by_app` (אופטימיזציה לפי אפליקציה)
  - `encoded_clicks_by_media` (אופטימיזציה לפי מקור)
  - `encoded_clicks_by_partner` (אופטימיזציה לפי שותף)
  - `encoded_clicks_by_site` (אופטימיזציה לפי אתר)
  - `encoded_clicks_by_retargeting` (אופטימיזציה לפי ריטרגטינג)

### Cache System
- שימוש ב-BigQuery table: `practicode-2025.cache.query_results`
- נורמליזציה של SQL (case, whitespace insensitive)
- TTL: 30 days
- Hash key: SHA256 של SQL מנורמל
- MERGE operation for cache write

### Chart Generation
- Automatic detection via keywords
- Smart column selection based on user question
- Support for bar, line, pie charts
- Time-series optimization (label rotation, sampling)
- "Top N" detection and handling
- Aggregation by dimension
- Matplotlib backend (PNG base64)

---

## �📊 Data Models

### Agent 1 Output (IntentAgent)
```
{
  question: string
  valid: boolean
  sql: string (if valid)
  reason: string (if invalid)
  missing_fields: string[]
  app_id: string
  date_from: string
  date_to: string
}
```

### Agent 2 Output (FocusAgent)
```
{
  valid: boolean
  sql: string (updated)
  question: string (refined)
  reason: string (if still invalid)
  missing_fields: string[]
}
```

### Agent 3 Output (ExecutorAgent)
```
{
  status: "success" | "error"
  description: string
  rows: object[]
  row_count: number
  aggregated: boolean
  chart_type: string (bar|line|pie|etc)
}
```

### Agent 4 Output (ExplainerAgent)
```
{
  status: "success" | "error"
  description: string (user-friendly)
  render_type: "text" | "table" | "chart"
  table_markdown: string | null
  chart_options: object | null
}
```

### Anomaly Agent Output (AnomalyAgent - Bonus)
```
{
  status: "success" | "error"
  description: string (anomaly summary)
  rows: object[] (anomaly data)
  row_count: number
  chart_type: string (line|bar|scatter)
  anomalies: object[] (detected anomalies by media_source)
}
```

---

## 🛠️ Technologies

| Layer | Tech |
|-------|------|
| Frontend | React 18, Tailwind CSS, ECharts |
| Backend | Python, Google ADK, Google Genai |
| Database | BigQuery (GCP) |
| Language | Hebrew + English support |
| Communication | SSE (Server-Sent Events) |

---

## 🔄 Example Flow

### Regular Query
```
User: "כמה קליקים ל-app_id_123 ביום האחרון?"

1️⃣  RootAgent receives message
2️⃣  Intent Agent: ✓ Valid (has app_id + date)
3️⃣  Skip Focus Agent (not needed)
4️⃣  Check Cache: Cache miss
5️⃣  Executor Agent: Execute SQL on BigQuery
6️⃣  Get Results: 1,234 clicks
7️⃣  Explanation Agent: Format as table
8️⃣  User sees: "בקטגוריה X קיימות 1,234 קליקים..."
```

### Anomaly Query
```
User: "האם יש אנומליה בקליקים של app_id_123?"

1️⃣  RootAgent receives message
2️⃣  Intent Agent: Detects → ANOMALY question ✓
3️⃣  Route to Anomaly Agent directly
4️⃣  Anomaly Agent: 
    - Analyze media sources hourly
    - Detect spikes/drops in data
    - Format as chart visualization
    - Return complete answer
5️⃣  User sees: Visual chart with anomalies (directly from Anomaly Agent)
```
