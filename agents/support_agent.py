from datetime import datetime
from database.db import get_connection, log_audit, create_approval_request
from tools.gemini_service import generate_response
from tools.security_tool import SecurityGuardrails

class SupportAgent:
    """
    Agent 2: Customer Support Agent
    
    Responsibilities:
    - Receive and understand customer messages.
    - Answer frequently asked questions.
    - Retrieve information from business knowledge base.
    - Identify customer complaints and negative sentiment.
    - Categorize enquiries (General, Billing, Technical, Sales Inquiry).
    - Create support tickets in database.
    - Forward sales-related enquiries to the Sales Agent.
    - Escalate difficult, unresolved, or refund-related issues to a human representative.
    
    Restrictions:
    - Must NOT invent business policies or product specifications.
    - Must NOT promise refunds, fee waivers, or discounts autonomously.
    - Must escalate uncertain or sensitive cases to Human Approval.
    """
    NAME = "Customer Support Agent"
    ROLE = "Customer Enquiry, Complaint Triage & Support Ticketing"
    PERMITTED_ACTIONS = [
        "triage_enquiry",
        "create_ticket",
        "resolve_ticket",
        "search_faq",
        "categorize_enquiry",
        "analyze_sentiment",
        "forward_to_sales",
        "request_refund"
    ]

    KNOWLEDGE_BASE = {
        "hours": "Our business working hours are 09:00 - 18:00 PKT (Mon-Fri).",
        "pricing": "Our starter tier is $2,500/year, Professional is $7,500/year, and Enterprise starts at $12,500/year with custom SLA.",
        "integration": "We support native SQLite, PostgreSQL, REST APIs, Calendar sync, and webhook integrations.",
        "security": "BizAgent employs role-based access control, prompt injection filters, and automatic PII masking.",
        "refund_policy": "Refund requests are subject to administrative review within 5-7 business days."
    }

    @staticmethod
    def analyze_sentiment(text: str) -> str:
        lowered = text.lower()
        if any(w in lowered for w in ["angry", "upset", "broken", "terrible", "worst", "fraud", "refund", "charged twice", "unacceptable"]):
            return "Negative"
        elif any(w in lowered for w in ["thank", "great", "awesome", "excellent", "good", "pleased", "love"]):
            return "Positive"
        return "Neutral"

    @classmethod
    def handle_enquiry(cls, customer_name: str, email: str, subject: str, message: str) -> dict:
        sentiment = cls.analyze_sentiment(message)
        lowered = message.lower()

        # Categorization
        is_sales = any(w in lowered for w in ["pricing", "cost", "quote", "interested in", "buy", "purchase", "services"])
        is_billing = any(w in lowered for w in ["invoice", "charged", "billing", "fee", "refund", "receipt"])
        is_complaint = sentiment == "Negative" or "broken" in lowered or "error" in lowered

        category = "Sales Inquiry" if is_sales else ("Billing" if is_billing else ("Complaint" if is_complaint else "General"))
        priority = "Critical" if "refund" in lowered and "twice" in lowered else ("High" if sentiment == "Negative" or "urgent" in lowered else "Medium")

        conn = get_connection()
        try:
            cursor = conn.cursor()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            cursor.execute("""
            INSERT INTO tickets (customer_name, email, subject, message, priority, status, category, sentiment, assigned_agent, created_at)
            VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, ?, ?)
            """, (customer_name, email, subject, message, priority, category, sentiment, cls.NAME, now_str))
            ticket_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()

        log_audit(cls.NAME, "CREATE_TICKET", f"Created ticket #{ticket_id} for {customer_name} [Category: {category}, Priority: {priority}, Sentiment: {sentiment}]")

        # Human Approval Trigger for Refunds / Billing adjustments
        approval_id = None
        if "refund" in lowered or "charged twice" in lowered or "billing dispute" in lowered:
            approval_id = create_approval_request(
                agent_name=cls.NAME,
                action_type="REFUND_AUTHORIZATION",
                title=f"Refund Request from {customer_name} (Ticket #{ticket_id})",
                description=f"Customer reported billing dispute: '{message[:100]}...'. Requires finance supervisor authorization.",
                risk_level="Critical",
                proposed_operation="Authorize billing refund or credit adjustment",
                payload={"ticket_id": ticket_id, "customer": customer_name, "email": email, "amount": 499.0}
            )

        # Knowledge base lookup for instant context
        kb_context = ""
        for k, v in cls.KNOWLEDGE_BASE.items():
            if k in lowered:
                kb_context += f"KB Info ({k}): {v}\n"

        # AI Response generation
        reply = generate_response(
            f"Customer Message: {message}\nKnowledge Base: {kb_context}",
            system_prompt=(
                "You are an empathetic, highly professional Customer Support Agent for BizAgent AI. "
                "Acknowledge the customer's request, confirm their ticket has been registered with priority, "
                "and explain next steps. If this is a sales inquiry, mention that our Sales Specialist has been looped in. "
                "If it requires billing review or a refund, clarify that it has been escalated to management."
            )
        )

        return {
            "ticket_id": ticket_id,
            "category": category,
            "sentiment": sentiment,
            "priority": priority,
            "is_sales_lead": is_sales,
            "reply": reply,
            "approval_required": approval_id is not None,
            "approval_id": approval_id
        }

    @staticmethod
    def get_tickets(status=None):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM tickets WHERE status = ? ORDER BY id DESC", (status,))
            else:
                cursor.execute("SELECT * FROM tickets ORDER BY id DESC")
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()
