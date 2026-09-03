"""API request/response schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LoanApplicationRequest(BaseModel):
    applicant_id: str
    age: int = Field(..., ge=18, le=100)
    income: float = Field(..., gt=0)
    employment_type: str
    credit_score: int = Field(..., ge=300, le=850)
    loan_amount: float = Field(..., gt=0)
    tenure_months: int = Field(..., gt=0)
    existing_liabilities: float = Field(..., ge=0)
    location: str
    application_timestamp: Optional[str] = None

class DecisionResponse(BaseModel):
    case_id: str
    classification: str
    risk_score: int
    confidence_level: int
    key_factors: List[str]
    explanation: str
    applicant_profile: dict
    financial_risk: dict
    compliance_action: dict
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    service: str
