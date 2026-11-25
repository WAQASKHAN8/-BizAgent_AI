import re
from database.db import log_audit, create_approval_request

class SecurityGuardrails:
    """
    Enterprise Security & Guardrail layer protecting against:
    - Prompt injections & jailbreak attacks
    - PII data leakage (Credit Cards, Phone Numbers, SSNs, Passwords)
    - Unauthorized agent boundary violations
    - Unsanctioned database modifications
    - Opt-out / GDPR suppression violations
    """

    INJECTION_PATTERNS = [
        r"ignore (all )?previous instructions",
        r"system prompt reveal",
        r"bypass (all )?security",
        r"act as root",
        r"drop table",
        r"delete from",
        r"truncate table",
        r"reveal your secrets",
        r"give me your api key",
        r"disregard (all )?safety",
        r"jailbreak mode",
        r"ignore guardrails"
    ]

    PERMITTED_ACTIONS = {
        "AI Orchestrator Agent": [
            "route_intent", "decompose_task", "synthesize_response", "delegate_task", "escalate_to_human", "record_agent_activity"
        ],
        "Coordinator Agent": [
            "route_intent", "decompose_task", "synthesize_response", "delegate_task", "escalate_to_human", "record_agent_activity"
        ],
        "Customer Support Agent": [
            "triage_enquiry", "create_ticket", "resolve_ticket", "search_faq", "categorize_enquiry", "analyze_sentiment", "forward_to_sales", "request_refund"
        ],
        "Support Agent": [
            "triage_enquiry", "create_ticket", "resolve_ticket", "search_faq", "categorize_enquiry", "analyze_sentiment", "forward_to_sales", "request_refund"
        ],
        "Sales & Lead Agent": [
            "capture_lead", "score_lead", "draft_followup", "update_pipeline", "record_optout", "schedule_followup", "request_discount", "request_campaign_approval"
        ],
        "Sales Agent": [
            "capture_lead", "score_lead", "draft_followup", "update_pipeline", "record_optout", "schedule_followup", "request_discount", "request_campaign_approval"
        ],
        "Appointment & Scheduling Agent": [
            "check_availability", "check_slots", "book_appointment", "book_meeting", "reschedule_meeting", "cancel_meeting", "detect_conflicts", "send_reminder"
        ],
        "Appointment Agent": [
            "check_availability", "check_slots", "book_appointment", "book_meeting", "reschedule_meeting", "cancel_meeting", "detect_conflicts", "send_reminder"
        ],
        "Reporting & Analytics Agent": [
            "aggregate_kpis", "generate_digest", "detect_anomalies", "calculate_conversion", "export_report"
        ],
        "Reporting Agent": [
            "aggregate_kpis", "generate_digest", "detect_anomalies", "calculate_conversion", "export_report"
        ],
        "Administration Agent": [
            "organize_records", "manage_admin_tasks", "create_task", "complete_task", "generate_admin_doc", "prepare_meeting_summary", "check_system_health", "request_setting_change", "request_record_purge"
        ]
    }

    # Actions that unconditionally require Human-in-the-Loop Approval
    SENSITIVE_ACTIONS_REQUIRING_APPROVAL = [
        "discounts_exceeding_threshold",
        "refund_authorization",
        "bulk_sales_campaign",
        "permanent_record_deletion",
        "critical_setting_change",
        "vip_sla_deviation",
        "cancel_high_priority_appointment"
    ]

    @classmethod
    def inspect_prompt(cls, user_text: str) -> dict:
        """Checks for prompt injection attempts and dangerous commands."""
        lowered = user_text.lower()
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, lowered):
                return {
                    "is_safe": False,
                    "flag": "PROMPT_INJECTION_DETECTED",
                    "reason": f"Input matched security filter pattern: '{pattern}'"
                }
        return {"is_safe": True, "flag": "CLEAN", "reason": "No threats detected."}

    @staticmethod
    def mask_pii(text: str) -> str:
        """Redacts sensitive PII (Phone numbers, Credit cards, SSNs) before LLM logging."""
        # Mask credit cards (13-19 digits, with spaces or dashes)
        text = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_CREDIT_CARD]", text)
        # Mask phone numbers
        text = re.sub(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[REDACTED_PHONE]", text)
        # Mask SSN
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", text)
        return text

    @classmethod
    def check_agent_boundary(cls, agent_name: str, requested_action: str) -> bool:
        """
        Enforces strict role-based action boundaries for each agent:
        Support cannot modify pricing.
        Sales cannot book technical SLA waivers without approval.
        Admin cannot delete records without approval.
        """
        allowed = cls.PERMITTED_ACTIONS.get(agent_name, [])
        return requested_action in allowed

    @classmethod
    def enforce_action_permission(cls, agent_name: str, action: str, context: dict = None) -> dict:
        """
        Authorizes or blocks an action before execution.
        Returns: {"allowed": bool, "requires_approval": bool, "reason": str}
        """
        # 1. Boundary check
        if not cls.check_agent_boundary(agent_name, action):
            log_audit(agent_name, "SECURITY_BOUNDARY_VIOLATION", f"Agent attempted unauthorized action: '{action}'", status="BLOCKED")
            return {
                "allowed": False,
                "requires_approval": False,
                "reason": f"Action '{action}' is strictly outside the authorized role boundaries of {agent_name}."
            }

        # 2. Check if specific parameters trigger approval
        if action in ["request_discount", "apply_discount"]:
            disc = float(context.get("discount_pct", 0) if context else 0)
            if disc > 15.0:
                return {
                    "allowed": True,
                    "requires_approval": True,
                    "reason": f"Discount of {disc}% exceeds 15% threshold; requires manager sign-off."
                }

        if action in ["request_refund", "issue_refund"]:
            return {
                "allowed": True,
                "requires_approval": True,
                "reason": "Issuing merchant refunds always requires Human Approval."
            }

        if action in ["request_setting_change", "modify_critical_settings"]:
            return {
                "allowed": True,
                "requires_approval": True,
                "reason": "Modifying business critical settings requires Admin approval."
            }

        if action in ["request_record_purge", "permanent_delete_records"]:
            return {
                "allowed": True,
                "requires_approval": True,
                "reason": "Permanent data deletion requires Admin approval."
            }

        return {"allowed": True, "requires_approval": False, "reason": "Action authorized."}
