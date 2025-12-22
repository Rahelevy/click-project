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
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │ Intent Agent (Agent 1)          │
                    │ - Validates question            │
                    │ - Checks if complete           │
                    │ - Extracts: app_id, dates       │
                    │ - Generates SQL                 │
                    │ - Returns: valid=true/false     │
                    └─────────────────┬───────────────┘
                                      │
                          ┌───────────┴────────────┐
                          │                        │
         Is ANOMALY question?         Regular question
                          │                        │
                          ▼                        ▼
         ┌──────────────────────────────┐ ┌─────────────────────┐
         │ Anomaly Agent (Agent Bonus)  │ │ Focus Agent (Ag 2)  │
         │ - Detects anomalies          │ │ - Ask clarification │
         │ - Hourly aggregation         │ │ - Refine question   │
         │ - Media source analysis      │ │ - Update SQL        │
         │ - Returns answer directly    │ │ - Loop if needed    │
         └──────────────┬───────────────┘ └──────────┬──────────┘
                        │                            │
                        │                            ▼
                        │              ┌─────────────────────────┐
                        │              │ BigQuery Cache          │
                        │              │ - Check if cached       │
                        │              └──────────┬──────────────┘
                        │                         │
                        │                         ▼
                        │              ┌─────────────────────────┐
                        │              │ Executor Agent (Ag 3)   │
                        │              │ - Execute SQL           │
                        │              │ - Aggregation           │
                        │              │ - Cache results         │
                        │              └──────────┬──────────────┘
                        │                         │
                        │                         ▼
                        │              ┌─────────────────────────┐
                        │              │ Explanation Agent (Ag 4)│
                        │              │ - Formats data          │
                        │              │ - Detects language      │
                        │              │ - Render: text/table/ch │
                        │              └──────────┬──────────────┘
                        │                         │
                        └────────────┬────────────┘
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
- אם כן → החזרת תשובה מהירה
- אם לא → המשך לביצוע

### 5️⃣ ביצוע Query (Executor Agent)
- הרצת SQL על BigQuery
- טיפול באגרגציות
- שמירת תוצאות במטמון

### 6️⃣ עיצוב תשובה (Explanation Agent)
- זיהוי שפה
- בחירת סוג תצוגה: text / table / chart
- יצירת הסבר ידידותי למשתמש

### 7️⃣ החזרת תשובה
- הצגת התוצאות למשתמש בפורמט המתאים

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
