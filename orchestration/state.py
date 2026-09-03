"""Shared state definition for LangGraph orchestration."""
from typing import TypedDict, Optional, List

class LoanApplicationState(TypedDict):
    # Input application data
    applicant_id: str
    age: int
    income: float
    employment_type: str
    credit_score: int
    loan_amount: float
    tenure_months: int
    existing_liabilities: float
    location: str
    application_timestamp: str

    # Enriched by agents
    applicant_profile: Optional[dict]
    financial_risk: Optional[dict]
    loan_decision: Optional[dict]
    compliance_action: Optional[dict]
