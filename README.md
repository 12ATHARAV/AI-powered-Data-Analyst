# AI-Powered Data Analyst

[![CI/CD Pipeline](https://github.com/12ATHARAV/AI-powered-Data-Analyst/actions/workflows/ci.yml/badge.svg)](https://github.com/12ATHARAV/AI-powered-Data-Analyst/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agents-FF6F00?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=black)](https://react.dev)

An AI-powered data analysis tool that lets users upload CSV files and interact with their data using plain English. It automatically cleans messy data, generates SQL queries, creates interactive charts, detects statistical outliers, and explains its findings in a modern web dashboard.

---

## How It Works

```mermaid
flowchart LR
    User["User Query / CSV Upload"] --> Frontend["React Frontend (Vite)"]
    Frontend --> Nginx["Nginx Reverse Proxy"]
    Nginx --> Backend["FastAPI Backend"]
    
    subgraph Storage["Storage Layer"]
        DB[("SQLite (WAL Mode)\nSession-Isolated")]
    end
    
    subgraph Agents["LangGraph Agent Workflow"]
        Supervisor["1. Supervisor\n(Plans analysis)"]
        SQL["2. SQL Coder\n(Queries SQLite)"]
        Anomaly["3. Anomaly Detector\n(Flags IQR Outliers)"]
        Viz["4. Chart Designer\n(Formats Recharts)"]
        Synthesizer["5. Synthesizer\n(Final Answer)"]
        
        Supervisor --> SQL & Anomaly & Viz --> Synthesizer
    end
    
    subgraph LLM["LLM Engine"]
        Primary["Primary: NVIDIA Nemotron"]
        Fallback["Fallback: Groq"]
    end
    
    Backend --> Storage
    Backend --> Agents
    Supervisor -.-> LLM
    SQL <--> DB
    Anomaly <--> DB
    Synthesizer --> Frontend
```

### The 5-Step Agent Workflow
1. **Supervisor**: Analyzes the user's question, reviews the table schemas, and plans which agents are needed.
2. **SQL Agent**: Formulates safe `SELECT` queries, joins related tables, and runs them against the SQLite database.
3. **Anomaly Hunter**: Runs interquartile range (IQR) and Z-score checks on numerical columns to identify and explain statistical outliers.
4. **Visualization Designer**: Translates the query result into the best chart format (Bar, Line, Pie, or Scatter).
5. **Executive Synthesizer**: Reviews the data and writes a clear, structured summary answering the user's question.

---

## Key Features

* **Natural Language Chat**: Ask everyday business questions and get clear answers with supporting numbers and charts.
* **Automated Data Cleaning**: Automatically handles corrupted characters (mojibake), inconsistent casing (`east` vs `East`), currency symbols (`$1,200` $\rightarrow$ `1200`), and missing values with a full audit log.
* **Multi-Table Analysis**: Detects common columns between multiple CSVs (e.g., `customer_id` across `sales` and `customers`) and performs automatic SQL `JOIN`s.
* **Executive Dashboard**: Pre-built dashboard showing key metrics, revenue trends, product performance, and anomalies.
* **Multi-Tenant Session Isolation**: Each visitor gets their own isolated SQLite session database (`storage/sessions/{session_id}.db`). Multiple people can test the app simultaneously without seeing or overwriting each other's data.
* **Real-time Streaming & Live Logs**: Uses Server-Sent Events (SSE) so users can watch the agent's step-by-step thinking and SQL execution live.
* **Resilient Dual-LLM Support**: Built with NVIDIA Nemotron as the primary model and automatic fallback to Groq if rate limits or network issues occur.

---

## Example Questions to Try

| Question | What It Shows | Output |
| :--- | :--- | :--- |
| **"Which region generated the highest revenue?"** | Grouping & aggregation | Bar chart of regional revenue + SQL breakdown |
| **"Show monthly sales trends."** | Date parsing & time series | Line chart of revenue over time |
| **"Which products are underperforming?"** | Multi-table join (`sales` + `products`) | Low-performing product table + revenue ranking |
| **"What are the top five customers?"** | Multi-table join (`sales` + `customers`) | Ranked bar chart of top spenders |
| **"Generate SQL for this analysis."** | SQL query generation | Formatted SQL query with 1-click copy |
| **"Detect anomalies in the dataset."** | Statistical outlier detection | Table of outlier rows with plain-English reasons |

---

## Quickstart

### Option 1: Running with Docker (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/12ATHARAV/AI-powered-Data-Analyst.git
   cd AI-powered-Data-Analyst
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   Add your `NVIDIA_API_KEY` and/or `GROQ_API_KEY` in `.env` (the application also works with fallback mock data if no keys are provided).

3. **Start the containers:**
   ```bash
   docker compose up -d --build
   ```

4. **Open in browser:**
   * **Frontend UI**: [http://localhost:5173](http://localhost:5173)
   * **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

To stop the containers:
```bash
docker compose down
```

---

### Option 2: Running Locally

#### 1. Backend Setup
```bash
# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt pytest pytest-asyncio

# Start FastAPI server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Frontend Setup
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173).

---

## Testing

Run the automated test suite covering CSV ingestion, SQL safety guardrails, anomaly detection, data cleaning, and session isolation:
```bash
python -m pytest backend/tests -v
```

Run frontend linter and production build check:
```bash
cd frontend
npm run lint
npm run build
```

---

## Project Structure

```text
AI-powered-Data-Analyst/
├── .github/workflows/ci.yml       # Automated CI/CD test and build pipeline
├── backend/
│   ├── app/
│   │   ├── agents/                # LangGraph multi-agent team (supervisor, sql, anomaly, viz, synthesizer)
│   │   ├── api/                   # FastAPI route handlers and session middleware
│   │   ├── db/                    # SQLite engine with WAL mode and session routing
│   │   ├── eda/                   # Statistical profiling and anomaly detection
│   │   ├── ingest/                # CSV parsing, validation, and auto-cleaning
│   │   ├── llm/                   # Dual-LLM client (NVIDIA + Groq fallback)
│   │   ├── config.py              # Application settings
│   │   └── main.py                # App entrypoint
│   ├── tests/                     # Automated pytest suite (14 tests)
│   ├── Dockerfile                 # Backend Docker configuration
│   └── requirements.txt           # Python dependencies
├── data/samples/                  # Sample CSVs (customers.csv, products.csv, sales.csv)
├── frontend/
│   ├── src/                       # React components, dashboard, chat, and chart renderers
│   ├── Dockerfile                 # Frontend multi-stage Docker configuration
│   ├── nginx.conf                 # Nginx proxy and SSE configuration
│   └── package.json
├── storage/                       # Local SQLite database and uploads
├── docker-compose.yml             # Full-stack Docker orchestration
└── README.md
```

---

## Key Technical Decisions

* **SQLite with WAL Mode**: Kept local and lightweight with zero external database dependencies. Enabled Write-Ahead Logging (WAL) and a 15-second busy timeout so multiple read/write queries can run concurrently without locking.
* **Session Database Isolation**: Each user gets their own session-scoped SQLite database. When a visitor lands on the site, their session is pre-loaded with sample tables so they can immediately test the app without manual setup.
* **Query Safety**: All SQL generation is restricted to read-only `SELECT` statements. Data modification commands (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`) are blocked by code guardrails.
* **Data Privacy**: Raw dataset rows are never sent in bulk to the LLM. Only table schemas and column summaries are passed to generate queries; query execution happens locally, and only the top preview rows are sent to summarize the findings.
