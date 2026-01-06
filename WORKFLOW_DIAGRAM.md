# Workflow Diagram (תרשים זרימת עבודה)

```
                         START
                           │
                           ▼
                    ┏━━━━━━━━━━━━━┓
                    ┃ User sends  ┃
                    ┃  question   ┃
                    ┗━━━━━┯━━━━━━━┛
                          │
                          ▼
                    ┌─────────────┐
                    │ Intent Agent│
                    │   Parse &   │
                    │   Validate  │
                    └──────┬──────┘
                           │
                           ▼
                      ╔════════╗
                      ║ Type?  ║
                      ╚═══╤════╝
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    [Anomaly]        [Invalid]        [Valid]
         │                │                │
         ▼                ▼                │
    ┌─────────┐     ┌──────────┐          │
    │ Anomaly │     │  Focus   │          │
    │  Agent  │     │  Agent   │          │
    └────┬────┘     └────┬─────┘          │
         │               │                │
         │          ╔════╧════╗           │
         │          ║ Valid?  ║           │
         │          ╚════╤════╝           │
         │               │                │
         │        ┌──────┴─────┐          │
         │       No           Yes         │
         │        │            │          │
         │        └──►Loop     │          │
         │                     │          │
         │                     ▼          │
         │              ┌──────────────┐  │
         │              │ Check Cache  │◄─┘
         │              └──────┬───────┘
         │                     │
         │                ╔════╧════╗
         │                ║ Cached? ║
         │                ╚════╤════╝
         │                     │
         │              ┌──────┴─────┐
         │             Yes           No
         │              │             │
         │              │             ▼
         │              │      ┌──────────┐
         │              │      │ Executor │
         │              │      │  Agent   │
         │              │      └────┬─────┘
         │              │           │
         │              │           ▼
         │              │      ┌──────────┐
         │              │      │   Save   │
         │              │      │  Cache   │
         │              │      └────┬─────┘
         │              │           │
         │              └───────────┘
         │                     │
         │                     ▼
         │              ┌─────────────┐
         │              │ Explanation │
         │              │    Agent    │
         │              └──────┬──────┘
         │                     │
         └─────────────────────┘
                           │
                           ▼
                    ┏━━━━━━━━━━━━━┓
                    ┃   Return    ┃
                    ┃   Response  ┃
                    ┗━━━━━━━━━━━━━┛
                           │
                           ▼
                          END


Legend (מקרא):
┏━━━━━┓  Start/End (התחלה/סיום)
┌─────┐  Process (תהליך)
╔═════╗  Decision (החלטה)
```

---

## Process Description (תיאור התהליכים)

### 1. User Input
המשתמש שולח שאלה בשפה טבעית (עברית או אנגלית)

### 2. Intent Agent - Parsing & Validation
- ניתוח השאלה
- זיהוי סוג השאלה (רגילה / אנומליה) → sets `query_type`
- חילוץ פרמטרים (app_id, תאריכים, media_source)
- בדיקת תקינות
- **בחירת טבלה אופטימלית** (Table Router)

### 3. Decision: Question Type
**שלושה מסלולים אפשריים:**

#### Path A: Anomaly Question
- זוהתה כשאלת אנומליה (query_type="anomaly")
- מועבר ישירות ל-Anomaly Agent (**✅ FULLY INTEGRATED**)
- הסוכן מבצע ניתוח על טבלת anomalies
- מחזיר visualization עם matplotlib
- גרף מוטבע ב-base64 PNG
- סוף תהליך

#### Path B: Invalid/Incomplete Question
- חסר מידע חיוני
- מועבר ל-Focus Agent
- הסוכן שואל שאלות הבהרה
- **Decision Point:** האם קיבלנו מספיק מידע?
  - **No** → חזרה ל-Focus Agent (Loop)
  - **Yes** → המשך לבדיקת Cache

#### Path C: Valid Question
- השאלה תקינה ומלאה
- ממשיך ישירות לבדיקת Cache

### 4. Check Cache
בדיקה אם קיימת תשובה שמורה במטמון עבור אותה שאילתה
- נורמליזציה של SQL (whitespace/case insensitive)
- SHA256 hash key
- TTL: 30 days

**Decision Point:** האם נמצא במטמון?
- **Yes** → שליפת התוצאות מהמטמון (מהיר)
- **No** → המשך להרצת  (EU location)
- שימוש בטבלה המותאמת (Table Router)
- טיפול באגרגציות
- קבלת תוצאות

### 6. Save to Cache
- שמירת התוצאות במטמון לשימוש עתידי
- MERGE operation (INSERT or UPDATE)
- Serialization with datetime support

### 6. Save to Cache
שמירת התוצאות במטמ (עברית/אנגלית + RTL/LTR)
- **זיהוי אוטומטי של בקשות לגרף** (keywords: chart, graph, תרשים, גרף)
- **בחירה חכמה של עמודות** ל-X/Y axis based on question context
- **ייצור גרפים** עם matplotlib:
  - Bar charts (with value formatting)
  - Line charts (optimized for time-series)
  - Pie charts
- **זיהוי "Top N" queries** והדגשת הממצא המוביל
- בחירת פורמט תצוגה: text / table / chart
- יצירת הסבר ידידותי למשתמש

### 8. Return Response
- החזרת התשובה למשתמש דרך SSE
- **React UI מעבד את התגובה:**
  - TableRenderer for structured data
  - ChartRenderer for visualizations
  - Automatic RTL/LTR support
- שמירה ב-LocalStorage (conversation history)י למשתמש

### 8. Return Response
החזרת התשובה למשתמש

---

## Key Differences from Architecture Diagram

**תרשים הארכיטקטורה** מראה את **מבנה הרכיבים והקשרים** ביניהם.

**תרשים ה-Workflow** מראה את **תהליך קבלת ההחלטות והזרימה** הלוגית:
- נקודות החלטה (Decision Points)
- לולאות (Loops)
- תנאים (Conditions)
- סדר ביצוע (Execution Order)
- מסלולים חלופיים (Alternative Paths)

---

## Example Flows

### Flow 1: Valid Regular Question (זרימה רגילה)
```
User → Intent → [Valid] → Cache → [No] → Executor → Save → Explanation → Return
```

### Flow 2: Invalid Question with Loop (שאלה לא מלאה)
```
User → Intent → [Invalid] → Focus → [No] → Focus → [Yes] → Cache → ...
```

### Flow 3: Anomaly Detection (זיהוי אנומליות)
```
User → Intent → [Anomaly] → Anomaly Agent → Return
```

### Flow 4: Cache Hit (מטמון)
```
User → Intent → [Valid] → Cache → [Yes] → Explanation → Return
```
