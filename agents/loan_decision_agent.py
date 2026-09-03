"""Loan Decision Agent - Calls Claude LLM for intelligent classification."""
import logging
import uuid
from common.llm_client import LLMClient
from common.mcp_client import MCPToolCall
from common.config import MCP_DECISION_SYNTHESIS_URL

logger = logging.getLogger(__name__)
llm_client = LLMClient()

def run(state: dict) -> dict:
    """
    Call Claude LLM to synthesize loan decision based on:
    - Applicant profile analysis
    - Financial risk metrics

    Returns:
    - Classification (APPROVED/REJECTED/REQUIRES_MANUAL_REVIEW)
    - Risk score
    - Confidence level
    - Key factors
    - Explanation
    """
    applicant_profile = state.get("applicant_profile", {})
    financial_risk = state.get("financial_risk", {})

    decision = llm_client.get_loan_decision(applicant_profile, financial_risk)

    case_id = str(uuid.uuid4())
    decision["case_id"] = case_id

    log_result = MCPToolCall.call_tool(
        MCP_DECISION_SYNTHESIS_URL,
        "log_decision",
        {
            "case_id": case_id,
            "classification": decision.get("classification", "REQUIRES_MANUAL_REVIEW"),
            "risk_score": decision.get("risk_score", 50),
            "confidence_level": decision.get("confidence_level", 50),
            "key_factors": decision.get("key_factors", []),
            "explanation": decision.get("explanation", "")
        }
    )

    if not log_result.get("success"):
        logger.warning(f"Failed to log decision to MCP: {log_result}")

    state["loan_decision"] = decision
    logger.info(f"Loan Decision Agent: {decision['classification']} (case_id={case_id})")
    return state
