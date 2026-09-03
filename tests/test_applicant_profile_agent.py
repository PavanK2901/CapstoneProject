from agents import applicant_profile_agent
from common.mcp_client import MCPToolCall


def test_income_stability_rewards_high_income_and_salaried():
    high = applicant_profile_agent._calculate_income_stability(120000, "salaried")
    low = applicant_profile_agent._calculate_income_stability(30000, "unemployed")
    assert high == 50  # 25 (income) + 25 (salaried)
    assert low == 5    # 5 (income) + 0 (unemployed)


def test_employment_risk_levels():
    assert applicant_profile_agent._assess_employment_risk("salaried", 5) == "low"
    assert applicant_profile_agent._assess_employment_risk("salaried", 1) == "medium"
    assert applicant_profile_agent._assess_employment_risk("contract", 10) == "high"
    assert applicant_profile_agent._assess_employment_risk("unknown_type", 10) == "high"


def test_run_new_applicant_is_not_penalized(monkeypatch):
    """A cold-start applicant (not on file) must not default fields to 0 - see prior
    review finding where 0-defaults spuriously triggered manual review."""
    monkeypatch.setattr(
        MCPToolCall, "call_tool",
        lambda base_url, tool_name, args: {"success": False, "error": "not found"}
    )

    state = {"applicant_id": "NEWAPP", "income": 90000, "employment_type": "salaried"}
    result = applicant_profile_agent.run(state)

    profile = result["applicant_profile"]
    assert profile["profile_on_file"] is False
    assert profile["completeness_status"] == "new_applicant_no_internal_history"
    assert profile["employment_tenure_years"] is None
    assert profile["payment_on_time_percentage"] is None


def test_run_known_applicant_uses_credit_history(monkeypatch):
    def fake_call_tool(base_url, tool_name, args):
        if tool_name == "get_applicant_record":
            return {"success": True, "employment_history": {"current_job_tenure_years": 6}}
        if tool_name == "credit_history_summary":
            return {
                "success": True,
                "credit_history": {
                    "years_of_history": 10,
                    "delinquencies_count": 0,
                    "payment_on_time_percentage": 99
                }
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(MCPToolCall, "call_tool", fake_call_tool)

    state = {"applicant_id": "APP001", "income": 90000, "employment_type": "salaried"}
    result = applicant_profile_agent.run(state)

    profile = result["applicant_profile"]
    assert profile["profile_on_file"] is True
    assert profile["completeness_status"] == "complete"
    assert profile["employment_tenure_years"] == 6
    assert profile["payment_on_time_percentage"] == 99
    assert profile["employment_risk"] == "low"
