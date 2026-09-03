import uuid

import pytest
from fastapi.testclient import TestClient

import api.main as main_module
from agents import loan_decision_agent
from common import db
from common.mcp_client import MCPToolCall

FAKE_RISK_THRESHOLDS = {
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

FAKE_DECISION = {
    "classification": "APPROVED",
    "risk_score": 22,
    "confidence_level": 85,
    "key_factors": ["Good credit score"],
    "explanation": "Strong applicant."
}


def _fake_call_tool(base_url, tool_name, args):
    if tool_name == "get_applicant_record":
        return {"success": False, "error": "not found"}
    if tool_name == "get_risk_thresholds":
        return FAKE_RISK_THRESHOLDS
    if tool_name == "evaluate_anomaly":
        return {"success": True, "anomaly_detected": False}
    if tool_name == "log_decision":
        return {"success": True, "case_id": args.get("case_id")}
    if tool_name == "send_notification":
        return {"success": True, "notification_id": 1}
    raise AssertionError(f"unexpected tool call in this test: {tool_name}")


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(MCPToolCall, "call_tool", _fake_call_tool)
    monkeypatch.setattr(
        loan_decision_agent.llm_client, "get_loan_decision",
        lambda profile, risk: dict(FAKE_DECISION)
    )
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_audit.db"))
    db.init_db()
    main_module.application_cache.clear()
    return TestClient(main_module.app)


def _sample_payload():
    return {
        "applicant_id": f"TEST-{uuid.uuid4().hex[:8]}",
        "age": 32,
        "income": 85000,
        "employment_type": "salaried",
        "credit_score": 720,
        "loan_amount": 250000,
        "tenure_months": 360,
        "existing_liabilities": 500,
        "location": "New York"
    }


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_submit_application_returns_decision(client):
    response = client.post("/applications", json=_sample_payload())
    assert response.status_code == 200

    body = response.json()
    assert body["classification"] == "APPROVED"
    assert body["risk_score"] == 22
    assert body["case_id"]
    assert "rule_based_risk_score" in body["financial_risk"]
    assert body["compliance_action"]["action_taken"] == "Disbursement Initiated"


def test_get_application_after_submit_is_persisted(client):
    submit_response = client.post("/applications", json=_sample_payload())
    case_id = submit_response.json()["case_id"]

    get_response = client.get(f"/applications/{case_id}")
    assert get_response.status_code == 200
    assert get_response.json()["case_id"] == case_id

    # Confirm it is actually in the SQLite audit trail, not just the in-memory cache.
    assert db.get_application_record(case_id) is not None


def test_get_unknown_case_returns_404(client):
    response = client.get("/applications/does-not-exist")
    assert response.status_code == 404
