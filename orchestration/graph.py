"""LangGraph orchestration engine for loan approval workflow."""
import logging
from langgraph.graph import StateGraph
from orchestration.state import LoanApplicationState
from agents import applicant_profile_agent, financial_risk_agent, loan_decision_agent, compliance_action_agent

logger = logging.getLogger(__name__)

def create_loan_approval_graph():
    """Create the LangGraph workflow for loan approval."""
    workflow = StateGraph(LoanApplicationState)

    workflow.add_node("process_applicant_profile", applicant_profile_agent.run)
    workflow.add_node("calculate_financial_risk", financial_risk_agent.run)
    workflow.add_node("make_loan_decision", loan_decision_agent.run)
    workflow.add_node("execute_compliance_action", compliance_action_agent.run)

    workflow.set_entry_point("process_applicant_profile")
    workflow.add_edge("process_applicant_profile", "calculate_financial_risk")
    workflow.add_edge("calculate_financial_risk", "make_loan_decision")
    workflow.add_edge("make_loan_decision", "execute_compliance_action")
    workflow.set_finish_point("execute_compliance_action")

    return workflow.compile()

graph = create_loan_approval_graph()
