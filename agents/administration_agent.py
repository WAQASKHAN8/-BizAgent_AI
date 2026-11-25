from datetime import datetime
import json
from database.db import (
    get_connection,
    log_audit,
    create_approval_request,
    get_customers,
    add_customer,
    get_admin_tasks,
    add_admin_task,
    update_admin_task,
    get_business_settings,
    update_business_setting,
    get_notifications,
    create_notification
)
from tools.gemini_service import generate_response

class AdministrationAgent:
    """
    Agent 6: Administration Agent
    Role: Automates routine administrative activities, maintains customer/operational records,
          tracks internal operational tasks, prepares meeting summaries, and handles governance alerts.
    
    Responsibilities:
    - Organize customer records & business directories.
    - Maintain business operational information.
    - Manage internal administrative tasks & reminders.
    - Prepare executive meeting summaries & documentation.
    - Generate administrative memos & compliance reports.
    - Track pending departmental tasks.
    - Organize and dispatch business notifications.
    
    Restrictions:
    - CANNOT permanently delete records or purge tables without Human Approval.
    - CANNOT modify critical business settings (e.g. discount policy, working hours) without Human Approval.
    - CANNOT access or export customer data outside authenticated sessions.
    """
    NAME = "Administration Agent"
    ROLE = "Routine Administration, Record Organization & Operational Tasks"
    PERMITTED_ACTIONS = [
        "organize_records",
        "manage_admin_tasks",
        "generate_admin_doc",
        "prepare_meeting_summary",
        "update_task_status",
        "check_system_health",
        "dispatch_notification"
    ]
    RESTRICTED_ACTIONS = [
        "permanent_delete_records",
        "modify_critical_settings",
        "export_unredacted_pii"
    ]

    @classmethod
    def get_tasks(cls, status=None) -> list:
        tasks = get_admin_tasks()
        if status:
            return [t for t in tasks if t.get("status") == status]
        return tasks

    @classmethod
    def create_task(cls, title: str, category: str = "Operations", priority: str = "Medium", due_date: str = "", notes: str = "") -> dict:
        task_id = add_admin_task(title, category, priority, due_date, notes)
        create_notification("New Admin Task", f"Task #{task_id} ({title}) assigned to Administration Agent.", "INFO")
        return {
            "task_id": task_id,
            "title": title,
            "category": category,
            "priority": priority,
            "status": "Pending",
            "message": f"Administrative task #{task_id} successfully registered."
        }

    @classmethod
    def complete_task(cls, task_id: int) -> dict:
        update_admin_task(task_id, "Completed")
        return {"task_id": task_id, "status": "Completed", "message": f"Admin task #{task_id} marked as completed."}

    @classmethod
    def prepare_meeting_summary(cls, meeting_title: str, attendees: list, notes: str) -> str:
        prompt = f"""
Prepare a formal Executive Meeting Summary:
Title: {meeting_title}
Attendees: {', '.join(attendees) if attendees else 'Internal Operations Team'}
Raw Meeting Notes:
{notes}

Format with:
1. Executive Brief (1-2 sentences)
2. Key Decisions Made
3. Action Items with assigned owners
4. Next Review Date
"""
        summary = generate_response(
            prompt,
            system_prompt="You are the Administration Agent for BizAgent AI. Write clear, structured, professional executive documentation."
        )
        log_audit(cls.NAME, "PREPARE_MEETING_SUMMARY", f"Prepared meeting minutes for: {meeting_title}")
        return summary

    @classmethod
    def generate_admin_document(cls, doc_type: str, title: str, details: dict) -> str:
        prompt = f"""
Generate an official administrative document:
Document Type: {doc_type}
Document Title: {title}
Context Details:
{json.dumps(details, indent=2)}

Include standard business headers, purpose statement, operative provisions, and sign-off placeholders.
"""
        doc_text = generate_response(
            prompt,
            system_prompt="You are the Administration Agent for BizAgent AI. Generate formal corporate documentation."
        )
        log_audit(cls.NAME, "GENERATE_ADMIN_DOCUMENT", f"Generated document '{title}' ({doc_type})")
        return doc_text

    @classmethod
    def request_critical_setting_change(cls, setting_key: str, new_value: str, reason: str) -> dict:
        """
        Restriction Enforcement: Critical business settings cannot be modified autonomously.
        Creates an approval request in the Human Approval Center.
        """
        current_settings = get_business_settings()
        curr_val = current_settings.get(setting_key, "Not set")

        approval_id = create_approval_request(
            agent_name=cls.NAME,
            action_type="CRITICAL_SETTING_CHANGE",
            title=f"Modify Setting: '{setting_key}'",
            description=f"Administration Agent requested change for '{setting_key}' from '{curr_val}' to '{new_value}'. Reason: {reason}",
            risk_level="High",
            proposed_operation=f"UPDATE business_settings SET value='{new_value}' WHERE key='{setting_key}'",
            payload={"key": setting_key, "old_value": curr_val, "new_value": new_value, "reason": reason}
        )
        return {
            "status": "PENDING_APPROVAL",
            "approval_id": approval_id,
            "message": f"Changing critical setting '{setting_key}' requires human authorization. Request #{approval_id} submitted to Human Approval Center."
        }

    @classmethod
    def request_permanent_deletion(cls, table_name: str, filter_criteria: str, reason: str) -> dict:
        """
        Restriction Enforcement: Permanent record deletion cannot be executed autonomously.
        Creates a Critical Risk approval request in the Human Approval Center.
        """
        approval_id = create_approval_request(
            agent_name=cls.NAME,
            action_type="PERMANENT_RECORD_DELETION",
            title=f"Record Purge: '{table_name}'",
            description=f"Administration Agent requested permanent record purge on table '{table_name}' matching '{filter_criteria}'. Reason: {reason}",
            risk_level="Critical",
            proposed_operation=f"DELETE FROM {table_name} WHERE {filter_criteria}",
            payload={"table": table_name, "filter": filter_criteria, "reason": reason}
        )
        return {
            "status": "PENDING_APPROVAL",
            "approval_id": approval_id,
            "message": f"Permanent deletion from '{table_name}' blocked by security policy. Escalated as High-Risk Approval #{approval_id}."
        }

    @classmethod
    def check_system_health(cls) -> dict:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM customers")
            c_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM leads")
            l_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tickets")
            t_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM appointments")
            a_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM approvals WHERE status = 'PENDING'")
            p_appr = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM opt_out_records")
            opt_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM admin_tasks WHERE status = 'Pending'")
            pend_tasks = cursor.fetchone()[0]

            health_status = "Optimal" if p_appr < 5 else "Attention Required"

            return {
                "health_status": health_status,
                "total_customers": c_count,
                "total_leads": l_count,
                "total_tickets": t_count,
                "total_appointments": a_count,
                "pending_approvals": p_appr,
                "suppression_list_size": opt_count,
                "pending_admin_tasks": pend_tasks,
                "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        finally:
            conn.close()
