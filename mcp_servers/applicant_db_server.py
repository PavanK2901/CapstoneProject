"""Applicant Profile MCP Server - Provides applicant data and credit history."""
import json
import logging

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from common.config import APPLICANTS_DATA_FILE, APPLICANT_DB_PORT

logger = logging.getLogger(__name__)
mcp = FastMCP("applicant-db")

applicants_db = {}


def load_applicants_data():
    global applicants_db
    try:
        with open(APPLICANTS_DATA_FILE, 'r') as f:
            applicants_db = json.load(f)
            logger.info(f"Loaded {len(applicants_db)} applicant records")
    except Exception as e:
        logger.error(f"Failed to load applicants data: {e}")
        applicants_db = {}


load_applicants_data()


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "applicant_db"})


@mcp.tool()
def get_applicant_record(applicant_id: str) -> dict:
    """Look up an applicant's on-file record by applicant_id."""
    if applicant_id in applicants_db:
        applicant = applicants_db[applicant_id]
        return {
            "success": True,
            "applicant_id": applicant_id,
            "name": applicant.get("name", "Unknown"),
            "age": applicant.get("age", 0),
            "employment_type": applicant.get("employment_type", "Unknown"),
            "employment_history": applicant.get("employment_history", {}),
            "location": applicant.get("location", "Unknown"),
            "verified": applicant.get("verified", False)
        }
    return {"success": False, "error": f"Applicant {applicant_id} not found"}


@mcp.tool()
def credit_history_summary(applicant_id: str) -> dict:
    """Summarize an applicant's on-file credit history."""
    if applicant_id in applicants_db:
        applicant = applicants_db[applicant_id]
        credit_history = applicant.get("credit_history", {})
        return {
            "success": True,
            "applicant_id": applicant_id,
            "credit_history": {
                "years_of_history": credit_history.get("years_of_history", 0),
                "accounts_open": credit_history.get("accounts_open", 0),
                "accounts_closed": credit_history.get("accounts_closed", 0),
                "delinquencies_count": credit_history.get("delinquencies_count", 0),
                "payment_on_time_percentage": credit_history.get("payment_on_time_percentage", 0)
            }
        }
    return {"success": False, "error": f"Applicant {applicant_id} not found"}


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=APPLICANT_DB_PORT)
