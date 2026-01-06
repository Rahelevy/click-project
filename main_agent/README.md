# Main Agent - Multi-Agent Analytics System

## Overview

This is the backend implementation of a multi-agent system for analyzing AppsFlyer click data stored in BigQuery. The system uses Google's ADK (Agent Development Kit) to orchestrate multiple specialized agents that work together to process natural language queries, generate SQL, execute queries, and provide human-friendly explanations.

## Quick Start

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r ../requirements.txt

# Set up credentials
export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Run the server
adk web --log_level debug
```

## Architecture

### Agent Pipeline

```
User Question → Intent Agent → Focus Agent (if needed) → Executor Agent → Explanation Agent → Response
                       ↓
                Anomaly Agent (if anomaly query detected)
```

### Core Components

1. **RootAgent** (`agent.py`) - Orchestrator
   - Manages multi-turn conversations
   - Routes between agents
   - Handles caching and error recovery
   - Maintains debug traces

2. **IntentAgent** (`sub_agents/a_intent_agent/`) - Question Parser
   - Validates and parses natural language questions
   - Extracts filters (app_id, dates, media_source, etc.)
   - Generates SQL with intelligent table routing
   - Detects anomaly queries (`query_type="anomaly"`)
   - Supports English and Hebrew

3. **FocusAgent** (`sub_agents/b_focus_agent/`) - Clarification Handler
   - Asks clarifying questions when information is missing
   - Refines vague queries
   - Loops until enough information is gathered
   - Language-aware responses

4. **ExecutorAgent** (`sub_agents/c_executor_agent/`) - SQL Executor
   - Safely executes SQL on BigQuery (EU location)
   - Handles aggregations
   - Manages connection errors
   - Returns structured results

5. **ExplainerAgent** (`sub_agents/d_explanation_agent/`) - Response Formatter
   - Converts raw SQL results to natural language
   - Detects chart requests and generates visualizations
   - Creates formatted tables
   - Identifies "top N" findings
   - Language detection and bilingual support

6. **AnomalyAgent** (`sub_agents/anomaly_agent/`) - Anomaly Detector ✅
   - Fully integrated into pipeline
   - Queries `final_anomalies` table
   - Generates hourly trend visualizations
   - Media source analysis
   - Z-score based detection

### Supporting Modules

#### Table Router (`table_router.py`)
Intelligent routing to optimized partitioned tables:
- `encoded_clicks_partitioned` - Default balanced table
- `encoded_clicks_by_app` - Optimized for app-focused queries
- `encoded_clicks_by_media` - Optimized for media source queries
- `encoded_clicks_by_partner` - Optimized for partner queries
- `encoded_clicks_by_site` - Optimized for site queries
- `encoded_clicks_by_retargeting` - Optimized for retargeting analysis

#### Cache System (`cache/bq_cache.py`)
BigQuery-backed caching for query results:
- Table: `practicode-2025.cache.query_results`
- TTL: 30 days (configurable)
- SQL normalization (whitespace/case insensitive)
- SHA256 hash keys
- MERGE operation for cache writes

#### Chart Generator (`sub_agents/d_explanation_agent/chart_generator.py`)
Automatic visualization generation:
- Matplotlib backend (PNG base64 export)
- Smart column detection based on user question
- Support for bar, line, and pie charts
- Time-series optimization
- "Top N" query detection

## Example Queries

**Regular Queries:**
- "How many clicks for app_id_20 on 2025-10-24?"
- "כמה קליקים היו למקור פייסבוק אתמול?"
- "Show me top media sources for app_id_123 this week"

**Chart Queries:**
- "Show me a chart of clicks by media source"
- "הראה לי גרף של קליקים לפי שעה"

**Anomaly Queries:**
- "Show me anomalies"
- "What anomalies did facebook have?"
- "הראה אנומליות"

## Testing

```bash
# Run all tests
python -m pytest tests/

# Test specific agent
python tests/test_intent_agent.py
python tests/test_executor_agent.py
```

## Key Features

✅ Multi-turn conversations
✅ Intelligent table routing
✅ Query result caching (30 days)
✅ Automatic chart generation
✅ Anomaly detection & visualization
✅ Bilingual support (Hebrew/English)
✅ Debug tracing

## Environment Variables

```env
GOOGLE_API_KEY=your_api_key_here  # Optional
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json  # Required
BQ_CACHE_TABLE_ID=practicode-2025.cache.query_results
BQ_CACHE_TTL_SECONDS=2592000  # 30 days
BQ_CACHE_ENABLED=true
```

## Documentation

See main project documentation:
- [SPECIFICATION.md](../SPECIFICATION.md) - Detailed system specification
- [ARCHITECTURE_SIMPLE_UML.md](../ARCHITECTURE_SIMPLE_UML.md) - System architecture
- [WORKFLOW_DIAGRAM.md](../WORKFLOW_DIAGRAM.md) - Process workflow

