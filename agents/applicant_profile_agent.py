"""Applicant Profile Agent - Enriches application with applicant history and stability scores."""
import logging
from common.mcp_client import MCPToolCall
from common.config import MCP_APPLICANT_DB_URL

logger = logging.getLogger(__name__)

def run(state: dict) -> dict:
    """
    Analyze applicant profile and enrich state with:
    - Income stability score
    - Employment risk assessment
    - Credit history summary
    - Application completeness flags
    """
    applicant_id = state.get("applicant_id")
    income = state.get("income", 0)
    employment_type = state.get("employment_type", "unknown")

    applicant_profile = {
        "applicant_id": applicant_id,
        "income_stability_score": 0,
        "employment_risk": "unknown",
        "employment_type": employment_type,
        "employment_tenure_years": None,
        "payment_on_time_percentage": None,
        "credit_history_years": None,
        "delinquencies_count": None,
        "profile_on_file": False,
        "completeness_status": "complete"
    }

    applicant_record = MCPToolCall.call_tool(
        MCP_APPLICANT_DB_URL,
        "get_applicant_record",
        {"applicant_id": applicant_id}
    )

    if applicant_record.get("success"):
        applicant_profile["profile_on_file"] = True
        employment_history = applicant_record.get("employment_history", {})
        applicant_profile["employment_tenure_years"] = employment_history.get("current_job_tenure_years", 0)

        credit_summary = MCPToolCall.call_tool(
            MCP_APPLICANT_DB_URL,
            "credit_history_summary",
            {"applicant_id": applicant_id}
        )

        if credit_summary.get("success"):
            credit_info = credit_summary.get("credit_history", {})
            applicant_profile["payment_on_time_percentage"] = credit_info.get("payment_on_time_percentage", 0)
            applicant_profile["credit_history_years"] = credit_info.get("years_of_history", 0)
            applicant_profile["delinquencies_count"] = credit_info.get("delinquencies_count", 0)
    else:
        applicant_profile["completeness_status"] = "new_applicant_no_internal_history"

    applicant_profile["income_stability_score"] = _calculate_income_stability(income, employment_type)
    applicant_profile["employment_risk"] = _assess_employment_risk(
        employment_type, applicant_profile["employment_tenure_years"] or 0
    )

    state["applicant_profile"] = applicant_profile
    logger.info(f"Applicant Profile Agent: Processed {applicant_id}")
    return state

def _calculate_income_stability(income: float, employment_type: str) -> int:
    """Calculate income stability score 0-100."""
    score = 0

    if income >= 100000:
        score += 25
    elif income >= 60000:
        score += 15
    else:
        score += 5

    employment_bonuses = {
        "salaried": 25,
        "self_employed": 15,
        "contract": 10,
        "retired": 20,
        "unemployed": 0
    }
    score += employment_bonuses.get(employment_type, 0)

    return min(score, 100)

def _assess_employment_risk(employment_type: str, tenure_years: int) -> str:
    """Assess employment risk level."""
    if employment_type == "salaried":
        return "low" if tenure_years >= 2 else "medium"
    elif employment_type == "self_employed":
        return "low" if tenure_years >= 3 else "high"
    elif employment_type == "contract":
        return "high"
    elif employment_type == "retired":
        return "medium"
    else:
        return "high"
