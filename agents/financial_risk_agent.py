"""Financial Risk Analysis Agent - Evaluates financial risk metrics."""
import logging
from common.mcp_client import MCPToolCall
from common.config import MCP_RISK_RULES_URL

logger = logging.getLogger(__name__)

def run(state: dict) -> dict:
    """
    Analyze financial risk and compute:
    - Debt-to-Income ratio
    - Credit score risk level
    - Loan amount risk
    - Anomaly detection
    - Risk reasoning
    """
    credit_score = state.get("credit_score", 600)
    loan_amount = state.get("loan_amount", 0)
    tenure_months = state.get("tenure_months", 360)
    existing_liabilities = state.get("existing_liabilities", 0)
    income = state.get("income", 0)

    financial_risk = {
        "credit_score": credit_score,
        "debt_to_income_ratio": 0.0,
        "dti_classification": "unknown",
        "credit_score_risk_level": "unknown",
        "loan_amount_risk_level": "unknown",
        "loan_to_income_ratio": 0.0,
        "anomaly_detected": False,
        "rule_based_risk_score": 50,
        "reasoning": ""
    }

    risk_thresholds = MCPToolCall.call_tool(
        MCP_RISK_RULES_URL,
        "get_risk_thresholds",
        {}
    )

    if risk_thresholds.get("success"):
        thresholds = risk_thresholds.get("dti_thresholds", {})
        credit_bands = risk_thresholds.get("credit_score_bands", {})
        loan_to_income_bands = risk_thresholds.get("loan_to_income_ratio", {})

        monthly_loan_payment = _calculate_monthly_payment(loan_amount, tenure_months)
        monthly_income = income / 12

        if monthly_income > 0:
            financial_risk["debt_to_income_ratio"] = (existing_liabilities + monthly_loan_payment) / monthly_income
        else:
            financial_risk["debt_to_income_ratio"] = 0.0

        dti = financial_risk["debt_to_income_ratio"]
        if dti <= 0.36:
            financial_risk["dti_classification"] = "safe"
        elif dti <= 0.43:
            financial_risk["dti_classification"] = "moderate"
        elif dti <= 0.50:
            financial_risk["dti_classification"] = "high"
        else:
            financial_risk["dti_classification"] = "very_high"

        for band, params in credit_bands.items():
            if params.get("min", 0) <= credit_score <= params.get("max", 1000):
                financial_risk["credit_score_risk_level"] = band
                break

        if income > 0:
            financial_risk["loan_to_income_ratio"] = loan_amount / income
        else:
            financial_risk["loan_to_income_ratio"] = 0.0

        if financial_risk["loan_to_income_ratio"] > 5.0:
            financial_risk["loan_amount_risk_level"] = "very_high"
        elif financial_risk["loan_to_income_ratio"] > 4.0:
            financial_risk["loan_amount_risk_level"] = "high"
        elif financial_risk["loan_to_income_ratio"] > 3.0:
            financial_risk["loan_amount_risk_level"] = "moderate"
        else:
            financial_risk["loan_amount_risk_level"] = "safe"

        anomaly_check = MCPToolCall.call_tool(
            MCP_RISK_RULES_URL,
            "evaluate_anomaly",
            {
                "loan_to_income_ratio": financial_risk["loan_to_income_ratio"],
                "credit_score_drop": 0,
                "employment_type": state.get("employment_type", "unknown")
            }
        )

        if anomaly_check.get("success"):
            financial_risk["anomaly_detected"] = anomaly_check.get("anomaly_detected", False)

        dti_impact = thresholds.get(financial_risk["dti_classification"], {}).get("risk_score_impact", 0)
        credit_impact = credit_bands.get(financial_risk["credit_score_risk_level"], {}).get("risk_score_impact", 0)
        loan_impact = loan_to_income_bands.get(financial_risk["loan_amount_risk_level"], {}).get("risk_score_impact", 0)
        financial_risk["rule_based_risk_score"] = min(100, dti_impact + credit_impact + loan_impact)

    financial_risk["reasoning"] = _build_reasoning(financial_risk, state)
    state["financial_risk"] = financial_risk
    logger.info(f"Financial Risk Agent: DTI={financial_risk['debt_to_income_ratio']:.2f}, Credit={financial_risk['credit_score']}")
    return state

def _calculate_monthly_payment(principal: float, tenure_months: int) -> float:
    """Simple monthly payment calculation (assumes fixed rate ~5%)."""
    if tenure_months == 0:
        return 0
    annual_rate = 0.05
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return principal / tenure_months
    payment = principal * (monthly_rate * (1 + monthly_rate)**tenure_months) / ((1 + monthly_rate)**tenure_months - 1)
    return payment

def _build_reasoning(financial_risk: dict, state: dict) -> str:
    """Build a detailed reasoning string."""
    reasons = []

    dti_class = financial_risk["dti_classification"]
    if dti_class == "safe":
        reasons.append("DTI ratio is within safe limits")
    elif dti_class == "moderate":
        reasons.append("DTI ratio is moderate - manageable risk")
    elif dti_class == "high":
        reasons.append("DTI ratio is high - elevated debt burden")
    else:
        reasons.append("DTI ratio exceeds safe thresholds")

    credit_score = financial_risk["credit_score"]
    if credit_score >= 750:
        reasons.append("Excellent credit history")
    elif credit_score >= 700:
        reasons.append("Good credit score")
    elif credit_score >= 650:
        reasons.append("Fair credit score - some concern")
    else:
        reasons.append("Credit score is low - significant risk")

    if financial_risk.get("anomaly_detected"):
        reasons.append("Loan amount is unusually high relative to income")

    return "; ".join(reasons)
