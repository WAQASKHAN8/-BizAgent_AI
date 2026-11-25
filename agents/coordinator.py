import json
import re
import uuid
from datetime import datetime
from config import client, DEFAULT_MODEL, FALLBACK_MODELS, API_KEY
from agents.support_agent import SupportAgent
from agents.sales_agent import SalesAgent
from agents.appointment_agent import AppointmentAgent
from agents.reporting_agent import ReportingAgent
from agents.administration_agent import AdministrationAgent
from database.db import log_audit, log_agent_message, create_notification, get_business_settings, is_opted_out
from tools.gemini_service import generate_response
from tools.security_tool import SecurityGuardrails

class CoordinatorAgent:
    """
    Agent 1: AI Orchestrator Agent (Central Coordinator & Decision Controller)
    
    Responsibilities:
    - Receive incoming business requests.
    - Understand user intent with LLM-powered decomposition.
    - Identify which specialized agent(s) should handle each sub-task.
    - Break complex requests into smaller executable tasks.
    - Delegate tasks to specialized agents (Support, Sales, Appointments, Reporting, Administration).
    - Share structured context & information between agents.
    - Collect, validate, and synthesize agent responses.
    - Track task execution status & retry failed tasks if appropriate.
    - Enforce security boundaries and escalate sensitive operations to Human Approval.
    - Return a coherent, professional synthesized response to the user.
    """
    NAME = "AI Orchestrator Agent"
    ROLE = "Central Coordinator & Decision-Making Controller"

    @classmethod
    def decompose_query(cls, user_message: str) -> dict:
        """
        Uses Gemini LLM to analyze the user message and determine which specialized agents must act,
        along with extracted structured parameters for each agent.
        """
        prompt = f"""
You are the AI Orchestrator Agent for BizAgent AI Multi-Agent System.
Analyze the user request and determine which of the 6 specialized agents must act:

Specialized Agents:
1. "support": Customer Support Agent (enquiries, complaints, bug reports, refund requests, support tickets)
2. "sales": Sales & Lead Agent (pricing inquiries, software purchase, proposals, lead capture, discount requests, follow-ups)
3. "appointment": Appointment & Scheduling Agent (booking meetings, checking available time slots, rescheduling, cancelling)
4. "reporting": Reporting & Analytics Agent (sales metrics, KPI inquiries, conversion rates, daily/weekly executive digests)
5. "admin": Administration Agent (internal administrative tasks, meeting minutes, records organization, system settings)
6. "general": General enterprise assistance

User Request: "{user_message}"

Respond strictly with a valid JSON object matching this schema:
{{
  "intent_summary": "1-sentence executive summary of user request",
  "active_agents": ["sales", "appointment"],  // list of required agent keys
  "sales_details": {{
      "company": "Company Name if mentioned or Prospect Corp",
      "deal_value": 5000.0,
      "discount_pct": 0.0,
      "notes": "summary of sales requirement"
  }},
  "support_details": {{
      "subject": "Extracted issue subject",
      "is_refund": false,
      "is_complaint": false
  }},
  "appointment_details": {{
      "service": "Product Demonstration & Architecture Review",
      "preferred_time": "tomorrow 14:00"
  }},
  "reporting_details": {{
      "requested_kpi": "all"
  }},
  "admin_details": {{
      "task_title": "Administrative action if requested",
      "category": "Operations"
  }}
}}
Respond with ONLY the JSON object, without markdown fences or backticks.
"""
        plan = None
        if client and API_KEY:
            for model_name in FALLBACK_MODELS:
                try:
                    res = client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    if res and res.text:
                        raw = res.text.strip()
                        raw = re.sub(r"^```(json)?", "", raw).strip()
                        raw = re.sub(r"```$", "", raw).strip()
                        plan = json.loads(raw)
                        break
                except Exception:
                    continue

        if not plan:
            plan = cls._fallback_decomposition(user_message)

        return plan

    @classmethod
    def _fallback_decomposition(cls, text: str) -> dict:
        lowered = text.lower()
        active = []

        if any(w in lowered for w in ["support", "ticket", "issue", "bug", "broken", "refund", "charged", "help", "complaint"]):
            active.append("support")
        if any(w in lowered for w in ["buy", "purchase", "price", "pricing", "discount", "quote", "sales", "lead", "deal", "cost", "interested in your software", "services"]):
            active.append("sales")
        if any(w in lowered for w in ["book", "appointment", "meeting", "schedule", "call", "demo", "calendar", "slot", "arrange a meeting"]):
            active.append("appointment")
        if any(w in lowered for w in ["report", "analytics", "kpi", "performance", "metrics", "digest", "summary", "stats", "conversion"]):
            active.append("reporting")
        if any(w in lowered for w in ["admin", "task", "meeting minutes", "memo", "health", "system setting", "organize"]):
            active.append("admin")

        if not active:
            active = ["general"]

        disc_match = re.search(r"(\d+)\s*%", text)
        disc_pct = float(disc_match.group(1)) if disc_match else 0.0

        return {
            "intent_summary": "Processed multi-agent business inquiry",
            "active_agents": active,
            "sales_details": {"company": "Client", "deal_value": 7500.0, "discount_pct": disc_pct, "notes": text[:100]},
            "support_details": {
                "subject": "Customer Inquiry",
                "is_refund": "refund" in lowered or "charged" in lowered,
                "is_complaint": "broken" in lowered or "terrible" in lowered or "angry" in lowered
            },
            "appointment_details": {"service": "Product Demonstration & Architecture Review", "preferred_time": "tomorrow 14:00"},
            "reporting_details": {"requested_kpi": "all"},
            "admin_details": {"task_title": "Routine Administrative Operation", "category": "Operations"}
        }

    @classmethod
    def route_request(cls, user_message: str, customer_info: dict = None, task_id: str = None) -> dict:
        """
        Main multi-agent dispatch pipeline with structured messaging and HITL governance.
        """
        task_id = task_id or f"TASK-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        customer_info = customer_info or {"name": "Business Client", "email": "client@enterprise.com", "company": "Prospect Corp"}

        # 1. Security & Guardrail Check
        security_check = SecurityGuardrails.inspect_prompt(user_message)
        if not security_check["is_safe"]:
            log_audit(cls.NAME, "SECURITY_BLOCK", f"Blocked unsafe input: {security_check['reason']}", status="BLOCKED")
            log_agent_message(
                task_id=task_id,
                sender_agent=cls.NAME,
                receiver_agent="Security Guardrails",
                task_description="Inspect incoming prompt for injection and boundary violations",
                customer_data=customer_info,
                input_context=user_message,
                output_result=f"BLOCKED: {security_check['reason']}",
                status="FAILED",
                approval_requirement=0
            )
            return {
                "task_id": task_id,
                "agent": cls.NAME,
                "intent": "SECURITY_VIOLATION",
                "status": "BLOCKED",
                "response": f"🛡️ **Security Alert:** Request was blocked by BizAgent Guardrails. Reason: {security_check['reason']}",
                "actions": ["Triggered SecurityGuardrails filter", "Prevented malicious injection attempt"],
                "approval_required": False,
                "structured_messages": [],
                "agent_reports": {}
            }

        masked_message = SecurityGuardrails.mask_pii(user_message)

        # 2. Intent Analysis & Sub-Task Planning
        plan = cls.decompose_query(masked_message)
        active_agents = plan.get("active_agents", ["general"])

        structured_messages = []
        all_actions = []
        approval_flags = []
        response_sections = []
        agent_reports = {}

        # Log Orchestrator initial plan
        log_agent_message(
            task_id=task_id,
            sender_agent="User Interface",
            receiver_agent=cls.NAME,
            task_description="Receive business inquiry and decompose sub-tasks",
            customer_data=customer_info,
            input_context=masked_message,
            output_result=f"Intent: {plan.get('intent_summary')} | Target Agents: {', '.join(active_agents)}",
            status="COMPLETED",
            approval_requirement=0
        )

        # ----------------------------------------------------------------------
        # Agent 2: Customer Support Agent
        # ----------------------------------------------------------------------
        if "support" in active_agents:
            supp_desc = "Process customer enquiry, evaluate sentiment, triage support ticket"
            supp_res = SupportAgent.handle_enquiry(
                customer_name=customer_info.get("name", "Client"),
                email=customer_info.get("email", "client@enterprise.com"),
                subject=plan.get("support_details", {}).get("subject", "Customer Support Inquiry"),
                message=masked_message
            )
            agent_reports["Customer Support Agent"] = supp_res
            all_actions.append(f"🎧 Support Agent: Created Ticket #{supp_res['ticket_id']} (Sentiment: {supp_res['sentiment']}, Priority: {supp_res['priority']})")
            
            if supp_res["approval_required"]:
                approval_flags.append(f"Support Agent: Refund Request #{supp_res['approval_id']} sent to Human Approval Center")
            
            log_agent_message(
                task_id=task_id,
                sender_agent=cls.NAME,
                receiver_agent=SupportAgent.NAME,
                task_description=supp_desc,
                customer_data=customer_info,
                input_context=masked_message,
                output_result=f"Ticket #{supp_res['ticket_id']} logged. Sentiment: {supp_res['sentiment']}",
                status="WAITING_APPROVAL" if supp_res["approval_required"] else "COMPLETED",
                approval_requirement=1 if supp_res["approval_required"] else 0
            )
            response_sections.append(f"**Customer Support Response:**\n{supp_res['reply']}")

        # ----------------------------------------------------------------------
        # Agent 3: Sales & Lead Management Agent
        # ----------------------------------------------------------------------
        if "sales" in active_agents:
            s_det = plan.get("sales_details", {})
            company = customer_info.get("company") or s_det.get("company", "Prospect Corp")
            deal_val = float(s_det.get("deal_value", 7500.0) or 7500.0)
            disc_pct = float(s_det.get("discount_pct", 0.0) or 0.0)

            # Check Opt-out compliance first
            client_email = customer_info.get("email", "client@enterprise.com")
            if is_opted_out(client_email):
                all_actions.append(f"🛑 Sales Agent: Halted follow-up sequences. Recipient {client_email} is on permanent opt-out suppression list.")
                log_agent_message(
                    task_id=task_id,
                    sender_agent=cls.NAME,
                    receiver_agent=SalesAgent.NAME,
                    task_description="Verify marketing opt-out status prior to lead outreach",
                    customer_data=customer_info,
                    input_context=f"Email: {client_email}",
                    output_result="BLOCKED: Recipient opted out of marketing",
                    status="BLOCKED",
                    approval_requirement=0
                )
                response_sections.append(f"**Sales & Lead Notice:**\nRecipient `{client_email}` is on the permanent suppression list. In accordance with anti-spam compliance (CAN-SPAM/GDPR), automated marketing communications are suspended.")
            else:
                # Capture & qualify lead
                qual = SalesAgent.qualify_lead(
                    name=customer_info.get("name", "Client"),
                    email=client_email,
                    company=company,
                    budget=deal_val,
                    company_size=35,
                    timeline_months=1,
                    notes=masked_message
                )
                all_actions.append(f"📈 Sales Agent: Captured & Qualified Lead #{qual['lead_id']} with score {qual['score']}/100 ({qual['qualification']})")

                # Check discount escalation
                disc_approval_id = None
                if disc_pct > 0:
                    disc_res = SalesAgent.request_discount(qual["lead_id"], disc_pct)
                    all_actions.append(f"📈 Sales Agent: Evaluated {disc_pct}% discount ({disc_res['action_taken']})")
                    if disc_res["action_taken"] == "ESCALATED_TO_HUMAN":
                        disc_approval_id = disc_res.get("approval_id")
                        approval_flags.append(f"Sales Agent: Discount of {disc_pct}% exceeds autonomous policy (15%) -> Approval Request #{disc_approval_id}")

                # Check external communication approval policy
                settings = get_business_settings()
                require_approval_ext = settings.get("require_approval_for_external_comms", "true").lower() == "true"
                proposal_approval_id = None
                if require_approval_ext and not disc_approval_id:
                    proposal_approval_id = SalesAgent.request_proposal_approval(
                        lead_id=qual["lead_id"],
                        client_name=customer_info.get("name", "Client"),
                        email=client_email,
                        deal_value=deal_val,
                        proposal_text=f"Enterprise Development Proposal for {company} (${deal_val:,.2f})"
                    )
                    approval_flags.append(f"Sales Agent: Outbound commercial communication requires Human Approval (#{proposal_approval_id})")

                sales_reply = generate_response(
                    f"Customer Request: {masked_message}\nCompany: {company}\nDeal Value: ${deal_val}\nDiscount Requested: {disc_pct}%",
                    system_prompt=(
                        "You are the Sales & Lead Agent for BizAgent AI. Provide a compelling, professional B2B commercial response. "
                        "Highlight tailored solutions and explain that high-tier discounts or custom terms are submitted to management for review."
                    )
                )

                log_agent_message(
                    task_id=task_id,
                    sender_agent=cls.NAME,
                    receiver_agent=SalesAgent.NAME,
                    task_description="Capture lead, qualify score, and prepare commercial proposal",
                    customer_data=customer_info,
                    input_context=f"Deal Value: ${deal_val}, Discount: {disc_pct}%",
                    output_result=f"Lead #{qual['lead_id']} qualified ({qual['score']}/100)",
                    status="WAITING_APPROVAL" if (disc_approval_id or proposal_approval_id) else "COMPLETED",
                    approval_requirement=1 if (disc_approval_id or proposal_approval_id) else 0
                )

                agent_reports["Sales & Lead Agent"] = {
                    "lead_id": qual["lead_id"],
                    "score": qual["score"],
                    "proposal": sales_reply,
                    "approval_id": disc_approval_id or proposal_approval_id
                }
                response_sections.append(f"**Sales & Commercial Proposal:**\n{sales_reply}")

        # ----------------------------------------------------------------------
        # Agent 4: Appointment & Scheduling Agent
        # ----------------------------------------------------------------------
        if "appointment" in active_agents:
            open_slots = AppointmentAgent.get_open_slots()
            chosen_slot = open_slots[0] if open_slots else "Tomorrow 14:00"
            service_name = plan.get("appointment_details", {}).get("service", "Product Demonstration & Architecture Review")

            book_res = AppointmentAgent.schedule_meeting(
                client_name=customer_info.get("name", "Client"),
                email=customer_info.get("email", "client@enterprise.com"),
                service=service_name,
                slot_time=chosen_slot,
                notes=masked_message[:80]
            )
            agent_reports["Appointment & Scheduling Agent"] = book_res

            if book_res["success"]:
                all_actions.append(f"📅 Appointment Agent: Reserved slot {chosen_slot} (Appt #{book_res['appointment_id']})")
                response_sections.append(f"**Appointment Coordination:**\n✅ {book_res['message']}")
            else:
                all_actions.append(f"📅 Appointment Agent: Scheduling conflict detected on slot {chosen_slot}")
                response_sections.append(f"**Appointment Coordination:**\n⚠️ {book_res['message']}")

            log_agent_message(
                task_id=task_id,
                sender_agent=cls.NAME,
                receiver_agent=AppointmentAgent.NAME,
                task_description=f"Check calendar availability and schedule {service_name}",
                customer_data=customer_info,
                input_context=f"Requested Slot: {chosen_slot}",
                output_result=book_res["message"],
                status="COMPLETED" if book_res["success"] else "CONFLICT_DETECTED",
                approval_requirement=0
            )

        # ----------------------------------------------------------------------
        # Agent 5: Reporting & Analytics Agent
        # ----------------------------------------------------------------------
        if "reporting" in active_agents:
            digest = ReportingAgent.generate_executive_digest()
            kpis = ReportingAgent.get_kpi_summary()
            agent_reports["Reporting & Analytics Agent"] = {"kpis": kpis, "digest": digest}
            all_actions.append(f"📊 Reporting Agent: Calculated real-time KPIs (Pipeline: ${kpis['total_pipeline_value']:,.0f}, Active Leads: {kpis['active_leads']})")
            response_sections.append(f"**Executive Business Report:**\n{digest}")

            log_agent_message(
                task_id=task_id,
                sender_agent=cls.NAME,
                receiver_agent=ReportingAgent.NAME,
                task_description="Compute real-time operational metrics and executive digest from database",
                customer_data=customer_info,
                input_context="Query DB: leads, tickets, appointments, approvals",
                output_result=f"Computed digest: {kpis['active_leads']} leads, SLA: {kpis['sla_compliance_pct']}%",
                status="COMPLETED",
                approval_requirement=0
            )

        # ----------------------------------------------------------------------
        # Agent 6: Administration Agent
        # ----------------------------------------------------------------------
        if "admin" in active_agents:
            task_title = plan.get("admin_details", {}).get("task_title", "General Operational Review")
            admin_task = AdministrationAgent.create_task(
                title=task_title,
                category="Operations",
                priority="Medium",
                notes=f"Created via Orchestrator from request: {masked_message[:80]}"
            )
            health = AdministrationAgent.check_system_health()
            agent_reports["Administration Agent"] = {"task": admin_task, "health": health}
            all_actions.append(f"📁 Administration Agent: Created operational task #{admin_task['task_id']} ('{task_title}')")
            response_sections.append(f"**Administrative Action:**\nTask #{admin_task['task_id']} registered. System health status: `{health['health_status']}` (Pending Approvals: {health['pending_approvals']}, Active Leads: {health['total_leads']}).")

            log_agent_message(
                task_id=task_id,
                sender_agent=cls.NAME,
                receiver_agent=AdministrationAgent.NAME,
                task_description="Create administrative task and evaluate operational health",
                customer_data=customer_info,
                input_context=task_title,
                output_result=f"Admin task #{admin_task['task_id']} registered. Health: {health['health_status']}",
                status="COMPLETED",
                approval_requirement=0
            )

        # Default fallback if no specialized agent was triggered
        if not response_sections:
            gen_reply = generate_response(
                masked_message,
                system_prompt="You are BizAgent AI Orchestrator. Provide clear, professional executive assistance."
            )
            all_actions.append("🤖 Orchestrator Agent: Synthesized general business response")
            response_sections.append(gen_reply)

        final_text = "\n\n---\n\n".join(response_sections)
        primary_agent = ", ".join([f"{a.capitalize()} Agent" for a in active_agents])

        log_audit(cls.NAME, "ORCHESTRATION_COMPLETE", f"Task {task_id} completed across: {', '.join(active_agents)}")

        return {
            "task_id": task_id,
            "agent": primary_agent or cls.NAME,
            "intent": "MULTI_AGENT_COLLABORATION" if len(active_agents) > 1 else active_agents[0].upper(),
            "status": "WAITING_APPROVAL" if len(approval_flags) > 0 else "COMPLETED",
            "response": final_text,
            "actions": all_actions,
            "approval_required": len(approval_flags) > 0,
            "approval_flags": approval_flags,
            "agent_reports": agent_reports
        }

# Alias for backwards compatibility & naming clarity
OrchestratorAgent = CoordinatorAgent
