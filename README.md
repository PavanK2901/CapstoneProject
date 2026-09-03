# Agentic AI Intelligent Loan Approval System

A multi-agent AI system for automated loan application analysis and decision-making. Four domain-specific
agents are orchestrated with LangGraph, communicate with backend services over the real Model Context
Protocol (via `fastmcp`), and are fronted by a FastAPI gateway and a Streamlit UI.

## Business Objectives → Design Decisions

| Business objective (case study) | How this system addresses it |
|---|---|
| Automate loan application analysis | A single `POST /applications` call runs the full pipeline (profile → risk → decision → compliance) with no manual steps. |
| Improve decision speed and consistency | Deterministic rule-weight tables (`data/risk_rules.json`) compute a `rule_based_risk_score` baseline; the LLM refines it within a bounded margin instead of free-forming a score, so identical inputs land in a predictable range every time. |
| Explainable and auditable decisions | Every decision carries `risk_score`, `confidence_level`, `key_factors`, and a narrative `explanation` traceable to specific inputs (DTI, credit band, employment tenure). Decisions, notifications, and full application records are persisted to a SQLite audit trail (`common/db.py`, `data/audit.db`) that survives restarts. |
| Scalable, loosely-coupled microservices | Each backend capability (applicant data, risk rules, decision logging, notifications) is an independent MCP server on its own port, callable by any agent through a uniform `MCPToolCall.call_tool(url, tool_name, args)` interface. |
| Banking / compliance relevance | A dedicated Compliance & Action Orchestrator agent maps every classification to a concrete action (disbursement, closure, escalation) and a logged notification, rather than leaving that mapping implicit in the decision step. |

## Architecture Overview

```
Streamlit UI (Port 8501)
    │
    ├─→ FastAPI Gateway (Port 8000)
            │
            ├─→ LangGraph Orchestrator
                    │
        ┌───────────┼───────────┬─────────────┐
        ▼           ▼           ▼             ▼
    Applicant   Financial   Loan Decision  Compliance
    Profile     Risk        Agent           Orchestrator
    Agent       Agent       (calls Claude)  Agent
        │           │           │             │
        ▼           ▼           ▼             ▼
   MCP Server   MCP Server   MCP Server    MCP Server
   :9001/mcp    :9002/mcp    :9003/mcp     :9004/mcp
   (applicant   (risk        (decision     (notification,
    records)     rules)       audit log)    audit log)
```

Each MCP server is a real Model Context Protocol server (built with `fastmcp`, streamable-HTTP transport,
`tools/list`/`tools/call` JSON-RPC semantics at `/mcp`) — not a bespoke REST convention. Agents reach them
through `fastmcp.Client` via the shared `common/mcp_client.py` helper.

### Agent Responsibilities

1. **Applicant Profile Agent** (`agents/applicant_profile_agent.py`) - income stability score, employment risk, credit history summary, completeness flags. Correctly distinguishes "no internal history" (new applicant) from an actual data problem.
2. **Financial Risk Agent** (`agents/financial_risk_agent.py`) - debt-to-income ratio, credit score risk level, loan amount risk, anomaly detection, and a deterministic `rule_based_risk_score` aggregated from the weight tables in `data/risk_rules.json`.
3. **Loan Decision Agent** (`agents/loan_decision_agent.py`) - calls Claude (Anthropic Python SDK) to classify the application and explain the decision, anchored to the rule-based baseline score.
4. **Compliance & Action Orchestrator** (`agents/compliance_action_agent.py`) - maps the classification to an action, sends and logs a notification, tracks the case ID.

## Technology Stack

- **Streamlit** - the loan-application chat/form UI (`ui/app.py`)
- **FastAPI** - the public `/applications` gateway (`api/main.py`)
- **LangGraph** - orchestrates the 4 agents over a shared `TypedDict` state (`orchestration/`)
- **FastMCP** - real MCP servers/client for agent-to-service communication (`mcp_servers/`, `common/mcp_client.py`)
- **Anthropic Python SDK** - Claude API integration for the Loan Decision Agent (`common/llm_client.py`)
- **SQLite** - persistent audit trail for decisions, notifications, and full application records (`common/db.py`)
- **pytest** - offline unit/integration test suite (`tests/`)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
# for running the test suite too:
pip install -r requirements-dev.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Run All Services

**Terminal 1: Start backend services**
```bash
python run_all.py
```

This launches:
- 4 MCP servers (ports 9001-9004)
- FastAPI microservice (port 8000)

**Terminal 2: Start Streamlit UI**
```bash
streamlit run ui/app.py
```

## Quick Test

### Via cURL (the public FastAPI gateway)
```bash
curl -X POST http://localhost:8000/applications \
  -H "Content-Type: application/json" \
  -d '{
    "applicant_id": "APP001",
    "age": 32,
    "income": 85000,
    "employment_type": "salaried",
    "credit_score": 720,
    "loan_amount": 250000,
    "tenure_months": 360,
    "existing_liabilities": 500,
    "location": "New York"
  }'
```

### Via Streamlit UI
1. Open http://localhost:8501 in your browser
2. Fill in the loan application form
3. Submit and see the AI-powered decision with explanation

See `TESTING_GUIDE.md` for MCP-level tool testing and the automated test suite.

## ⚠️ Preventing "500 Server Error" on First Submission

**Important:** The 5 backend services (FastAPI + 4 MCP servers) require **5-15 seconds** to fully initialize after `python run_all.py` starts. Submitting an application before this window closes causes a 500 error because MCP service calls timeout.

### ✅ Guaranteed Safe Startup

**Use the automatic startup script (recommended):**
```bash
bash startup_and_wait.sh
```

This script:
1. Cleans old data
2. Stops any existing services
3. Starts all services
4. Waits until all 5 are healthy
5. Confirms when you can submit (no manual waiting required)

**OR, manual verification:**

After `python run_all.py`, wait for this output:
```
✅ All MCP services are ready. FastAPI is accepting requests.
```

Then, in a **separate terminal**, run:
```bash
bash health_check.sh
```

Expected output (don't proceed until you see all 5 ✅):
```
✅ Port 9001 (Applicant DB): healthy
✅ Port 9002 (Risk Rules): healthy
✅ Port 9003 (Decision Synthesis): healthy
✅ Port 9004 (Notification): healthy
✅ Port 8000 (FastAPI): healthy
All services ready!
```

### 🔧 If You Get "503 Service Unavailable"

This is **intentional** — it means services are still starting. Wait 5-10 seconds and retry:
```bash
curl -X POST http://localhost:8000/applications \
  -H "Content-Type: application/json" \
  -d '{...your application JSON...}'
```

The API will return 503 until all services are ready, then automatically accept requests.

## Project Structure

- `common/` - shared utilities: config, MCP client (`fastmcp.Client` wrapper), LLM client, SQLite audit trail (`db.py`)
- `data/` - mock applicant data, risk rules, and the generated `audit.db` SQLite file
- `mcp_servers/` - 4 real MCP servers (FastMCP, streamable-HTTP) for agent communication
- `agents/` - 4 domain-specific agents
- `orchestration/` - LangGraph state and graph definition
- `api/` - FastAPI schemas and endpoints
- `ui/` - Streamlit UI
- `tests/` - offline pytest suite (no live services or API key required)

## Decision Classification

The system returns decisions in 3 categories:

- **APPROVED**: Low-risk applications with strong financial profile
- **REJECTED**: High-risk applications or credit score issues
- **REQUIRES_MANUAL_REVIEW**: Borderline cases, or cases where the LLM call itself fails, needing underwriter assessment

Each decision includes:
- Risk score (0-100) — anchored to a deterministic `rule_based_risk_score` baseline (see `financial_risk`), refined by Claude within a bounded margin
- Confidence level (0-100%)
- Key decision factors
- Detailed explanation from Claude
- A persisted audit record (case, decision, notification) retrievable via `GET /applications/{case_id}` even after a restart

# NewBeginingProject