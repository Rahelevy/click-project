# 📊 Clicks Project - Multi-Agent Analytics System

A **multi-agent AI system** that transforms natural language questions about AppsFlyer click data into intelligent SQL queries, executes them on BigQuery, and provides human-readable explanations with automatic visualizations.

---

## 🎯 Overview

**What is Clicks Project?**

Clicks Project is a sophisticated analytics platform that bridges the gap between non-technical users and complex data. Instead of writing SQL queries, users can simply ask questions in natural language (English or Hebrew), and the system automatically:

1. ✅ Understands and validates the question
2. ✅ Generates optimized SQL with intelligent table routing
3. ✅ Executes queries on BigQuery with intelligent caching
4. ✅ Detects patterns and anomalies automatically
5. ✅ Returns results as clear explanations and interactive charts
6. ✅ Handles multi-turn conversations with context preservation

**Key Use Cases:**
- Analyze ad campaign performance on AppsFlyer
- Identify traffic anomalies in real-time
- Track clicks by media source, app, or geography
- Generate hourly trend reports
- Create interactive dashboards from natural language queries

---

## 🏗️ Architecture

The system is built on a **multi-agent architecture** where specialized agents collaborate:

```
User Question 
    ↓
1️⃣  Intent Agent (Parse & Generate SQL)
    ↓
    ├─→ Anomaly Query? → Anomaly Agent (Pattern Detection)
    └─→ Regular Query → 2️⃣ Focus Agent (Clarification)
    ↓
3️⃣  Executor Agent (BigQuery Execution + Caching)
    ↓
4️⃣  Explanation Agent (Results → Charts + Explanations)
    ↓
React UI (Streaming responses via SSE)
```

### 🤖 Agent Breakdown

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Intent Agent** | Parses natural language, generates SQL | User question | Validated SQL query |
| **Focus Agent** | Asks clarifying questions | Incomplete question | Refined question |
| **Executor Agent** | Runs SQL on BigQuery | SQL query | Query results |
| **Explanation Agent** | Formats results, generates charts | Query results | Natural language explanation + charts |
| **Anomaly Agent** | Detects unusual patterns | Anomaly-focused question | Z-score analysis + visualizations |

### 🗄️ Technology Stack

**Backend:**
- Python 3.x
- Google ADK (Agent Development Kit)
- BigQuery for analytics
- SQLite for local caching

**Frontend:**
- React 19+
- Vite (build tool)
- Tailwind CSS (styling)
- Server-Sent Events (SSE) for real-time streaming

**Infrastructure:**
- BigQuery (Data warehouse)
- Google Cloud Storage (Configuration)
- Optimized partitioned tables for performance

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Google Cloud credentials (BigQuery access)

### Backend Setup

```bash
# Navigate to backend directory
cd main_agent

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r ../requirements.txt

# Set up Google Cloud credentials
export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Run the ADK web server
adk web --log_level debug
```

The backend will start on `http://localhost:3001`

### Frontend Setup

```bash
# Navigate to frontend directory
cd multi-agent-ui

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will start on `http://localhost:5173`

---

## 📁 Project Structure

```
ClicksProject/
├── main_agent/                      # Backend (Python)
│   ├── agent.py                    # Root agent orchestrator
│   ├── table_router.py             # Intelligent table routing
│   ├── bq.py                       # BigQuery client
│   ├── config.py                   # Configuration
│   ├── cache/
│   │   └── bq_cache.py             # BigQuery caching system
│   └── sub_agents/                 # Specialized agents
│       ├── a_intent_agent/         # Question parsing
│       ├── b_focus_agent/          # Clarification handler
│       ├── c_executor_agent/       # SQL executor
│       ├── d_explanation_agent/    # Results formatter
│       └── anomaly_agent/          # Anomaly detection
│
├── multi-agent-ui/                  # Frontend (React)
│   ├── src/
│   │   ├── components/
│   │   │   └── renderers/          # Chart & Table renderers
│   │   ├── lib/
│   │   │   ├── adkClient.js        # Backend API client
│   │   │   └── mockApi.js          # Mock data for testing
│   │   └── App.jsx                 # Main app component
│   └── vite.config.js              # Vite configuration
│
├── SPECIFICATION.md                 # Detailed system specification
├── ARCHITECTURE_SIMPLE_UML.md       # Architecture diagrams
├── WORKFLOW_DIAGRAM.md              # Process flow diagrams
└── requirements.txt                 # Python dependencies
```

---

## 💡 How It Works: Example Workflow

### Example Question
> "What's the hourly click trend for app_id_123 in the last 7 days by media source?"

### Step-by-Step Processing

1. **Intent Agent** 
   - Detects: Query type = "anomaly/trend"
   - Extracts: app_id=123, time_range=7d
   - Generates SQL with optimal table routing
   - Detects language and format preferences

2. **Anomaly Agent** (if trend detected)
   - Queries hourly aggregated data
   - Calculates Z-scores for anomaly detection
   - Identifies unusual spikes or drops

3. **Executor Agent**
   - Checks BigQuery cache (30-day TTL)
   - If not cached: Executes SQL on BigQuery
   - If cached: Returns cached results (faster)
   - Stores result in cache table

4. **Explanation Agent**
   - Formats raw data into readable insights
   - Detects chart-suitable data
   - Generates time-series visualization
   - Returns HTML with embedded chart

5. **React UI**
   - Streams results via SSE
   - Renders interactive chart
   - Displays human-readable explanation
   - Preserves conversation history

---

## 🔑 Key Features

### 🌍 Bilingual Support
- Automatic language detection (English & Hebrew)
- RTL (Right-to-Left) support for Hebrew text
- Locale-aware formatting and explanations

### ⚡ Performance Optimization
- **Intelligent Table Routing**: Automatically selects optimized partitioned tables
  - `encoded_clicks_by_app` for app-focused queries
  - `encoded_clicks_by_media` for media source queries
  - `encoded_clicks_by_partner` for partner analysis
  - And more...
- **Query Caching**: BigQuery-backed cache with 30-day TTL
- **SQL Normalization**: Whitespace/case-insensitive query matching

### 📈 Automatic Chart Generation
- Detects chart-suitable data automatically
- Generates time-series, bar, and scatter plots
- Integrates Matplotlib for rendering
- Renders as interactive HTML

### 🚨 Anomaly Detection
- Hourly trend analysis with Z-score calculation
- Media source-level anomaly identification
- Automatic visualization of anomalies
- Real-time pattern detection

### 💬 Multi-Turn Conversations
- Preserves conversation context
- Combines previous questions with new inputs
- Reduces user back-and-forth
- Session-level state management

### 🔐 Safety & Validation
- Question validation before SQL generation
- BigQuery EU data residency enforcement
- Automatic query limiting to prevent excessive data retrieval
- Safe SQL injection prevention

---

## 🛠️ Configuration

### Environment Variables

Create a `.env` file in `main_agent/`:

```bash
# BigQuery Configuration
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
BIGQUERY_PROJECT_ID=your-project-id
BIGQUERY_DATASET_ID=your-dataset-id

# Cache Configuration
CACHE_TABLE_ID=cache.query_results
CACHE_TTL_DAYS=30

# Language Support
SUPPORTED_LANGUAGES=en,he
DEFAULT_LANGUAGE=en

# API Configuration
API_PORT=3001
UI_ORIGIN=http://localhost:5173
```

### BigQuery Tables

The system expects these optimized tables:
- `encoded_clicks_partitioned` (default)
- `encoded_clicks_by_app` (app-focused)
- `encoded_clicks_by_media` (media source)
- `encoded_clicks_by_partner` (partner)
- `encoded_clicks_by_site` (site)
- `encoded_clicks_by_retargeting` (retargeting)
- `final_anomalies` (anomaly detection)
- `cache.query_results` (caching)

See [main_agent/OPTIMIZED_TABLES_README.md](main_agent/OPTIMIZED_TABLES_README.md) for table schemas.

---

## 📊 Data Flow

```
External Input (User)
    ↓
React UI (multi-agent-ui/)
    ↓
Backend API (main_agent/)
    ↓
Intent Agent (Parse question into SQL)
    ↓
BigQuery Cache (Check if result exists)
    ↓
BigQuery (Execute query if not cached)
    ↓
Executor Agent (Process results)
    ↓
Explanation Agent (Format + visualize)
    ↓
SSE Stream (Real-time response)
    ↓
React UI (Display results)
    ↓
User (Final output)
```

---

## 🧪 Testing

Run the test suite:

```bash
cd main_agent

# Run all tests
pytest tests/

# Run specific test
pytest tests/test_intent_agent.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

Available tests:
- `test_intent_agent.py` - Query parsing and validation
- `test_focus_agent_run.py` - Clarification handling
- `test_executor_agent.py` - SQL execution
- `test_explainer_agent.py` - Result formatting
- `test_bq_cache.py` - Caching system
- `test_llm_anomaly.py` - Anomaly detection
- `test_pipeline_all.py` - End-to-end pipeline
- And more...

---

## 🐛 Debugging

### Enable Debug Logging

```bash
# Backend debug mode
adk web --log_level debug

# Frontend debug mode
npm run dev
```

### Check BigQuery Cache

```python
from main_agent.cache.bq_cache import BQCache

cache = BQCache()
# View cache entries
cache.get_cache_stats()
```

### View Agent Trace

The system logs detailed agent execution traces. Check logs for:
- `debug_trace` - Full pipeline execution details
- Agent-specific logs for each step
- SQL queries generated
- BigQuery results

---

## 📖 Documentation

- [SPECIFICATION.md](SPECIFICATION.md) - Detailed system specification
- [ARCHITECTURE_SIMPLE_UML.md](ARCHITECTURE_SIMPLE_UML.md) - System architecture diagrams
- [WORKFLOW_DIAGRAM.md](WORKFLOW_DIAGRAM.md) - Process flow diagrams
- [main_agent/README.md](main_agent/README.md) - Backend-specific documentation
- [multi-agent-ui/README.md](multi-agent-ui/README.md) - Frontend-specific documentation
- [main_agent/OPTIMIZED_TABLES_README.md](main_agent/OPTIMIZED_TABLES_README.md) - BigQuery table schemas

---

## 🚀 Deployment

### Production Build

**Backend:**
```bash
cd main_agent
adk deploy --platform cloud-run
```

**Frontend:**
```bash
cd multi-agent-ui
npm run build
# Output in dist/ directory
# Deploy to hosting platform (Vercel, Netlify, Firebase, etc.)
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Run tests: `pytest tests/`
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

**Coding Standards:**
- Follow PEP 8 for Python
- Use type hints in all functions
- Write docstrings for all modules/functions
- Add unit tests for new features
- Update documentation accordingly


## ✉️ Contact & Support

**Project Maintainer:** Rahel Levy
**Issues:** For bug reports and feature requests, please open an issue on GitHub.


## 📊 Project Statistics

- **Languages:** Python, JavaScript, SQL
- **Agents:** 5 specialized agents + 1 root orchestrator
- **Supported Languages:** English, Hebrew
- **API:** RESTful with SSE streaming
- **Database:** BigQuery (Google Cloud)

---

**Last Updated:** April 2026
**Version:** 1.0.0

For detailed technical information, refer to the [SPECIFICATION.md](SPECIFICATION.md) and [ARCHITECTURE_SIMPLE_UML.md](ARCHITECTURE_SIMPLE_UML.md) documents.
