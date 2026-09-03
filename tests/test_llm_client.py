from types import SimpleNamespace

import httpx
import pytest
from anthropic import APIStatusError

from common.llm_client import LLMClient

PROFILE = {"income_stability_score": 40, "employment_risk": "low", "profile_on_file": True}


def _financial_risk(rule_based_risk_score=30):
    return {
        "debt_to_income_ratio": 0.2,
        "dti_classification": "safe",
        "credit_score": 720,
        "credit_score_risk_level": "good",
        "loan_amount_risk_level": "safe",
        "loan_to_income_ratio": 2.0,
        "anomaly_detected": False,
        "reasoning": "DTI ratio is within safe limits",
        "rule_based_risk_score": rule_based_risk_score
    }


def _fake_response(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def test_parses_plain_json(monkeypatch):
    client = LLMClient()
    monkeypatch.setattr(
        client.client.messages, "create",
        lambda **kwargs: _fake_response(
            '{"classification": "APPROVED", "risk_score": 25, "confidence_level": 90, '
            '"key_factors": ["Good credit"], "explanation": "Looks solid"}'
        )
    )

    decision = client.get_loan_decision(PROFILE, _financial_risk(rule_based_risk_score=25))
    assert decision["classification"] == "APPROVED"
    assert decision["risk_score"] == 25
    assert decision["key_factors"] == ["Good credit"]


def test_strips_markdown_fences(monkeypatch):
    client = LLMClient()
    monkeypatch.setattr(
        client.client.messages, "create",
        lambda **kwargs: _fake_response(
            '```json\n{"classification": "REJECTED", "risk_score": 80, '
            '"confidence_level": 70, "key_factors": [], "explanation": "High risk"}\n```'
        )
    )

    decision = client.get_loan_decision(PROFILE, _financial_risk(rule_based_risk_score=80))
    assert decision["classification"] == "REJECTED"
    assert decision["risk_score"] == 80


def test_malformed_json_falls_back_to_manual_review(monkeypatch):
    client = LLMClient()
    monkeypatch.setattr(
        client.client.messages, "create",
        lambda **kwargs: _fake_response("not valid json at all")
    )

    decision = client.get_loan_decision(PROFILE, _financial_risk())
    assert decision["classification"] == "REQUIRES_MANUAL_REVIEW"
    assert "Unable to parse LLM response" in decision["key_factors"]


def test_skips_leading_thinking_block_to_find_text(monkeypatch):
    """Extended thinking puts a ThinkingBlock at content[0]; the real answer is a later
    TextBlock. The client must not assume content[0] is always the answer."""
    client = LLMClient()
    thinking_block = SimpleNamespace(type="thinking", thinking="reasoning...", text=None)
    text_block = SimpleNamespace(
        type="text",
        text='{"classification": "APPROVED", "risk_score": 22, "confidence_level": 85, '
             '"key_factors": ["Solid profile"], "explanation": "Looks good"}'
    )
    monkeypatch.setattr(
        client.client.messages, "create",
        lambda **kwargs: SimpleNamespace(content=[thinking_block, text_block])
    )

    decision = client.get_loan_decision(PROFILE, _financial_risk(rule_based_risk_score=22))
    assert decision["classification"] == "APPROVED"
    assert decision["risk_score"] == 22


def test_empty_response_falls_back_to_manual_review(monkeypatch):
    client = LLMClient()
    monkeypatch.setattr(
        client.client.messages, "create",
        lambda **kwargs: SimpleNamespace(content=[])
    )

    decision = client.get_loan_decision(PROFILE, _financial_risk())
    assert decision["classification"] == "REQUIRES_MANUAL_REVIEW"


def test_api_error_falls_back_to_manual_review(monkeypatch):
    client = LLMClient()

    def raise_api_error(**kwargs):
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        response = httpx.Response(status_code=529, request=request)
        raise APIStatusError("overloaded", response=response, body=None)

    monkeypatch.setattr(client.client.messages, "create", raise_api_error)

    decision = client.get_loan_decision(PROFILE, _financial_risk())
    assert decision["classification"] == "REQUIRES_MANUAL_REVIEW"
    assert "LLM API call failed" in decision["key_factors"]


def test_risk_score_is_clamped_to_rule_based_baseline(monkeypatch):
    client = LLMClient()
    monkeypatch.setattr(
        client.client.messages, "create",
        lambda **kwargs: _fake_response(
            '{"classification": "REJECTED", "risk_score": 95, "confidence_level": 60, '
            '"key_factors": ["Model thinks it is very risky"], "explanation": "..."}'
        )
    )

    # Baseline is 20, LLM tries to jump to 95 -> clamped to 20 + 20 = 40
    decision = client.get_loan_decision(PROFILE, _financial_risk(rule_based_risk_score=20))
    assert decision["risk_score"] == 40
    assert "Risk score bounded by rule-based baseline for auditability" in decision["key_factors"]


def test_risk_score_within_margin_is_not_clamped(monkeypatch):
    client = LLMClient()
    monkeypatch.setattr(
        client.client.messages, "create",
        lambda **kwargs: _fake_response(
            '{"classification": "APPROVED", "risk_score": 30, "confidence_level": 85, '
            '"key_factors": ["Solid profile"], "explanation": "..."}'
        )
    )

    decision = client.get_loan_decision(PROFILE, _financial_risk(rule_based_risk_score=25))
    assert decision["risk_score"] == 30
    assert "Risk score bounded by rule-based baseline for auditability" not in decision["key_factors"]
