# Testing Guide - Multi-Agent Loan Approval System

## Pre-Requisites

1. **Python 3.10+**: Required for all components
2. **ANTHROPIC_API_KEY**: Get from https://console.anthropic.com/
3. **Dependencies**: Run `pip install -r requirements.txt`

## Quick Start

### 1. Setup Environment
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 2. Terminal 1: Start All Services
```bash
python run_all.py
```

Expected output:
```
🚀 Starting Applicant DB on port 9001...
🚀 Starting Risk Rules on port 9002...
🚀 Starting Decision Synthesis on port 9003...
🚀 Starting Notification on port 9004...
🚀 Starting FastAPI on port 8000...

✅ All services started successfully!
```

Wait until you see all health check confirmations.

### 3. Terminal 2: Start Streamlit UI
```bash
streamlit run ui/app.py
```

Opens browser at http://localhost:8501

## Test Cases

### Test 1: Good Candidate (Should Approve)
- **Applicant ID**: TEST_GOOD_001
- **Age**: 40
- **Income**: $150,000
- **Employment**: salaried
- **Credit Score**: 780
- **Loan Amount**: $200,000
- **Tenure**: 360 months
- **Liabilities**: $500
- **Location**: New York

**Expected**: APPROVED with high confidence

### Test 2: Poor Candidate (Should Reject)
- **Applicant ID**: TEST_BAD_001
- **Age**: 25
- **Income**: $30,000
- **Employment**: unemployed
- **Credit Score**: 520
- **Loan Amount**: $100,000
- **Tenure**: 360 months
- **Liabilities**: $2,000
- **Location**: Texas

**Expected**: REJECTED with high confidence

### Test 3: Borderline Case (Should Review)
- **Applicant ID**: TEST_REVIEW_001
- **Age**: 35
- **Income**: $65,000
- **Employment**: self_employed
- **Credit Score**: 680
- **Loan Amount**: $250,000
- **Tenure**: 300 months
- **Liabilities**: $1,500
- **Location**: California

**Expected**: REQUIRES_MANUAL_REVIEW with medium confidence

## CLI Testing

### Test via cURL
```bash
curl -X POST http://localhost:8000/applications \
  -H "Content-Type: application/json" \
  -d '{
    "applicant_id": "CURL_TEST_001",
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

### Health Checks
```bash
# Check FastAPI
curl http://localhost:8000/health

# Check Applicant DB MCP
curl http://localhost:9001/health

# Check Risk Rules MCP
curl http://localhost:9002/health

# Check Decision Synthesis MCP
curl http://localhost:9003/health

# Check Notification MCP
curl http://localhost:9004/health
```

## MCP Server Testing

These are real MCP servers (streamable-HTTP transport via `fastmcp`), not a plain REST endpoint, so a
one-line curl won't do a full tool call. Use `fastmcp.Client` (installed as part of `requirements.txt`):

### Call Applicant DB Tool Directly
```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://localhost:9001/mcp") as client:
        result = await client.call_tool("get_applicant_record", {"applicant_id": "APP001"})
        print(result.data)

asyncio.run(main())
```

### Call Risk Rules Tool Directly
```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://localhost:9002/mcp") as client:
        result = await client.call_tool("get_risk_thresholds", {})
        print(result.data)

asyncio.run(main())
```

## Running the Automated Test Suite

The `tests/` package runs fully offline - no live services and no `ANTHROPIC_API_KEY` required, since
MCP calls and the Claude client are monkeypatched in each test:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Covers: applicant profile scoring (including the new-applicant / cold-start path), the financial risk
agent's DTI/credit/loan-to-income banding and `rule_based_risk_score` aggregation, the LLM client's
JSON-fence stripping, malformed/empty-response fallback, `APIError` fallback, extended-thinking-block
handling, and risk-score clamping, and a `POST`/`GET /applications` integration test against the real
FastAPI app.

## Architecture Verification Checklist

- [ ] All 4 MCP servers start and respond to `/health`
- [ ] FastAPI service is running on port 8000
- [ ] Streamlit UI opens and connects to FastAPI
- [ ] Applicant profile agent enriches state correctly
- [ ] Financial risk agent computes DTI and risk metrics
- [ ] Loan decision agent calls Claude LLM
- [ ] Compliance agent sends notifications
- [ ] Decision log contains classified decisions
- [ ] Notifications appear in console output

## Evaluation Criteria Walkthrough

### 1. Understanding Agentic AI Architecture
- **How to demonstrate**: Show the 4-agent pipeline in action (run a test case and observe log output showing each agent's contribution)
- **Files to reference**: `agents/*.py` for individual agent responsibilities

### 2. Correct Orchestration using LangGraph
- **How to demonstrate**: Walk through `orchestration/graph.py` showing the StateGraph definition, explain how state flows through agents
- **Files to reference**: `orchestration/graph.py`, `orchestration/state.py`

### 3. Clear Agent Responsibilities and MCP Usage
- **How to demonstrate**: For each agent, show which MCP server it calls and what tools it uses. Each
  server is a real MCP server (FastMCP, streamable-HTTP, `/mcp` JSON-RPC endpoint) - confirm with
  `mcp_servers/*.py`'s `@mcp.tool()` definitions and `common/mcp_client.py`'s `fastmcp.Client` usage.
  - Applicant Profile Agent → calls ApplicantDB MCP (port 9001)
  - Financial Risk Agent → calls RiskRulesDB MCP (port 9002)
  - Loan Decision Agent → calls DecisionSynthesis MCP (port 9003) & Claude LLM
  - Compliance Agent → calls NotificationSystem MCP (port 9004)
- **Files to reference**: `agents/*.py`, `mcp_servers/*.py`

### 4. Ability to Modify Code Live
- **Easy to modify**: All rules/thresholds are in `data/risk_rules.json`
- **Easy to modify**: All mock applicant data in `data/applicants.json`
- **Easy to modify**: LLM prompt in `common/llm_client.py` (line ~40)
- **Easy to modify**: Classification logic in agents
- Changes take effect on next service restart

### 5. Explainable AI Outputs
- **How to demonstrate**: Show the decision response includes:
  - Classification (APPROVED/REJECTED/REQUIRES_MANUAL_REVIEW)
  - Risk Score (0-100) - bounded to within `RISK_SCORE_CLAMP_MARGIN` of `financial_risk.rule_based_risk_score`, a deterministic score computed from `data/risk_rules.json`'s weight tables, not a free-form LLM number
  - Confidence Level (0-100%)
  - Key Factors (list of decision reasons)
  - Explanation (narrative from Claude)
  - A persisted audit record: submit an application, restart `run_all.py`, then `GET /applications/{case_id}` still returns it (backed by `data/audit.db`)
- **Files to reference**: `api/schemas.py` DecisionResponse, `common/llm_client.py`, `common/db.py`

## Troubleshooting

### "Cannot connect to localhost:8000"
- Ensure `python run_all.py` is running
- Check that port 8000 is not in use: `lsof -i :8000`

### "Applicant not found" errors
- This is expected behavior - the mock data only includes APP001-APP005
- Use those IDs for testing, or add more records to `data/applicants.json`

### "ANTHROPIC_API_KEY not set"
- Ensure you created `.env` and added your API key
- Verify with: `echo $ANTHROPIC_API_KEY`

### MCP servers not starting
- Check port availability: `netstat -tlnp | grep -E :(9001|9002|9003|9004)`
- Review error logs in terminal running `python run_all.py`

## Live Demo Script (For Evaluation)

```
1. Show the code structure (30 sec)
   - Tree view of agents/, mcp_servers/, orchestration/

2. Highlight key files (1 min)
   - Open orchestration/graph.py → show StateGraph
   - Open agents/loan_decision_agent.py → show LLM call
   - Open mcp_servers/ → show each server

3. Start the system (1 min)
   - Run `python run_all.py`
   - Wait for all services to become ready

4. Submit a test case (1 min)
   - Use curl or Streamlit UI
   - Show real-time decision being generated

5. Modify and re-test (1 min)
   - Edit a threshold in data/risk_rules.json
   - Restart services
   - Show different decision for same applicant

6. Verify explainability (1 min)
   - Show the decision response structure
   - Highlight risk_score, key_factors, explanation
```
