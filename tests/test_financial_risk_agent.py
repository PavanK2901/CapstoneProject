from agents import financial_risk_agent
from common.mcp_client import MCPToolCall

FAKE_THRESHOLDS = {
    "success": True,
    "dti_thresholds": {
        "safe": {"max": 0.36, "risk_score_impact": 5},
        "moderate": {"min": 0.36, "max": 0.43, "risk_score_impact": 25},
        "high": {"min": 0.43, "max": 0.50, "risk_score_impact": 50},
        "very_high": {"min": 0.50, "risk_score_impact": 75}
    },
    "credit_score_bands": {
        "excellent": {"min": 750, "max": 850, "risk_score_impact": 5},
        "good": {"min": 700, "max": 749, "risk_score_impact": 15},
        "fair": {"min": 650, "max": 699, "risk_score_impact": 35},
        "poor": {"min": 600, "max": 649, "risk_score_impact": 60},
        "very_poor": {"min": 0, "max": 599, "risk_score_impact": 85}
    },
    "loan_to_income_ratio": {
        "safe": {"max_ratio": 3.0, "risk_score_impact": 5},
        "moderate": {"min_ratio": 3.0, "max_ratio": 4.0, "risk_score_impact": 20},
        "high": {"min_ratio": 4.0, "max_ratio": 5.0, "risk_score_impact": 40},
        "very_high": {"min_ratio": 5.0, "risk_score_impact": 60}
    }
}


def _fake_call_tool(base_url, tool_name, args):
    if tool_name == "get_risk_thresholds":
        return FAKE_THRESHOLDS
    if tool_name == "evaluate_anomaly":
        return {"success": True, "anomaly_detected": args["loan_to_income_ratio"] > 5.0}
    raise AssertionError(f"unexpected tool call: {tool_name}")


def test_monthly_payment_zero_tenure_is_zero():
    assert financial_risk_agent._calculate_monthly_payment(100000, 0) == 0


def test_run_computes_rule_based_risk_score_for_strong_applicant(monkeypatch):
    monkeypatch.setattr(MCPToolCall, "call_tool", _fake_call_tool)

    state = {
        "credit_score": 720,
        "loan_amount": 250000,
        "tenure_months": 360,
        "existing_liabilities": 500,
        "income": 85000,
        "employment_type": "salaried"
    }
    result = financial_risk_agent.run(state)
    risk = result["financial_risk"]

    assert risk["dti_classification"] == "safe"
    assert risk["credit_score_risk_level"] == "good"
    assert risk["loan_amount_risk_level"] == "safe"
    # safe DTI (5) + good credit (15) + safe loan-to-income (5)
    assert risk["rule_based_risk_score"] == 25
    assert risk["anomaly_detected"] is False


def test_run_computes_rule_based_risk_score_for_weak_applicant(monkeypatch):
    monkeypatch.setattr(MCPToolCall, "call_tool", _fake_call_tool)

    state = {
        "credit_score": 590,
        "loan_amount": 900000,
        "tenure_months": 120,
        "existing_liabilities": 4000,
        "income": 60000,
        "employment_type": "unemployed"
    }
    result = financial_risk_agent.run(state)
    risk = result["financial_risk"]

    assert risk["credit_score_risk_level"] == "very_poor"
    assert risk["loan_amount_risk_level"] == "very_high"
    assert risk["rule_based_risk_score"] == 100  # capped, since raw sum exceeds 100
    assert risk["anomaly_detected"] is True
