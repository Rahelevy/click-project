# Specification Document – Multi-Agent System for Data Analysis

## 1. Background and Purpose

This system allows users to run analytics queries on AppsFlyer click data stored in BigQuery, understand SQL results in natural language, and identify insights from raw data. The system is based on four independent agents, each with a clear and well-defined role, to ensure stability, flexibility, and easy maintenance.

**Key Features:**
- Natural language query interface supporting both English and Hebrew
- Multi-turn conversation with clarification requests
- SQL query generation from user questions
- BigQuery execution with caching for performance
- Human-readable explanations of results
- Bilingual support (automatic language detection)



---

## 2. Product Objectives

- Allow users to input free-text questions in natural language (English or Hebrew)
- Validate and refine ambiguous questions through clarification
- Convert valid questions into safe and accurate SQL queries
- Execute SQL queries on BigQuery efficiently with caching support
- Translate SQL results into clear, readable, natural-language explanations
- Support anomaly/fraud queries that return graphs (planned; not yet implemented)

---

## 3. Agent Architecture

### Agent #1 – Intent Agent (Language-to-SQL Converter)

**Responsibility:** Parse natural language questions, validate them, and generate SQL queries.

**Input:** Natural-language question (string or InvocationContext)

**Output:** Validated intent state containing:
- `question`: The parsed user question
- `valid`: Boolean indicating if the question is valid for SQL generation
- `sql`: Generated SQL query (if valid)
- `awaiting_user_input`: Boolean indicating if clarification is needed
- `reason`: If invalid, explains why (e.g., "missing_question", "invalid_date", "invalid_app_id")
- `missing_fields`: List of required fields that are missing
- `app_id`: Extracted app ID (if present)
- `date_from` / `date_to`: Extracted date range
- `media_source`: Extracted media source (if present)

**Validation Steps:**
1. **Question Parsing:** Extracts filters and parameters from the question
   - App ID (format: `app_id_<number>`)
   - Date range (various formats supported)
   - Media source/partner/publisher
   - Other relevant dimensions

2. **Validation Checks:**
   - Is the question understandable and not empty?
   - Are essential filters present (app_id, date range)?
   - Is the question too broad or unsafe?
   - Are all extracted parameters in valid formats?

3. **SQL Generation:**
   - Constructs SELECT statements based on extracted filters
   - Applies WHERE clauses for date ranges and dimensions
   - Adds automatic LIMIT to prevent excessive data retrieval
   - Applies numeric filter fixing (e.g., `app_id = 2` → `app_id = "app_id_2"`)

4. **Language Support:**
   - Automatically detects Hebrew vs. English
   - Handles Hebrew question parsing and validation
   - Generates appropriate error messages in the user's language

**States:**
- **Valid Question:** Returns SQL ready for execution
- **Invalid Question:** Forwards to Agent #2 for clarification
- **Awaiting Input:** Requests missing essential information from user

**Anomaly Requests (Planned):**
- The Intent Agent will classify queries like "show me all the anomalies of 10-24-2025" as anomaly-intent and route them to an internal anomalies module (not a separate agent). This module will produce graphs and a short summary for the specified date/range. Implementation is in progress and will be documented later.

---

### Agent #2 – Focus Agent (Clarification & Refinement)

**Responsibility:** Guide users to provide more precise questions when initial questions are too broad or missing required filters.

**Input:** Invalid intent state containing:
- `original_question`: The user's original unclear question
- `reason`: Why it was invalid
- `missing_fields`: List of fields that need clarification
- `refined_question`: (optional) If provided in a previous interaction

**Output:** Focus agent state containing:
- `awaiting_user_input`: Boolean indicating if more input is needed
- `missing_fields`: Updated list of missing filters
- `question_to_user`: Clarifying question(s) to ask the user
- `refined_question`: The rephrased, more precise question (if enough filters are identified)

**Workflow:**
1. **Analyze Missing Filters:** Uses LLM to determine which filters are still needed
   - Date range
   - Specific app ID
   - Media source or partner
   - Other dimensions

2. **Ask Clarifying Questions:** Generates natural questions in the user's language
   - Short and simple questions
   - One question at a time
   - Provides context or examples when helpful

3. **Refine Question:** Once enough filters are provided, rephrases the original question to be more precise and specific

4. **Loop Control:** Enables the root agent to loop back to Agent #1 with the refined question

**Language Support:**
- Detects user's language from original question
- Always responds in the same language (Hebrew or English)
- Never switches language mid-conversation

---

### Agent #3 – Executor Agent (SQL Executor & Data Retriever)

**Responsibility:** Safely execute SQL queries on BigQuery and return raw results.

**Input:** Executor state containing:
- `user_question`: The original user question (for context)
- `sql`: The SQL query to execute

**Output:** Executor state containing:
- `user_question`: Original question
- `incoming`: Execution result with:
  - `status`: "success" or "error"
  - `description`: Result summary or error message
- `db_result`: Raw rows from BigQuery (list of dicts) or None

**Execution Process:**

1. **SQL Validation:**
   - Ensures SQL contains a SELECT statement
   - Rejects dangerous operations (DELETE, UPDATE, DROP, etc.)
   - Validates query structure

2. **BigQuery Execution:**
   - Creates BigQuery client with fixed project and EU location
   - Submits query with 120-second timeout
   - Retrieves all result rows
   - Handles connection errors gracefully

3. **Result Handling:**
   - Empty results: Status "success" with message "Query returned no rows"
   - Results present: Status "success" with row count
   - Execution errors: Status "error" with error details

4. **Caching Integration:**
   - Root agent checks cache BEFORE calling executor
   - If cache hit, executor is skipped entirely
   - If executor runs successfully, result is cached for future use
   - Cache TTL: 30 days (configurable)
   - Cache key: Normalized SQL query (whitespace/formatting insensitive)

**Safety Features:**
- Fixed BigQuery project and location to prevent cross-project access
- Query timeout to prevent long-running queries
- Result size limits via automatic LIMIT clause in Agent #1

---

### Agent #4 – Explanation Agent (Result Interpreter)

**Responsibility:** Transform raw SQL results into clear, human-readable explanations.

**Input:** Explanation input containing:
- `user_question`: Original user question
- `incoming`: Executor result (status and description)
- `db_result`: Raw result rows from database

**Output:** Explanation state containing:
- `status`: "success" or "error"
- `description`: Human-readable explanation of the results

**Explanation Strategies:**

1. **Single Number Results:**
   - If result is a count of clicks: "You have X clicks"
   - If result is zero: "No clicks were found for your request"

2. **Text with Context:**
   - Rephrases success descriptions naturally
   - Preserves factual information (dates, filters, counts)
   - Adds warmth and clarity

3. **Tabular Results (JSON list of rows):**
   - Converts raw JSON to Markdown table
   - Extracts column names from all rows
   - Limits display to first 20 rows if data is large
   - Adds summary title and formatting

4. **Error Handling:**
   - Translates technical error messages to user-friendly explanations
   - Suggests next steps when queries fail

**Language Support:**
- Always responds in the same language as the original question
- Detects language from user_question
- Never mixes languages in response

---

## 4. Workflow

### Overall Flow

```
User Question
    ↓
Agent #1 (Intent)
    ├─ Valid → proceed
    └─ Invalid → Agent #2
              ↓
        Agent #2 (Focus)
        Ask clarification
              ↓
        Refined question → back to Agent #1 [LOOP]
              ↓
        Valid → proceed
    ↓
Cache Lookup (in Root Agent)
    ├─ HIT → Use cached result
    └─ MISS → Agent #3
        ↓
Agent #3 (Executor)
Execute SQL on BigQuery
    ↓
Cache Store (in Root Agent)
    ↓
Agent #4 (Explanation)
Transform result to natural language
    ↓
Response to User
```

### Detailed Steps

#### Step 1: Intent Validation
1. User submits a free-text question
2. Agent #1 receives the question and extracts filters
3. Agent #1 validates the extracted information:
   - If valid → Generate SQL, proceed to Step 3
   - If invalid → Forward to Step 2

#### Step 2: Clarification Loop (Optional)
1. Agent #2 identifies missing or ambiguous filters
2. Agent #2 asks clarifying questions in the user's language
3. User provides more information
4. Agent #2 refines the question
5. Refined question goes back to Agent #1
6. Loop continues until question is valid

#### Step 3: Caching Check (Root Agent)
1. Root agent receives valid SQL from Agent #1
2. Root agent checks BigQuery cache for identical queries
3. If cache hit: Skip to Step 5 with cached result
4. If cache miss: Proceed to Step 4

#### Step 4: SQL Execution
1. Agent #3 receives SQL query
2. Agent #3 validates the query structure
3. Agent #3 executes query on BigQuery (EU location)
4. Agent #3 returns raw result rows or error

#### Step 5: Result Caching (Root Agent)
1. If execution succeeded, result is cached for 30 days
2. Future identical queries can use this cache

#### Step 6: Explanation & Response
1. Agent #4 receives raw results from executor
2. Agent #4 transforms results to natural language
3. Agent #4 returns friendly explanation
4. Response shown to user

---

### Anomaly Query Flow (Planned)
When the user asks for anomalies (e.g., "show me all the anomalies of 10-24-2025"):

1. Intent Agent classifies the request as anomaly-intent and extracts the date/range
2. The Root pipeline invokes an internal anomalies module (not a separate agent)
3. The anomalies module returns:
   - Graphs (visual artifacts) summarizing anomalies
   - A short, localized summary of the detected anomalies
4. The UI displays the graphs and the summary to the user
5. Technical specifics and detectors are being developed separately and will be added later

## 5. Data Model & Schemas

### Intent State (Agent #1 Output)
```python
{
  "question": str,              # Parsed user question
  "valid": bool,                # Is question valid?
  "sql": str,                   # Generated SQL (if valid)
  "awaiting_user_input": bool,  # Needs clarification?
  "reason": str,                # Why invalid (if applicable)
  "missing_fields": [str],      # List of missing filters
  "app_id": str | None,         # Extracted app ID
  "date_from": str | None,      # Date range start
  "date_to": str | None,        # Date range end
  "media_source": str | None,   # Extracted media source
}
```

### Focus State (Agent #2 Output)
```python
{
  "original_question": str,     # User's original question
  "awaiting_user_input": bool,  # Still needs input?
  "missing_fields": [str],      # Remaining missing filters
  "question_to_user": str,      # Clarifying question
  "refined_question": str | None # Rephrased question (if ready)
}
```

### Executor State (Agent #3 Output)
```python
{
  "user_question": str,         # Original question
  "incoming": {
    "status": "success" | "error",
    "description": str          # Summary or error details
  },
  "db_result": [dict] | None    # Raw result rows
}
```

### Explanation State (Agent #4 Output)
```python
{
  "status": "success" | "error",
  "description": str            # Human-readable explanation
}
```

---

## 6. Caching System

### Purpose
Reduce unnecessary BigQuery executions and improve response time for repeated queries.

### Implementation
- **Storage:** BigQuery table `practicode-2025.cache.query_results`
- **Key:** SHA256 hash of normalized SQL query
- **TTL:** 30 days (configurable via `BQ_CACHE_TTL_SECONDS`)
- **Enabled:** By default, configurable via `BQ_CACHE_ENABLED`

### Cache Workflow
1. Before executing a query, root agent checks if query is in cache
2. If cache entry exists and not expired, use cached result
3. If cache miss or expired, execute query normally
4. After successful execution, store result in cache
5. Automatic cleanup of expired entries

### SQL Normalization
- Whitespace and formatting differences don't affect cache lookups
- Semantically equivalent queries use the same cache entry
- Example: `SELECT * FROM table WHERE app_id = '1'` and `SELECT * FROM table WHERE app_id='1'` share the same cache


## 8. Error Handling & Fallbacks

### Intent Agent Fallbacks
1. If LLM-based parsing fails: Fall back to keyword extraction
2. If numeric filters are malformed: Attempt automatic fixing
3. If question is empty: Return "awaiting_user_input" with request for clarification

### Focus Agent Fallbacks
1. If state object is malformed: Normalize to AgentBInput schema
2. If LLM fails: Use rule-based clarification logic
3. If language detection fails: Default to English

### Executor Agent Fallbacks
1. If BigQuery client creation fails: Log error and return error state
2. If query timeout occurs: Return error message with retry suggestion
3. If network fails: Return error with connection details

### Explanation Agent Fallbacks
1. If result structure is unexpected: Attempt JSON parsing fallback
2. If LLM formatting fails: Return raw result summary
3. If language detection fails: Default to English explanation

### Root Agent Fallbacks
1. Try passing InvocationContext; if fails, fall back to dict
2. Try direct object instantiation; if fails, use mock objects
3. Attempt Pydantic model conversion; if fails, use raw dict

---

## 9. Technology Stack

- **Framework:** Google ADK (Agent Development Kit)
- **LLM:** Google GenAI API
- **Database:** BigQuery (Google Cloud)
- **Language:** Python 3.10+
- **Agent Orchestration:** Synchronous root agent with async ADK wrapper
- **Caching:** BigQuery-backed cache layer
- **Credentials:** Service account authentication (via GOOGLE_APPLICATION_CREDENTIALS)

---

## 10. Configuration & Environment

### Environment Variables
```
GOOGLE_API_KEY              # Optional: API key for GenAI
GOOGLE_APPLICATION_CREDENTIALS  # Service account JSON path
BQ_CACHE_TABLE_ID          # Cache table (default: practicode-2025.cache.query_results)
BQ_CACHE_TTL_SECONDS       # Cache TTL in seconds (default: 2592000 = 30 days)
BQ_CACHE_ENABLED           # Enable/disable caching (default: true)
```

### BigQuery Configuration
- **Project:** practicode-2025
- **Location:** EU (fixed for all queries)
- **Dataset:** Contains click analytics data from AppsFlyer

---

## 11. Future Enhancements

1. **Anomaly Detection:** Build specialized agent to identify unusual patterns in results
2. **Multi-Query Support:** Allow users to ask compound questions requiring multiple SQL queries
3. **Fraud Detection:** Integrate fraud-detection tools using query results
4. **Query History:** Store and retrieve past user queries for insights
5. **FAQ Mode:** Pre-built answers for common questions
6. **Custom Metrics:** Support user-defined metrics and KPIs
7. **Result Visualization:** Generate charts and visualizations for complex results
8. **Bulk Operations:** Support batch processing of multiple queries

---

## 12. Anomaly & Fraud Detection (Planned, Integrated)

This capability is planned but not implemented yet. It will be integrated as an internal module (not a separate agent) that the pipeline invokes when the user asks for anomalies or fraud insights.

### What it will do
- Handle queries like: "show me all the anomalies of 10-24-2025"
- Return graphs visualizing anomalies for the requested date/range
- Provide a short, localized summary of the anomalies

### How it fits the flow
- The Intent Agent will classify anomaly-intent and extract the relevant date/range
- The Root pipeline will call the internal anomalies module
- The UI will display the returned graphs and summary

### Status
- Under active development by a teammate; technical details and detectors will be added to this document later
