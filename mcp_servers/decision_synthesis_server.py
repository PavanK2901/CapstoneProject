"""Decision Synthesis MCP Server - Logs and retrieves loan decisions (SQLite-backed)."""
import logging
from datetime import datetime

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from common.config import DECISION_SYNTHESIS_PORT
from common import db

logger = logging.getLogger(__name__)
mcp = FastMCP("decision-synthesis")

db.init_db()


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "decision_synthesis"})


@mcp.tool()
def log_decision(case_id: str, classification: str, risk_score: int, confidence_level: int,
                  key_factors: list, explanation: str) -> dict:
    """Persist a loan decision to the audit trail."""
    timestamp = datetime.utcnow().isoformat()
    db.save_decision(case_id, classification, risk_score, confidence_level, key_factors, explanation, timestamp)
    logger.info(f"Logged decision for case {case_id}: {classification}")

    return {
        "success": True,
        "case_id": case_id,
        "message": "Decision logged successfully"
    }


@mcp.tool()
def get_decision_log(case_id: str) -> dict:
    """Retrieve a previously logged decision by case_id."""
    decision = db.get_decision(case_id)
    if decision is not None:
        return {"success": True, "decision": decision}
    return {"success": False, "error": f"Decision record for case {case_id} not found"}


@mcp.tool()
def get_all_decisions() -> dict:
    """Retrieve every decision logged so far, most recent first."""
    decisions = db.get_all_decisions()
    return {
        "success": True,
        "total_decisions": len(decisions),
        "decisions": decisions
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=DECISION_SYNTHESIS_PORT)
