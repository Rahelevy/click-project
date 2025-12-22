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
- זיהוי סוג השאלה (רגילה / אנומליה)
- חילוץ פרמטרים (app_id, תאריכים, media_source)
- בדיקת תקינות

### 3. Decision: Question Type
**שלושה מסלולים אפשריים:**

#### Path A: Anomaly Question
- זוהתה כשאלת אנומליה
- מועבר ישירות ל-Anomaly Agent
- הסוכן מחזיר תשובה מלאה עם גרף
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

**Decision Point:** האם נמצא במטמון?
- **Yes** → שליפת התוצאות מהמטמון (מהיר)
- **No** → המשך להרצת Query

### 5. Executor Agent (אם לא נמצא במטמון)
- הרצת SQL על BigQuery
- טיפול באגרגציות
- קבלת תוצאות

### 6. Save to Cache
שמירת התוצאות במטמון לשימוש עתידי

### 7. Explanation Agent
- זיהוי שפת המשתמש
- בחירת פורמט תצוגה: text / table / chart
- יצירת הסבר ידידותי למשתמש

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
