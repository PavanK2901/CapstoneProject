from anthropic import Anthropic, APIError
from common.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from pydantic import BaseModel
import json
import logging

logger = logging.getLogger(__name__)

RISK_SCORE_CLAMP_MARGIN = 20  # max points the LLM may deviate from the rule-based baseline

class LoanDecisionSchema(BaseModel):
    classification: str  # APPROVED, REJECTED, REQUIRES_MANUAL_REVIEW
    risk_score: int  # 0-100
    confidence_level: int  # 0-100
    key_factors: list[str]
    explanation: str

class LLMClient:
    def __init__(self):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = CLAUDE_MODEL

    def get_loan_decision(self, applicant_profile: dict, financial_risk: dict) -> dict:
        """Call Claude LLM with loan application context to get classification and explanation."""

        profile_on_file = applicant_profile.get('profile_on_file', False)
        rule_based_risk_score = financial_risk.get('rule_based_risk_score', 50)

        def _fmt(value, suffix=""):
            return "Not on file (new applicant)" if value is None else f"{value}{suffix}"

        internal_history_note = (
            ""
            if profile_on_file
            else (
                "\nNOTE: This applicant has no internal employment/credit history record on file. "
                "This is expected for a new/first-time applicant and is NOT itself a red flag or data "
                "inconsistency - do not treat 'Not on file' as contradicting the credit score or as "
                "grounds for manual review on its own. Base the decision primarily on the credit score, "
                "DTI ratio, and loan-to-income ratio provided below.\n"
            )
        )

        prompt = f"""You are a loan underwriting expert. Analyze the following loan application data and provide a decision.

APPLICANT PROFILE:
- Income Stability Score: {applicant_profile.get('income_stability_score', 0)}/100
- Employment Risk: {applicant_profile.get('employment_risk', 'Unknown')}
- Employment Type: {applicant_profile.get('employment_type', 'Unknown')}
- Years at Current Job: {_fmt(applicant_profile.get('employment_tenure_years'))}
- Internal Credit History Summary:
  - Payment On Time %: {_fmt(applicant_profile.get('payment_on_time_percentage'), '%')}
  - Years of History: {_fmt(applicant_profile.get('credit_history_years'))}
  - Delinquencies: {_fmt(applicant_profile.get('delinquencies_count'))}
- Application Completeness: {applicant_profile.get('completeness_status', 'Complete')}
{internal_history_note}
FINANCIAL RISK ASSESSMENT:
- Debt-to-Income Ratio: {financial_risk.get('debt_to_income_ratio', 0):.2%}
- DTI Classification: {financial_risk.get('dti_classification', 'Unknown')}
- Credit Score: {financial_risk.get('credit_score', 0)}
- Credit Score Risk Level: {financial_risk.get('credit_score_risk_level', 'Unknown')}
- Loan Amount Risk: {financial_risk.get('loan_amount_risk_level', 'Unknown')}
- Loan to Income Ratio: {financial_risk.get('loan_to_income_ratio', 0):.2f}
- Anomaly Detected: {financial_risk.get('anomaly_detected', False)}
- Risk Reasoning: {financial_risk.get('reasoning', 'No specific concerns')}
- Rule-Based Baseline Risk Score: {rule_based_risk_score}/100 (computed deterministically from the DTI, credit-score, and loan-to-income risk-weight tables above)

Based on this analysis, provide your decision in the following JSON format:
{{
    "classification": "APPROVED|REJECTED|REQUIRES_MANUAL_REVIEW",
    "risk_score": <0-100>,
    "confidence_level": <0-100>,
    "key_factors": ["factor1", "factor2", ...],
    "explanation": "Clear explanation of the decision"
}}

Use the Rule-Based Baseline Risk Score above as your starting point for `risk_score`. You may refine it up or
down by at most {RISK_SCORE_CLAMP_MARGIN} points based on holistic judgment (e.g. anomalies, employment risk,
new-applicant status) - if you deviate, state why in the explanation. Respond ONLY with valid JSON, no other text."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
        except APIError as e:
            logger.error(f"Claude API call failed: {e}", exc_info=True)
            return {
                "classification": "REQUIRES_MANUAL_REVIEW",
                "risk_score": 50,
                "confidence_level": 30,
                "key_factors": ["LLM API call failed"],
                "explanation": "Manual review required due to LLM service error"
            }

        if not response.content or len(response.content) == 0:
            logger.error(f"Empty response from Claude: {response}")
            return {
                "classification": "REQUIRES_MANUAL_REVIEW",
                "risk_score": 50,
                "confidence_level": 30,
                "key_factors": ["Unable to get LLM response"],
                "explanation": "Manual review required due to LLM communication error"
            }

        # response.content[0] is not necessarily the answer: if extended thinking is
        # enabled, the model emits a ThinkingBlock before the TextBlock, so scan for the
        # first block that actually has text rather than assuming index 0.
        response_text = None
        for content_item in response.content:
            if getattr(content_item, 'type', None) == 'text':
                response_text = getattr(content_item, 'text', None)
                break

        if response_text is None:
            logger.error(f"No text block found in response content: {response.content}")
            return {
                "classification": "REQUIRES_MANUAL_REVIEW",
                "risk_score": 50,
                "confidence_level": 30,
                "key_factors": ["Invalid LLM response format"],
                "explanation": "Manual review required due to invalid response format"
            }

        logger.info(f"Claude response: {response_text}")

        try:
            # Remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:].lstrip('\n')
            elif response_text.startswith("```"):
                response_text = response_text[3:].lstrip('\n')
            if response_text.endswith("```"):
                response_text = response_text[:-3].rstrip('\n')
            response_text = response_text.strip()

            decision_data = json.loads(response_text)
            key_factors = decision_data.get("key_factors", [])

            raw_risk_score = int(decision_data.get("risk_score", rule_based_risk_score))
            lower_bound = max(0, rule_based_risk_score - RISK_SCORE_CLAMP_MARGIN)
            upper_bound = min(100, rule_based_risk_score + RISK_SCORE_CLAMP_MARGIN)
            clamped_risk_score = max(lower_bound, min(upper_bound, raw_risk_score))

            if clamped_risk_score != raw_risk_score:
                key_factors = list(key_factors) + ["Risk score bounded by rule-based baseline for auditability"]

            return {
                "classification": decision_data.get("classification", "REQUIRES_MANUAL_REVIEW"),
                "risk_score": clamped_risk_score,
                "confidence_level": int(decision_data.get("confidence_level", 50)),
                "key_factors": key_factors,
                "explanation": decision_data.get("explanation", "Decision based on financial profile analysis")
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}\nResponse text: {response_text}")
            return {
                "classification": "REQUIRES_MANUAL_REVIEW",
                "risk_score": 50,
                "confidence_level": 30,
                "key_factors": ["Unable to parse LLM response"],
                "explanation": "Manual review required due to analysis error"
            }
