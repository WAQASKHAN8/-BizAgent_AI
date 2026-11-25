from database.db import (
    get_connection,
    log_audit,
    create_approval_request,
    is_opted_out,
    record_opt_out,
    log_email_message
)
from tools.crm_tool import CRMTool
from tools.gemini_service import generate_response

class SalesAgent:
    """
    Agent 3: Sales & Lead Management Agent
    
    Responsibilities:
    - Capture new inbound leads.
    - Store customer name, email, phone number, company, source, and inquiry.
    - Assign lead status: New, Contacted, Interested, Qualified, Converted, Lost.
    - Evaluate lead interest and priority score (0-100).
    - Generate personalized follow-up messages.
    - Create follow-up schedules.
    - Track customer responses.
    - Update lead records in database.
    - Escalate high-value deals and discounts > 15% to Human Approval.
    - Enforce CAN-SPAM / GDPR opt-out suppression immediately.
    """
    NAME = "Sales & Lead Agent"
    ROLE = "Lead Qualification, Pipeline Management & Automated Follow-ups"
    PERMITTED_ACTIONS = [
        "capture_lead",
        "score_lead",
        "draft_followup",
        "update_pipeline",
        "record_optout",
        "schedule_followup",
        "request_discount",
        "request_campaign_approval"
    ]

    @classmethod
    def qualify_lead(cls, name: str, email: str, company: str, budget: float, company_size: int = 25, timeline_months: int = 1, notes: str = "", phone: str = "") -> dict:
        # Check permanent suppression list first
        if is_opted_out(email):
            log_audit(cls.NAME, "LEAD_CAPTURE_SUPPRESSED", f"Attempted to qualify opted-out contact {email}. Marked as Lost - Opt Out.", status="BLOCKED")
            return {
                "lead_id": None,
                "score": 0,
                "qualification": "Suppressed (Opted Out)",
                "blocked": True,
                "reason": "Email address is on the permanent suppression list."
            }

        score = CRMTool.score_lead(company_size, budget, timeline_months)
        lead_id = CRMTool.add_lead(name, email, company, budget, score, notes)

        # High-value deal alert (> $10,000)
        escalation_info = None
        if budget >= 10000.0:
            app_id = create_approval_request(
                agent_name=cls.NAME,
                action_type="HIGH_VALUE_DEAL_NOTIFY",
                title=f"VIP Enterprise Lead: {company} (${budget:,.2f})",
                description=f"High-priority lead scored {score}/100 with budget of ${budget:,.2f}. Assigned for senior account executive review.",
                risk_level="Medium",
                proposed_operation="Assign executive account representative and custom terms",
                payload={"lead_id": lead_id, "company": company, "budget": budget, "score": score}
            )
            escalation_info = {"escalated": True, "approval_id": app_id}

        return {
            "lead_id": lead_id,
            "score": score,
            "qualification": "Enterprise / High Priority" if score >= 80 else "Mid-Market" if score >= 50 else "Standard",
            "escalation": escalation_info
        }

    @classmethod
    def request_proposal_approval(cls, lead_id: int, client_name: str, email: str, deal_value: float, proposal_text: str) -> int:
        """
        Governance trigger: Outbound business proposals require human approval prior to dispatch.
        """
        app_id = create_approval_request(
            agent_name=cls.NAME,
            action_type="OUTBOUND_EMAIL_APPROVAL",
            title=f"Approve Outbound Proposal for {client_name}",
            description=f"Proposal for deal valued at ${deal_value:,.2f} prepared for {client_name} ({email}).",
            risk_level="Low",
            proposed_operation="Send external sales email to prospective client",
            payload={"lead_id": lead_id, "recipient_name": client_name, "recipient_email": email, "deal_value": deal_value, "body": proposal_text}
        )
        return app_id

    @classmethod
    def process_followup(cls, lead_id: int) -> dict:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            lead = cursor.fetchone()
            if not lead:
                return {"error": "Lead not found", "blocked": True}

            lead_dict = dict(lead)

            # Check opt-out status (Mandatory compliance)
            if lead_dict.get("opt_out") == 1 or is_opted_out(lead_dict.get("email", "")):
                log_audit(cls.NAME, "FOLLOWUP_BLOCKED", f"Halted follow-up for {lead_dict['email']}: User previously opted out.", status="BLOCKED")
                return {
                    "blocked": True,
                    "reason": "Lead has opted out of communication (opt_out=True). No messages permitted under anti-spam regulations."
                }

            followup_text = CRMTool.generate_followup_message(
                lead_dict["name"], lead_dict["company"], lead_dict["stage"], lead_dict["deal_value"]
            )

            log_audit(cls.NAME, "DRAFT_FOLLOWUP", f"Drafted follow-up for {lead_dict['name']} at {lead_dict['company']}")
            return {
                "blocked": False,
                "lead": lead_dict,
                "followup_email": followup_text
            }
        finally:
            conn.close()

    @classmethod
    def request_discount(cls, lead_id: int, discount_pct: float) -> dict:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            lead = cursor.fetchone()
            if not lead:
                return {"error": "Lead not found"}

            lead_dict = dict(lead)
            result = CRMTool.trigger_discount_escalation(
                lead_id, discount_pct, lead_dict["deal_value"], lead_dict["name"]
            )
            return result
        finally:
            conn.close()

    @classmethod
    def handle_opt_out(cls, email: str, phone: str = "") -> dict:
        record_opt_out(email, phone, reason="Customer requested unsubscribe")
        return {
            "status": "SUCCESS",
            "message": f"Successfully processed opt-out for {email}. Permanently suppressed across all marketing sequences."
        }
