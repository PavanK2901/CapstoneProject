import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

# Service Ports
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", 8000))
APPLICANT_DB_PORT = int(os.getenv("APPLICANT_DB_PORT", 9001))
RISK_RULES_PORT = int(os.getenv("RISK_RULES_PORT", 9002))
DECISION_SYNTHESIS_PORT = int(os.getenv("DECISION_SYNTHESIS_PORT", 9003))
NOTIFICATION_PORT = int(os.getenv("NOTIFICATION_PORT", 9004))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# MCP Service URLs
MCP_APPLICANT_DB_URL = f"http://localhost:{APPLICANT_DB_PORT}"
MCP_RISK_RULES_URL = f"http://localhost:{RISK_RULES_PORT}"
MCP_DECISION_SYNTHESIS_URL = f"http://localhost:{DECISION_SYNTHESIS_PORT}"
MCP_NOTIFICATION_URL = f"http://localhost:{NOTIFICATION_PORT}"

# Data paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
APPLICANTS_DATA_FILE = os.path.join(DATA_DIR, "applicants.json")
RISK_RULES_DATA_FILE = os.path.join(DATA_DIR, "risk_rules.json")
