"""FastAPI microservice for loan application processing."""
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from api.schemas import LoanApplicationRequest, DecisionResponse, HealthResponse
from orchestration.graph import graph
from orchestration.state import LoanApplicationState
from common import db
from common.mcp_client import MCPToolCall
from common.config import (
    MCP_APPLICANT_DB_URL,
    MCP_RISK_RULES_URL,
    MCP_DECISION_SYNTHESIS_URL,
    MCP_NOTIFICATION_URL
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Loan Approval API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()
application_cache = {}
_services_ready = False

@app.on_event("startup")
async def startup_event():
    """Verify all MCP services are ready before accepting application requests."""
    global _services_ready
    logger.info("Starting FastAPI. Verifying MCP services...")

    services = [
        ("Applicant DB", MCP_APPLICANT_DB_URL),
        ("Risk Rules", MCP_RISK_RULES_URL),
        ("Decision Synthesis", MCP_DECISION_SYNTHESIS_URL),
        ("Notification", MCP_NOTIFICATION_URL),
    ]

    all_ready = True
    for service_name, service_url in services:
        if MCPToolCall.wait_for_service(service_url, timeout=30):
            logger.info(f"✅ {service_name} ({service_url}) is ready")
        else:
            logger.error(f"❌ {service_name} ({service_url}) failed to start")
            all_ready = False

    if all_ready:
        _services_ready = True
        logger.info("✅ All MCP services are ready. FastAPI is accepting requests.")
    else:
        logger.warning("⚠️  Some MCP services are not ready yet. Requests may fail.")
        _services_ready = False


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "loan_approval_api"}

@app.post("/applications", response_model=DecisionResponse)
async def submit_application(request: LoanApplicationRequest):
    """Submit a loan application for processing."""
    if not _services_ready:
        raise HTTPException(
            status_code=503,
            detail="Services are initializing. Please wait 10-15 seconds and retry. "
                   "You can check service status with: curl http://localhost:8000/health"
        )

    try:
        timestamp = request.application_timestamp or datetime.utcnow().isoformat()

        initial_state: LoanApplicationState = {
            "applicant_id": request.applicant_id,
            "age": request.age,
            "income": request.income,
            "employment_type": request.employment_type,
            "credit_score": request.credit_score,
            "loan_amount": request.loan_amount,
            "tenure_months": request.tenure_months,
            "existing_liabilities": request.existing_liabilities,
            "location": request.location,
            "application_timestamp": timestamp,
            "applicant_profile": None,
            "financial_risk": None,
            "loan_decision": None,
            "compliance_action": None
        }

        logger.info(f"Processing application {request.applicant_id}")
        try:
            final_state = graph.invoke(initial_state)
        except Exception as e:
            logger.error(f"Graph invoke failed: {e}", exc_info=True)
            raise

        case_id = final_state.get("loan_decision", {}).get("case_id", "unknown")
        application_cache[case_id] = final_state

        response = DecisionResponse(
            case_id=case_id,
            classification=final_state.get("loan_decision", {}).get("classification", "UNKNOWN"),
            risk_score=final_state.get("loan_decision", {}).get("risk_score", 0),
            confidence_level=final_state.get("loan_decision", {}).get("confidence_level", 0),
            key_factors=final_state.get("loan_decision", {}).get("key_factors", []),
            explanation=final_state.get("loan_decision", {}).get("explanation", ""),
            applicant_profile=final_state.get("applicant_profile", {}),
            financial_risk=final_state.get("financial_risk", {}),
            compliance_action=final_state.get("compliance_action", {}),
            timestamp=datetime.utcnow().isoformat()
        )

        db.save_application_record(case_id, request.applicant_id, response.model_dump(), response.timestamp)

        logger.info(f"Application {request.applicant_id} processed: {response.classification}")
        return response

    except Exception as e:
        logger.error(f"Error processing application: {e}", exc_info=True)
        raise

@app.get("/applications/{case_id}", response_model=DecisionResponse)
async def get_application_status(case_id: str):
    """Retrieve decision for a case. Backed by the SQLite audit trail, so this
    survives an API restart, not just the in-memory cache from this process."""
    persisted = db.get_application_record(case_id)
    if persisted is not None:
        return DecisionResponse(**persisted)

    if case_id not in application_cache:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    final_state = application_cache[case_id]

    return DecisionResponse(
        case_id=case_id,
        classification=final_state.get("loan_decision", {}).get("classification", "UNKNOWN"),
        risk_score=final_state.get("loan_decision", {}).get("risk_score", 0),
        confidence_level=final_state.get("loan_decision", {}).get("confidence_level", 0),
        key_factors=final_state.get("loan_decision", {}).get("key_factors", []),
        explanation=final_state.get("loan_decision", {}).get("explanation", ""),
        applicant_profile=final_state.get("applicant_profile", {}),
        financial_risk=final_state.get("financial_risk", {}),
        compliance_action=final_state.get("compliance_action", {}),
        timestamp=datetime.utcnow().isoformat()
    )

if __name__ == "__main__":
    import uvicorn
    from common.config import FASTAPI_PORT
    uvicorn.run(app, host="0.0.0.0", port=FASTAPI_PORT)
