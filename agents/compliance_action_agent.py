"""Compliance & Action Orchestrator Agent - Maps decisions to actions and notifications."""
import logging
from datetime import datetime
from common.mcp_client import MCPToolCall
from common.config import MCP_NOTIFICATION_URL

logger = logging.getLogger(__name__)

def run(state: dict) -> dict:
    """
    Final orchestration:
    - Map classification to action
    - Send notification
    - Generate summary
    """
    case_id = state.get("loan_decision", {}).get("case_id", "unknown")
    classification = state.get("loan_decision", {}).get("classification", "UNKNOWN")
    applicant_id = state.get("applicant_id", "unknown")

    action_mapping = {
        "APPROVED": {
            "action": "Disbursement Initiated",
            "notification_type": "EMAIL",
            "subject": "Loan Application Approved"
        },
        "REJECTED": {
            "action": "Application Closed",
            "notification_type": "EMAIL",
            "subject": "Loan Application Rejected"
        },
        "REQUIRES_MANUAL_REVIEW": {
            "action": "Escalated to Manual Underwriter",
            "notification_type": "EMAIL",
            "subject": "Loan Application Under Review"
        }
    }

    action_info = action_mapping.get(classification, action_mapping["REQUIRES_MANUAL_REVIEW"])

    notification_result = MCPToolCall.call_tool(
        MCP_NOTIFICATION_URL,
        "send_notification",
        {
            "case_id": case_id,
            "notification_type": action_info["notification_type"],
            "recipient": f"applicant_{applicant_id}@example.com",
            "subject": action_info["subject"],
            "message": f"Your loan application ({case_id}) status: {classification}"
        }
    )

    compliance_action = {
        "case_id": case_id,
        "classification": classification,
        "action_taken": action_info["action"],
        "notification_sent": notification_result.get("success", False),
        "timestamp": datetime.utcnow().isoformat(),
        "summary": f"Application {case_id}: {classification} - {action_info['action']}"
    }

    state["compliance_action"] = compliance_action
    logger.info(f"Compliance Agent: Case {case_id} - Action: {action_info['action']}")
    return state
