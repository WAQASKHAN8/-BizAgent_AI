from datetime import datetime, timedelta
import json
from database.db import get_connection, log_audit, create_approval_request

class CRMTool:
    """Tooling for Lead Management, Automated Follow-ups, Opt-outs and Escalations."""

    @staticmethod
    def get_all_leads():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM leads ORDER BY score DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def score_lead(company_size: int, budget: float, timeline_months: int) -> int:
        """Calculates a normalized lead qualification score (0-100)."""
        score = 30  # Baseline
        if budget >= 10000:
            score += 35
        elif budget >= 5000:
            score += 20
        elif budget >= 1000:
            score += 10

        if company_size >= 100:
            score += 25
        elif company_size >= 20:
            score += 15

        if timeline_months <= 1:
            score += 15
        elif timeline_months <= 3:
            score += 10

        return min(score, 100)

    @staticmethod
    def add_lead(name: str, email: str, company: str, deal_value: float, score: int = 50, notes: str = ""):
        conn = get_connection()
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("""
        INSERT INTO leads (name, email, company, deal_value, score, stage, opt_out, last_contact, notes)
        VALUES (?, ?, ?, ?, ?, 'New', 0, ?, ?)
        """, (name, email, company, deal_value, score, now_str, notes))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        log_audit("Sales Agent", "ADD_LEAD", f"New lead added: #{new_id} ({company}) with deal value ${deal_value:,.2f}")
        return new_id

    @staticmethod
    def process_opt_out(email: str) -> dict:
        """
        Compliance Requirement: Handles customer opt-out immediately.
        Marks lead as opt_out=1, halts all automated sequences.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE leads SET opt_out = 1, stage = 'Lost - Opt Out' WHERE email = ?", (email,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()

        log_audit("Sales Agent", "OPT_OUT_PROCESSED", f"Opt-out recorded for email {email}. Automated communications halted.")
        return {
            "status": "SUCCESS" if affected > 0 else "NOT_FOUND",
            "message": f"Successfully opted out {email}. Compliance flag set to opt_out=True."
        }

    @staticmethod
    def trigger_discount_escalation(lead_id: int, discount_pct: float, deal_value: float, client_name: str) -> dict:
        """
        Escalation rule: Any discount > 15% or deal value > $10,000 with custom terms
        cannot be approved autonomously by the AI Agent. It requires Human Approval.
        """
        if discount_pct > 15.0 or deal_value > 10000.0:
            req_id = create_approval_request(
                agent_name="Sales Agent",
                action_type="HIGH_DISCOUNT_APPROVAL",
                title=f"Discount Approval ({discount_pct}%) for {client_name}",
                description=f"Sales agent negotiated a {discount_pct}% discount on deal value of ${deal_value:,.2f}. Exceeds autonomous threshold (15%).",
                payload={"lead_id": lead_id, "discount_pct": discount_pct, "deal_value": deal_value, "client_name": client_name}
            )
            return {
                "action_taken": "ESCALATED_TO_HUMAN",
                "approval_id": req_id,
                "message": f"Discount of {discount_pct}% exceeds policy limit (15%). Request #{req_id} sent to Human Approval Center."
            }
        else:
            return {
                "action_taken": "AUTO_APPROVED",
                "approval_id": None,
                "message": f"Discount of {discount_pct}% is within safe autonomous limits (<=15%). Approved."
            }

    @staticmethod
    def generate_followup_message(lead_name: str, company: str, stage: str, deal_value: float) -> str:
        """Generates tailored sales follow-up email draft."""
        return (
            f"Subject: Next Steps for {company} & BizAgent Partnership\n\n"
            f"Hi {lead_name},\n\n"
            f"I hope you're having a productive week. Following up on our recent discussion regarding "
            f"the AI Agent deployment for {company} (valued at ${deal_value:,.2f}).\n\n"
            f"Based on your current stage ({stage}), we have prepared an implementation roadmap "
            f"that can accelerate your routine operations by over 60%.\n\n"
            f"Would you be open for a brief 20-minute alignment session this Thursday or Friday?\n\n"
            f"Best regards,\n"
            f"BizAgent AI Sales Operations Team\n"
            f"[Reply 'UNSUBSCRIBE' at any time to opt-out]"
        )
