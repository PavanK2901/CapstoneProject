"""Streamlit chatbot UI for loan application submission."""
import streamlit as st
import requests
import json
from datetime import datetime

FASTAPI_URL = "http://localhost:8000"

st.set_page_config(page_title="Loan Approval Assistant", page_icon="🏦", layout="wide")

st.title("🏦 Intelligent Loan Approval Assistant")
st.markdown("Submit your loan application and get instant AI-powered analysis")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Welcome! I'm your AI loan advisor. I can help you understand your loan application prospects. Fill in the form below and I'll provide a detailed analysis powered by our Multi-Agent AI system."
        }
    ]

if "submitted_cases" not in st.session_state:
    st.session_state.submitted_cases = []

st.markdown("---")

with st.form("loan_application_form"):
    st.subheader("📋 Loan Application Details")

    col1, col2 = st.columns(2)
    with col1:
        applicant_id = st.text_input("Applicant ID", value=f"APP{datetime.now().strftime('%Y%m%d%H%M%S')}")
        age = st.number_input("Age", min_value=18, max_value=100, value=35)
        income = st.number_input("Annual Income ($)", min_value=20000, value=75000)
        employment_type = st.selectbox(
            "Employment Type",
            ["salaried", "self_employed", "contract", "retired", "unemployed"]
        )

    with col2:
        credit_score = st.number_input("Credit Score", min_value=300, max_value=850, value=720)
        loan_amount = st.number_input("Loan Amount ($)", min_value=10000, value=250000)
        tenure_months = st.number_input("Loan Tenure (months)", min_value=12, max_value=360, value=360)
        existing_liabilities = st.number_input("Existing Monthly Liabilities ($)", min_value=0, value=500)

    location = st.text_input("Location", value="New York")

    submitted = st.form_submit_button("🚀 Submit Application", use_container_width=True)

    if submitted:
        try:
            payload = {
                "applicant_id": applicant_id,
                "age": age,
                "income": income,
                "employment_type": employment_type,
                "credit_score": credit_score,
                "loan_amount": loan_amount,
                "tenure_months": tenure_months,
                "existing_liabilities": existing_liabilities,
                "location": location,
                "application_timestamp": datetime.utcnow().isoformat()
            }

            with st.spinner("🤖 Multi-Agent AI analyzing your application..."):
                response = requests.post(f"{FASTAPI_URL}/applications", json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()

            st.session_state.messages.append({
                "role": "user",
                "content": f"I applied for a ${loan_amount:,.0f} loan with a credit score of {credit_score}"
            })

            decision = result.get("classification", "UNKNOWN")
            badge_color = "🟢" if decision == "APPROVED" else "🔴" if decision == "REJECTED" else "🟡"

            message = f"""
{badge_color} **Decision: {decision}**

**Case ID:** {result.get('case_id')}

**Financial Analysis:**
- Risk Score: {result.get('risk_score')}/100
- Confidence Level: {result.get('confidence_level')}%
- Debt-to-Income Ratio: {result.get('financial_risk', {}).get('debt_to_income_ratio', 0):.2%}
- Credit Score Risk: {result.get('financial_risk', {}).get('credit_score_risk_level', 'Unknown')}

**Key Decision Factors:**
"""
            for factor in result.get('key_factors', []):
                message += f"- {factor}\n"

            message += f"\n**Analysis:**\n{result.get('explanation', 'No explanation provided')}"

            if result.get('compliance_action'):
                message += f"\n\n**Next Steps:** {result.get('compliance_action', {}).get('action_taken', 'Pending')}"

            st.session_state.messages.append({
                "role": "assistant",
                "content": message
            })

            st.session_state.submitted_cases.append({
                "case_id": result.get('case_id'),
                "decision": decision,
                "timestamp": datetime.now().isoformat()
            })

        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to the loan approval API. Make sure to run `python run_all.py` first!")
        except requests.exceptions.Timeout:
            st.error("❌ Request timed out. The analysis is taking longer than expected.")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

st.markdown("---")
st.subheader("💬 Conversation History")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.submitted_cases:
    st.markdown("---")
    st.subheader("📊 Application History")
    for case in st.session_state.submitted_cases:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.code(case["case_id"], language=None)
        with col2:
            st.write(f"**{case['decision']}**")
        with col3:
            st.write(case["timestamp"][:10])

st.markdown("---")
st.caption("🔐 Powered by Multi-Agent AI • Loan decisions generated by Claude LLM + domain agents")
