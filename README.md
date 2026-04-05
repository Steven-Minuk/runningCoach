# AI Running Coach

A personal running data platform that combines an Azure cloud ETL pipeline with an AI coaching interface powered by GPT-4o and your actual GPS training data.

## Overview

Upload a GPX file from your GPS watch → the pipeline automatically processes it through a medallion architecture → your AI coach can immediately analyse your run with per-kilometre pace breakdowns, elevation profiles, split analysis, and personalised recommendations backed by running science literature.

## Architecture

```
GPX Upload (Garmin / manual)
    ↓
Azure Blob Storage (bronze-gpx)
    ↓
Azure Event Grid (gpx-blob-created trigger)
    ↓
Azure Function (func-runningcoach-dev)
    ├── Bronze  → gpx_parser.py       (parse raw GPX)
    ├── Silver  → metrics.py          (compute pace, distance, elevation)
    │             → Azure SQL track_points (~400 rows per run)
    │             → Azure Blob silver-track-points (JSON)
    └── Gold    → sql_loader.py       (run summary)
                  → Azure SQL runs (1 row per run)
                  → Azure Blob gold-run-summary (JSON)
    ↓
AI Coach (Streamlit + LangGraph + GPT-4o)
    ├── db_reader.py   (SQL tools for agent)
    ├── rag.py         (FAISS vectorstore over 8 running science PDFs)
    └── agent.py       (LangGraph ReAct agent)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Cloud | Azure Functions (Flex Consumption), Azure Blob Storage, Azure SQL, Azure Event Grid |
| ETL | Python 3.11, pyodbc, SQLAlchemy |
| AI Agent | LangGraph, LangChain, GPT-4o (OpenAI), FAISS RAG |
| UI | Streamlit |
| CI/CD | GitHub Actions, Azure CLI |
| Testing | pytest (65 unit tests) |

## Project Structure

```
runningCoach/
├── .github/workflows/deploy.yml   # CI/CD pipeline
├── ai_coach/
│   ├── agent.py                   # LangGraph + GPT-4o ReAct agent
│   ├── app.py                     # Streamlit UI with session management
│   ├── db_reader.py               # LangChain tools for SQL queries
│   ├── rag.py                     # FAISS vectorstore over running science PDFs
│   ├── docs/                      # Running science PDFs (gitignored)
│   └── vectorstore/               # FAISS index (gitignored)
├── migrations/
│   ├── V1__create_runs_table.sql
│   └── V2__create_track_points_table.sql
├── scripts/
│   └── backfill_track_points.py
├── tests/
│   ├── test_data_quality.py       # 22 tests
│   ├── test_gpx_parser.py         # 17 tests
│   └── test_metrics.py            # 27 tests
├── data_quality.py
├── function_app.py                # Azure Function entry point
├── gpx_parser.py
├── metrics.py
├── sql_loader.py
└── requirements.txt
```

## SQL Schema

**runs table** (gold layer — 1 row per run)
```sql
run_id, source_file_name, activity_name, start_time, end_time,
duration_seconds, total_distance_km, total_distance_miles,
avg_speed_kmh, avg_pace_min_per_km, elevation_gain_m,
elevation_loss_m, calories_est, point_count
```

**track_points table** (silver layer — ~400 rows per run)
```sql
point_id, run_id, source_file_name, point_index,
latitude, longitude, elevation_m, point_time,
segment_distance_m, cumulative_distance_m,
segment_seconds, instant_speed_kmh
```

## AI Coach Features

The agent has access to 5 tools that query your actual training data:

- `get_recent_runs` — overview of recent runs with run_id, distance, pace
- `get_training_stats` — total volume, weekly mileage, fitness benchmarks
- `get_run_pace_profile` — per-km pace breakdown with split analysis
- `get_elevation_profile` — elevation and grade per 500m segment
- `get_best_efforts` — fastest efforts at 1k, 5k, 10k, half-marathon

Combined with FAISS RAG over running science PDFs (Jack Daniels' Running Formula and others), the agent gives personalised, data-driven coaching advice.

## Setup

### Prerequisites

- Python 3.11
- Azure subscription
- OpenAI API key
- ODBC Driver 18 for SQL Server

### Environment Variables

Create a `.env` file in the project root:

```env
# Azure SQL
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database
AZURE_SQL_USER=your-username
AZURE_SQL_PASSWORD=your-password

# Azure Storage
AzureWebJobsStorage=DefaultEndpointsProtocol=https;AccountName=...
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...

# OpenAI
OPENAI_API_KEY=sk-...

# Optional
RUNNER_WEIGHT_LB=165.0
```

### Installation

```bash
# Clone the repo
git clone https://github.com/Steven-Minuk/runningCoach.git
cd runningCoach

# Create virtual environment with Python 3.11
py -3.11 -m venv .venv

# Activate
source .venv/bin/activate        # Mac
.venv\Scripts\Activate.ps1       # Windows

# Install dependencies
pip install -r requirements.txt
pip install streamlit langchain langchain-openai langgraph \
    langchain-community faiss-cpu pypdf pandas python-dotenv sqlalchemy
```

### Build the RAG vectorstore (one-time)

```bash
python -c "
from ai_coach.rag import build_vectorstore
import glob
build_vectorstore(glob.glob('ai_coach/docs/*.pdf'))
"
```

### Run the AI Coach

```bash
streamlit run ai_coach/app.py
```

Opens at `http://localhost:8501`

### Run Tests

```bash
pytest tests/ -v
```

## CI/CD

Every push to `main` triggers GitHub Actions:
1. Runs all 65 unit tests
2. Deploys to Azure Functions via Azure CLI zip deploy
3. Restarts the function app to register the updated function

Required GitHub secrets: `AZURE_CREDENTIALS`

## Data Pipeline

New runs are processed automatically:

1. Upload a `.gpx` file to the `bronze-gpx` blob container
2. Event Grid fires `gpx-blob-created`
3. Azure Function parses the GPX, computes metrics, validates data quality
4. Silver data (track points) inserted into `track_points` SQL table
5. Gold data (run summary) inserted into `runs` SQL table
6. AI coach can immediately query the new run

## Conversation History

The Streamlit app saves every coaching session to Azure Blob Storage (`conversations/` container) as JSON. Sessions are listed in the sidebar and can be resumed at any time from any machine with the same Azure Storage connection.

## Running Data

Currently tracking 176 runs from Austin, Texas and Gyeongju, Korea with ~70,000 track points in Azure SQL.
