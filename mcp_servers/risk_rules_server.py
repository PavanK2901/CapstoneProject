"""Financial Risk Rules MCP Server - Provides risk evaluation rules and thresholds."""
import json
import logging

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from common.config import RISK_RULES_DATA_FILE, RISK_RULES_PORT

logger = logging.getLogger(__name__)
mcp = FastMCP("risk-rules")

risk_rules = {}


def load_risk_rules():
    global risk_rules
    try:
        with open(RISK_RULES_DATA_FILE, 'r') as f:
            risk_rules = json.load(f)
            logger.info("Loaded risk rules")
    except Exception as e:
        logger.error(f"Failed to load risk rules: {e}")
        risk_rules = {}


load_risk_rules()


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "risk_rules"})


@mcp.tool()
def get_risk_thresholds() -> dict:
    """Return the configured DTI/credit-score/employment/income/loan-to-income risk thresholds."""
    return {
        "success": True,
        "dti_thresholds": risk_rules.get("debt_to_income_thresholds", {}),
        "credit_score_bands": risk_rules.get("credit_score_bands", {}),
        "employment_risk": risk_rules.get("employment_risk", {}),
        "income_stability": risk_rules.get("income_stability_score", {}),
        "loan_to_income_ratio": risk_rules.get("loan_amount_to_income_ratio", {}),
        "minimum_credit_score": risk_rules.get("minimum_credit_score", 600),
        "maximum_dti": risk_rules.get("maximum_dti_ratio", 0.50)
    }


@mcp.tool()
def evaluate_anomaly(loan_to_income_ratio: float, credit_score_drop: float, employment_type: str) -> dict:
    """Flag whether the loan-to-income ratio is an outlier relative to configured thresholds."""
    anomaly_threshold = risk_rules.get("anomaly_detection", {}).get("loan_to_income_outlier_threshold", 5.0)
    is_anomaly = loan_to_income_ratio > anomaly_threshold

    return {
        "success": True,
        "anomaly_detected": is_anomaly,
        "loan_to_income_ratio": loan_to_income_ratio,
        "anomaly_threshold": anomaly_threshold,
        "employment_type": employment_type,
        "reasoning": "Loan amount significantly exceeds annual income" if is_anomaly else "Loan amount within normal range"
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=RISK_RULES_PORT)
