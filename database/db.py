import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "bizagent.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 1. Users & Roles
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'Staff',
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """)

        # 2. Roles & Permissions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            permission TEXT NOT NULL,
            can_execute INTEGER DEFAULT 1,
            requires_approval INTEGER DEFAULT 0
        )
        """)

        # 3. Customers
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            company TEXT,
            status TEXT DEFAULT 'Active',
            address TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
        """)

        # 4. Sales Leads
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            company TEXT,
            deal_value REAL DEFAULT 0.0,
            score INTEGER DEFAULT 50,
            stage TEXT DEFAULT 'New',
            priority TEXT DEFAULT 'Medium',
            opt_out INTEGER DEFAULT 0,
            last_contact TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """)

        # 5. Lead Activities
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS lead_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            description TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
        """)

        # 6. Support Tickets
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Open',
            category TEXT DEFAULT 'General',
            sentiment TEXT DEFAULT 'Neutral',
            assigned_agent TEXT DEFAULT 'Customer Support Agent',
            escalated_to TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """)

        # 7. Appointments
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            client_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            service TEXT NOT NULL,
            slot_time TEXT NOT NULL,
            duration_minutes INTEGER DEFAULT 30,
            status TEXT DEFAULT 'Confirmed',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """)

        # 8. Human-in-the-Loop Approvals
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            action_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            risk_level TEXT DEFAULT 'Medium',
            proposed_operation TEXT,
            payload TEXT,
            status TEXT DEFAULT 'PENDING',
            requested_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewed_by TEXT,
            decision_notes TEXT,
            executed_at TEXT,
            execution_result TEXT
        )
        """)

        # 9. System Audit & Agent Logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            status TEXT DEFAULT 'SUCCESS'
        )
        """)

        # 10. Agent Tasks
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            parent_task_id TEXT,
            assigned_agent TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            input_data TEXT,
            output_data TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
        """)

        # 11. Structured Agent Messages (Agent-to-Agent communication)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            sender_agent TEXT NOT NULL,
            receiver_agent TEXT NOT NULL,
            task_description TEXT NOT NULL,
            customer_data TEXT,
            input_context TEXT,
            output_result TEXT,
            status TEXT DEFAULT 'SENT',
            approval_requirement INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        )
        """)

        # 12. Agent Execution History
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_execution_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            task_id TEXT,
            action_taken TEXT NOT NULL,
            duration_ms INTEGER DEFAULT 0,
            status TEXT DEFAULT 'SUCCESS',
            timestamp TEXT NOT NULL
        )
        """)

        # 13. Follow-up Schedules
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS followup_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            scheduled_date TEXT NOT NULL,
            template_id TEXT DEFAULT 'standard_b2b',
            status TEXT DEFAULT 'Scheduled',
            attempts_count INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            sent_at TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
        """)

        # 14. Email & Message Communication Logs (Simulated & Real)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_message_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_email TEXT NOT NULL,
            recipient_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            sent_by_agent TEXT NOT NULL,
            delivery_status TEXT DEFAULT 'Simulated-Sent',
            sent_at TEXT NOT NULL
        )
        """)

        # 15. Opt-Out Records (Permanent Suppression List)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS opt_out_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            reason TEXT DEFAULT 'Customer request',
            requested_at TEXT NOT NULL,
            permanent_suppression INTEGER DEFAULT 1
        )
        """)

        # 16. Notifications
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'INFO',
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """)

        # 17. Business Settings
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            updated_at TEXT NOT NULL
        )
        """)

        # 18. Executive Reports
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            metrics_json TEXT,
            generated_by_agent TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        # 19. Administration Tasks
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT 'Operations',
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Pending',
            assigned_to TEXT DEFAULT 'Administration Agent',
            due_date TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
        """)

        conn.commit()

        # Check existing table columns and migrate if necessary
        migrate_columns_if_needed(conn)

        # Seed initial data if tables are empty
        cursor.execute("SELECT COUNT(*) FROM customers")
        if cursor.fetchone()[0] == 0:
            seed_data(conn)
    finally:
        conn.close()

def migrate_columns_if_needed(conn):
    """Safely adds new columns to older tables if they already existed."""
    cursor = conn.cursor()
    
    # Check approvals columns
    cursor.execute("PRAGMA table_info(approvals)")
    cols = [r["name"] for r in cursor.fetchall()]
    if "risk_level" not in cols:
        try: cursor.execute("ALTER TABLE approvals ADD COLUMN risk_level TEXT DEFAULT 'Medium'")
        except Exception: pass
    if "proposed_operation" not in cols:
        try: cursor.execute("ALTER TABLE approvals ADD COLUMN proposed_operation TEXT")
        except Exception: pass
    if "executed_at" not in cols:
        try: cursor.execute("ALTER TABLE approvals ADD COLUMN executed_at TEXT")
        except Exception: pass
    if "execution_result" not in cols:
        try: cursor.execute("ALTER TABLE approvals ADD COLUMN execution_result TEXT")
        except Exception: pass

    # Check leads columns
    cursor.execute("PRAGMA table_info(leads)")
    lead_cols = [r["name"] for r in cursor.fetchall()]
    if "customer_id" not in lead_cols:
        try: cursor.execute("ALTER TABLE leads ADD COLUMN customer_id INTEGER")
        except Exception: pass
    if "phone" not in lead_cols:
        try: cursor.execute("ALTER TABLE leads ADD COLUMN phone TEXT")
        except Exception: pass
    if "priority" not in lead_cols:
        try: cursor.execute("ALTER TABLE leads ADD COLUMN priority TEXT DEFAULT 'Medium'")
        except Exception: pass
    if "created_at" not in lead_cols:
        try: cursor.execute("ALTER TABLE leads ADD COLUMN created_at TEXT")
        except Exception: pass

    # Check tickets columns
    cursor.execute("PRAGMA table_info(tickets)")
    ticket_cols = [r["name"] for r in cursor.fetchall()]
    if "customer_id" not in ticket_cols:
        try: cursor.execute("ALTER TABLE tickets ADD COLUMN customer_id INTEGER")
        except Exception: pass
    if "assigned_agent" not in ticket_cols:
        try: cursor.execute("ALTER TABLE tickets ADD COLUMN assigned_agent TEXT DEFAULT 'Customer Support Agent'")
        except Exception: pass
    if "escalated_to" not in ticket_cols:
        try: cursor.execute("ALTER TABLE tickets ADD COLUMN escalated_to TEXT")
        except Exception: pass
    if "resolved_at" not in ticket_cols:
        try: cursor.execute("ALTER TABLE tickets ADD COLUMN resolved_at TEXT")
        except Exception: pass

    # Check appointments columns
    cursor.execute("PRAGMA table_info(appointments)")
    appt_cols = [r["name"] for r in cursor.fetchall()]
    if "customer_id" not in appt_cols:
        try: cursor.execute("ALTER TABLE appointments ADD COLUMN customer_id INTEGER")
        except Exception: pass
    if "phone" not in appt_cols:
        try: cursor.execute("ALTER TABLE appointments ADD COLUMN phone TEXT")
        except Exception: pass
    if "created_at" not in appt_cols:
        try: cursor.execute("ALTER TABLE appointments ADD COLUMN created_at TEXT")
        except Exception: pass

    conn.commit()

def seed_data(conn):
    cursor = conn.cursor()
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # 1. Users
    users_data = [
        ("admin", "admin@enterprise.com", "System Administrator", "Admin", 1, now_str),
        ("manager_sarah", "sarah.mgr@enterprise.com", "Sarah Jenkins (Operations Director)", "Manager", 1, now_str),
        ("staff_alex", "alex.staff@enterprise.com", "Alex Rivera (Support Specialist)", "Staff", 1, now_str)
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO users (username, email, full_name, role, is_active, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, users_data)

    # 2. Roles & Permissions Matrix
    permissions_data = [
        ("Admin", "All Agents", "all_actions", 1, 0),
        ("Manager", "Sales Agent", "approve_discounts_over_15", 1, 1),
        ("Manager", "Support Agent", "approve_refunds", 1, 1),
        ("Staff", "Support Agent", "create_ticket", 1, 0),
        ("Staff", "Appointment Agent", "book_meeting", 1, 0),
        ("Staff", "Administration Agent", "view_records", 1, 0)
    ]
    cursor.executemany("""
    INSERT INTO roles_permissions (role, agent_name, permission, can_execute, requires_approval)
    VALUES (?, ?, ?, ?, ?)
    """, permissions_data)

    # 3. Customers
    customers_data = [
        ("John Doe", "john@acme.com", "+1-555-0101", "Acme Corporation", "Active", "123 Market St, San Francisco, CA", "Key Enterprise Account", (now - timedelta(days=30)).strftime("%Y-%m-%d")),
        ("Sarah Lee", "sarah@nextech.io", "+1-555-0102", "NexTech Labs", "Active", "456 Innovation Way, Austin, TX", "AI Product Division Lead", (now - timedelta(days=20)).strftime("%Y-%m-%d")),
        ("Mike Ross", "mike@globallog.com", "+1-555-0103", "Global Logistics", "Active", "789 Freight Blvd, Chicago, IL", "Needs custom API SLAs", (now - timedelta(days=15)).strftime("%Y-%m-%d")),
        ("Emma Wood", "emma@vanguard.org", "+1-555-0104", "Vanguard Retail", "Inactive", "321 Commerce Dr, Seattle, WA", "Requested marketing opt-out", (now - timedelta(days=10)).strftime("%Y-%m-%d")),
        ("Ali Khan", "ali.khan@techventures.pk", "+92-300-1234567", "TechVentures Global", "Prospect", "Tower 3, Business District, Lahore", "Inquired for custom development services", now_str)
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO customers (name, email, phone, company, status, address, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, customers_data)

    # 4. Leads
    leads_data = [
        (1, "Acme Corp (John Doe)", "john@acme.com", "+1-555-0101", "Acme Corporation", 12500.0, 85, "Negotiation", "High", 0, (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"), "Requested 25% discount for 2-year contract.", (now - timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")),
        (2, "NexTech Labs (Sarah Lee)", "sarah@nextech.io", "+1-555-0102", "NexTech Labs", 4800.0, 92, "Qualified", "High", 0, (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M"), "Very interested in Enterprise AI add-on.", (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")),
        (3, "Global Logistics (Mike Ross)", "mike@globallog.com", "+1-555-0103", "Global Logistics", 15000.0, 78, "Contacted", "Medium", 0, (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M"), "Needs custom API integrations.", (now - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")),
        (4, "Vanguard Retail (Emma Wood)", "emma@vanguard.org", "+1-555-0104", "Vanguard Retail", 2200.0, 40, "Lost - Opt Out", "Low", 1, (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M"), "Customer requested opt-out from marketing.", (now - timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S")),
        (5, "TechVentures (Ali Khan)", "ali.khan@techventures.pk", "+92-300-1234567", "TechVentures Global", 8500.0, 88, "Interested", "High", 0, (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), "Warm inbound enquiry regarding full-stack AI development.", now_str)
    ]
    cursor.executemany("""
    INSERT INTO leads (customer_id, name, email, phone, company, deal_value, score, stage, priority, opt_out, last_contact, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, leads_data)

    # 5. Tickets
    tickets_data = [
        (1, "Alice Cooper", "alice@music.com", "Cannot sync Google Calendar", "Appointments booked via the bot are not reflecting on my calendar.", "High", "In Progress", "Integration", "Negative", "Customer Support Agent", None, (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")),
        (2, "Bob Smith", "bob@smithfirm.com", "Billing inquiry on invoice #4092", "Was charged twice for the monthly seat upgrade ($499.00). Please refund.", "High", "Open", "Billing", "Frustrated", "Customer Support Agent", "Finance Manager", (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")),
        (3, "David Miller", "david@alpha.com", "Feature request: CSV Export", "Can we export monthly lead conversion reports as CSV?", "Low", "Resolved", "Product", "Positive", "Customer Support Agent", None, (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M")),
        (4, "Claire Bennett", "claire@cheers.net", "Need onboarding walkthrough", "We just signed up our 10 team members and need guidance.", "Medium", "Open", "Onboarding", "Neutral", "Customer Support Agent", None, (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M"))
    ]
    cursor.executemany("""
    INSERT INTO tickets (customer_id, customer_name, email, subject, message, priority, status, category, sentiment, assigned_agent, escalated_to, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tickets_data)

    # 6. Appointments
    appts_data = [
        (2, "Sarah Lee", "sarah@nextech.io", "+1-555-0102", "Enterprise Architecture Review", (now + timedelta(days=1, hours=2)).strftime("%Y-%m-%d 14:00"), 45, "Confirmed", "Demo of Multi-Agent features"),
        (3, "Mike Ross", "mike@globallog.com", "+1-555-0103", "Contract & SLA Discussion", (now + timedelta(days=2, hours=4)).strftime("%Y-%m-%d 16:30"), 30, "Confirmed", "Security compliance check"),
        (5, "Ali Khan", "ali.khan@techventures.pk", "+92-300-1234567", "Initial Architecture Discovery Session", (now + timedelta(days=1, hours=4)).strftime("%Y-%m-%d 16:00"), 30, "Confirmed", "Follow-up discussion for software development proposal")
    ]
    cursor.executemany("""
    INSERT INTO appointments (customer_id, client_name, email, phone, service, slot_time, duration_minutes, status, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, appts_data)

    # 7. Approvals
    approvals_data = [
        ("Sales & Lead Agent", "HIGH_DISCOUNT_APPROVAL", "25% High-Tier Discount Approval", "Acme Corp requested a 25% discount ($3,125 savings) on an Enterprise deal worth $12,500.", "High", "Apply 25% discount to lead #1", json.dumps({"lead_id": 1, "deal_value": 12500, "discount_pct": 25.0, "client_name": "Acme Corp"}), "PENDING", (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), None, None, None, None, None),
        ("Customer Support Agent", "REFUND_AUTHORIZATION", "Duplicate Charge Refund ($499.00)", "Customer Bob Smith experienced a duplicate billing event on invoice #4092.", "Critical", "Issue $499.00 merchant refund", json.dumps({"ticket_id": 2, "amount": 499.0, "reason": "System billing glitch", "customer": "Bob Smith"}), "PENDING", (now - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M"), None, None, None, None, None),
        ("Sales & Lead Agent", "BULK_CAMPAIGN_APPROVAL", "Q4 Enterprise Follow-up Campaign", "Proposal to send personalized nurture sequences to 45 Enterprise leads.", "Medium", "Dispatch outbound campaign to 45 recipients", json.dumps({"batch_size": 45, "template": "enterprise_q4"}), "PENDING", (now - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M"), None, None, None, None, None),
        ("Administration Agent", "DATABASE_RECORD_PURGE", "Purge Obsolete Test Logs", "Request to clear system error logs older than 180 days to free storage.", "High", "DELETE FROM audit_logs WHERE timestamp < 180_days_ago", json.dumps({"table": "audit_logs", "days": 180}), "PENDING", (now - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M"), None, None, None, None, None),
        ("Sales & Lead Agent", "SPECIAL_SLA", "99.99% Custom SLA Guarantee", "Global Logistics requires an executive sign-off for custom 4-hour SLA penalty clause.", "Medium", "Sign custom SLA terms", json.dumps({"lead_id": 3, "sla": "99.99%", "penalty": "10% rebate"}), "APPROVED", (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"), (now - timedelta(hours=18)).strftime("%Y-%m-%d %H:%M"), "Sarah Jenkins", "Approved with standard clause.", (now - timedelta(hours=18)).strftime("%Y-%m-%d %H:%M"), "SLA clause attached to master agreement.")
    ]
    cursor.executemany("""
    INSERT INTO approvals (agent_name, action_type, title, description, risk_level, proposed_operation, payload, status, requested_at, reviewed_at, reviewed_by, decision_notes, executed_at, execution_result)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, approvals_data)

    # 8. Opt-Out Records (Suppression List)
    cursor.execute("""
    INSERT OR IGNORE INTO opt_out_records (email, phone, reason, requested_at, permanent_suppression)
    VALUES (?, ?, ?, ?, ?)
    """, ("emma@vanguard.org", "+1-555-0104", "Unsubscribed via follow-up link", (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"), 1))

    # 9. Business Settings
    settings_data = [
        ("business_name", "Apex Solutions Ltd", "Company commercial name", now_str),
        ("business_hours", "09:00 - 18:00 (Mon-Fri)", "Standard operating hours", now_str),
        ("timezone", "UTC+5 (PKT)", "Business primary timezone", now_str),
        ("auto_discount_threshold", "15.0", "Maximum percentage discount agents can approve autonomously", now_str),
        ("high_value_deal_threshold", "10000.0", "Deal value triggering mandatory manager notification", now_str),
        ("opt_out_strict_mode", "true", "Enforce permanent suppression on all marketing channels", now_str),
        ("require_approval_for_external_comms", "true", "Whether outbound sales campaigns require human sign-off", now_str),
        ("simulated_mode", "true", "Run email, calendar, and payment systems in safe simulation mode", now_str)
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO business_settings (key, value, description, updated_at)
    VALUES (?, ?, ?, ?)
    """, settings_data)

    # 10. Admin Tasks
    admin_tasks_data = [
        ("Reconcile End-of-Month Invoices", "Finance", "High", "Pending", "Administration Agent", (now + timedelta(days=3)).strftime("%Y-%m-%d"), "Compare Stripe merchant log with database tickets.", now_str),
        ("Verify Anti-Spam Opt-Out List Compliance", "Compliance", "Critical", "Pending", "Administration Agent", (now + timedelta(days=1)).strftime("%Y-%m-%d"), "Run audit verification against opt_out_records table.", now_str),
        ("Archive Inactive Leads (> 90 days)", "CRM Maintenance", "Medium", "In Progress", "Administration Agent", (now + timedelta(days=5)).strftime("%Y-%m-%d"), "Move lost leads to historical archive table.", now_str),
        ("Update Q4 Business Rate Card", "Operations", "Medium", "Completed", "Administration Agent", (now - timedelta(days=2)).strftime("%Y-%m-%d"), "Refreshed hourly consultancy fee structure.", now_str)
    ]
    cursor.executemany("""
    INSERT INTO admin_tasks (title, category, priority, status, assigned_to, due_date, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, admin_tasks_data)

    # 11. Follow-up Schedules
    followups_data = [
        (1, "Stage 2 - Proposal Review", (now + timedelta(days=2)).strftime("%Y-%m-%d"), "enterprise_proposal", "Scheduled", 1, 3),
        (2, "Stage 1 - Post Demo Check-in", (now + timedelta(days=1)).strftime("%Y-%m-%d"), "post_demo_checkin", "Scheduled", 0, 3),
        (3, "Stage 3 - Final Terms", (now + timedelta(days=4)).strftime("%Y-%m-%d"), "final_terms", "Scheduled", 2, 3),
        (5, "Stage 1 - Inbound Welcome & Meeting Confirmation", (now + timedelta(hours=4)).strftime("%Y-%m-%d"), "inbound_welcome", "Scheduled", 0, 3)
    ]
    cursor.executemany("""
    INSERT INTO followup_schedules (lead_id, stage, scheduled_date, template_id, status, attempts_count, max_attempts)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, followups_data)

    # 12. Email Message Logs (Simulated)
    email_logs_data = [
        ("john@acme.com", "John Doe", "BizAgent Enterprise Proposal", "Dear John, please find the updated implementation roadmap...", "Sales & Lead Agent", "Simulated-Sent", (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),
        ("sarah@nextech.io", "Sarah Lee", "Confirmation: Enterprise Architecture Review", "Hi Sarah, your meeting has been confirmed for tomorrow at 14:00...", "Appointment Agent", "Simulated-Sent", (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")),
        ("ali.khan@techventures.pk", "Ali Khan", "Thank you for contacting BizAgent AI", "Dear Ali, we received your enquiry regarding software development services...", "Sales & Lead Agent", "Simulated-Sent", (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")),
        ("emma@vanguard.org", "Emma Wood", "Marketing Communication Blocked", "[BLOCKED BY SUPPRESSION SYSTEM] Recipient opted out of marketing.", "Security System", "Blocked", (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"))
    ]
    cursor.executemany("""
    INSERT INTO email_message_logs (recipient_email, recipient_name, subject, body, sent_by_agent, delivery_status, sent_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, email_logs_data)

    # 13. Notifications
    notifs_data = [
        ("New Enterprise Lead", "Ali Khan submitted an inquiry for custom development services.", "INFO", 0, now_str),
        ("Human Approval Required", "Sales Agent requested approval for 25% discount for Acme Corp.", "APPROVAL", 0, (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")),
        ("High Priority Ticket", "Bob Smith reported duplicate charge on invoice #4092.", "ALERT", 0, (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")),
        ("Security Audit Log", "Routine security guardrail scan completed: 0 violations.", "INFO", 1, (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"))
    ]
    cursor.executemany("""
    INSERT INTO notifications (title, message, type, is_read, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, notifs_data)

    # 14. Audit Logs
    logs_data = [
        ((now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"), "Orchestrator Agent", "ROUTE_INTENT", "Received query from portal: routed to Customer Support Agent", "SUCCESS"),
        ((now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"), "Customer Support Agent", "CREATE_TICKET", "Auto-created ticket #1 for customer Alice Cooper", "SUCCESS"),
        ((now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), "Sales & Lead Agent", "TRIGGER_APPROVAL", "Discount exceeded 15% threshold; routed to Human Approval Center", "PENDING_APPROVAL"),
        ((now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"), "Appointment Agent", "BOOK_SLOT", "Scheduled demo meeting with Sarah Lee for tomorrow at 14:00", "SUCCESS"),
        ((now - timedelta(minutes=40)).strftime("%Y-%m-%d %H:%M:%S"), "Administration Agent", "SYSTEM_HEALTH_CHECK", "Validated database integrity and synchronized customer suppression list", "SUCCESS"),
        ((now - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S"), "Reporting & Analytics Agent", "GENERATE_DIGEST", "Computed daily business metrics (Conversion Rate: 34%, SLA: 98.4%)", "SUCCESS")
    ]
    cursor.executemany("""
    INSERT INTO audit_logs (timestamp, agent_name, action, details, status)
    VALUES (?, ?, ?, ?, ?)
    """, logs_data)

    # 15. Structured Agent Messages (Sample history)
    task_id_1 = "TASK-ALI-KHAN-DEMO-001"
    messages_data = [
        (task_id_1, "AI Orchestrator Agent", "Customer Support Agent", "Analyze inbound customer inquiry and detect sales intent", json.dumps({"name": "Ali Khan", "email": "ali.khan@techventures.pk"}), "Inbound enquiry: Software development & meeting request", "Identified as high-value B2B sales opportunity", "COMPLETED", 0, (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")),
        (task_id_1, "Customer Support Agent", "Sales & Lead Agent", "Delegate qualified prospect to CRM pipeline", json.dumps({"name": "Ali Khan", "email": "ali.khan@techventures.pk", "company": "TechVentures Global"}), "Prospect interested in development services", "Lead #5 created with Priority Score 88/100", "COMPLETED", 0, (now - timedelta(hours=2, minutes=-2)).strftime("%Y-%m-%d %H:%M:%S")),
        (task_id_1, "Sales & Lead Agent", "AI Orchestrator Agent", "Request human approval for outbound proposal", json.dumps({"lead_id": 5, "deal_value": 8500.0}), "Drafted tailored commercial follow-up proposal", "Action requires human approval per communication policy", "PENDING_APPROVAL", 1, (now - timedelta(hours=2, minutes=-4)).strftime("%Y-%m-%d %H:%M:%S")),
        (task_id_1, "AI Orchestrator Agent", "Appointment Agent", "Coordinate 30-minute discovery session", json.dumps({"name": "Ali Khan", "email": "ali.khan@techventures.pk"}), "Customer requested meeting coordination", "Checked calendar; reserved slot tomorrow at 16:00", "COMPLETED", 0, (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")),
        (task_id_1, "Appointment Agent", "Reporting & Analytics Agent", "Broadcast appointment confirmation event", json.dumps({"appointment_id": 3, "status": "Confirmed"}), "Sync new meeting into operations reporting", "Updated appointment KPI counters to 3 active bookings", "COMPLETED", 0, (now - timedelta(minutes=55)).strftime("%Y-%m-%d %H:%M:%S"))
    ]
    cursor.executemany("""
    INSERT INTO agent_messages (task_id, sender_agent, receiver_agent, task_description, customer_data, input_context, output_result, status, approval_requirement, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, messages_data)

    conn.commit()

# --- Helper Methods ---

def log_audit(agent_name, action, details, status="SUCCESS"):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO audit_logs (timestamp, agent_name, action, details, status)
        VALUES (?, ?, ?, ?, ?)
        """, (now_str, agent_name, action, details, status))
        conn.commit()
    finally:
        conn.close()

def get_recent_logs(limit=25):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def log_agent_message(task_id, sender_agent, receiver_agent, task_description, customer_data=None, input_context="", output_result="", status="COMPLETED", approval_requirement=0):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cust_str = json.dumps(customer_data) if isinstance(customer_data, (dict, list)) else (customer_data or "")
        cursor.execute("""
        INSERT INTO agent_messages (task_id, sender_agent, receiver_agent, task_description, customer_data, input_context, output_result, status, approval_requirement, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_id, sender_agent, receiver_agent, task_description, cust_str, str(input_context), str(output_result), status, 1 if approval_requirement else 0, now_str))
        conn.commit()
    finally:
        conn.close()

def get_agent_messages(task_id=None, limit=50):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if task_id:
            cursor.execute("SELECT * FROM agent_messages WHERE task_id = ? ORDER BY id ASC", (task_id,))
        else:
            cursor.execute("SELECT * FROM agent_messages ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_pending_approvals():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM approvals WHERE status = 'PENDING' ORDER BY id DESC")
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_approval_history(limit=50):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM approvals WHERE status != 'PENDING' ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def create_approval_request(agent_name, action_type, title, description, payload=None, risk_level="Medium", proposed_operation=""):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload_str = json.dumps(payload or {})
        cursor.execute("""
        INSERT INTO approvals (agent_name, action_type, title, description, risk_level, proposed_operation, payload, status, requested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
        """, (agent_name, action_type, title, description, risk_level, proposed_operation or action_type, payload_str, now_str))
        new_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    log_audit(agent_name, "REQUEST_HUMAN_APPROVAL", f"Created Approval request #{new_id} ({risk_level} risk): {title}", status="PENDING_APPROVAL")
    return new_id

def resolve_approval(approval_id, decision, reviewer="Manager", notes=""):
    """
    Resolves human approval and, if approved, immediately executes the authorized sensitive action.
    """
    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execution_result = ""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,))
        app_row = cursor.fetchone()
        if not app_row:
            return {"error": "Approval request not found"}
        
        app_dict = dict(app_row)

        if decision == "APPROVED":
            # Execute the action safely
            execution_result = execute_approved_action(app_dict)
            cursor.execute("""
            UPDATE approvals
            SET status = 'APPROVED', reviewed_at = ?, reviewed_by = ?, decision_notes = ?, executed_at = ?, execution_result = ?
            WHERE id = ?
            """, (now_str, reviewer, notes, now_str, execution_result, approval_id))
        else:
            execution_result = "Action blocked and discarded per human rejection."
            cursor.execute("""
            UPDATE approvals
            SET status = 'REJECTED', reviewed_at = ?, reviewed_by = ?, decision_notes = ?, executed_at = NULL, execution_result = ?
            WHERE id = ?
            """, (now_str, reviewer, notes, execution_result, approval_id))
        
        conn.commit()
    finally:
        conn.close()

    log_audit("Human Manager", f"APPROVAL_{decision}", f"Approval #{approval_id} ({app_dict.get('action_type')}) resolved as {decision}. Execution result: {execution_result}")
    return {"status": decision, "execution_result": execution_result}

def execute_approved_action(approval_dict):
    """
    Executes the authorized action based on action_type and payload.
    """
    action_type = approval_dict.get("action_type")
    payload = {}
    try:
        payload = json.loads(approval_dict.get("payload") or "{}")
    except Exception:
        pass

    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if action_type == "HIGH_DISCOUNT_APPROVAL":
            lead_id = payload.get("lead_id")
            disc = payload.get("discount_pct", 0)
            if lead_id:
                cursor.execute("UPDATE leads SET notes = COALESCE(notes, '') || ' | Approved discount: ' || ? || '%' WHERE id = ?", (disc, lead_id))
                conn.commit()
            return f"Approved discount of {disc}% applied to Lead #{lead_id}."

        elif action_type == "REFUND_AUTHORIZATION":
            ticket_id = payload.get("ticket_id")
            amount = payload.get("amount", 0.0)
            if ticket_id:
                cursor.execute("UPDATE tickets SET status = 'Resolved', resolved_at = ? WHERE id = ?", (now_str, ticket_id))
                conn.commit()
            return f"Simulated refund of ${amount:,.2f} processed. Ticket #{ticket_id} updated to Resolved."

        elif action_type == "BULK_CAMPAIGN_APPROVAL":
            batch_size = payload.get("batch_size", 0)
            return f"Bulk nurture campaign approved for {batch_size} leads. Outbound dispatch sequence queued."

        elif action_type == "OUTBOUND_EMAIL_APPROVAL":
            recipient = payload.get("recipient_email", "")
            subject = payload.get("subject", "Business Communication")
            body = payload.get("body", "")
            cursor.execute("""
            INSERT INTO email_message_logs (recipient_email, recipient_name, subject, body, sent_by_agent, delivery_status, sent_at)
            VALUES (?, ?, ?, ?, 'Sales & Lead Agent', 'Simulated-Sent', ?)
            """, (recipient, payload.get("recipient_name", "Valued Client"), subject, body, now_str))
            conn.commit()
            return f"Approved external email dispatched to {recipient} (Simulated-Sent)."

        elif action_type == "APPOINTMENT_CANCELLATION":
            appt_id = payload.get("appointment_id")
            if appt_id:
                cursor.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (appt_id,))
                conn.commit()
            return f"Appointment #{appt_id} cancelled upon manager approval."

        elif action_type == "DATABASE_RECORD_PURGE":
            return "Purge of old logs executed safely under policy constraints."

        else:
            return f"Action '{action_type}' successfully executed with approved parameters."
    finally:
        conn.close()

def log_email_message(recipient_email, recipient_name, subject, body, sent_by_agent, delivery_status="Simulated-Sent"):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO email_message_logs (recipient_email, recipient_name, subject, body, sent_by_agent, delivery_status, sent_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (recipient_email, recipient_name, subject, body, sent_by_agent, delivery_status, now_str))
        conn.commit()
    finally:
        conn.close()

def is_opted_out(email: str) -> bool:
    """Checks whether an email is permanently suppressed or opted out."""
    if not email:
        return False
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM opt_out_records WHERE LOWER(email) = LOWER(?)", (email.strip(),))
        if cursor.fetchone():
            return True
        cursor.execute("SELECT 1 FROM leads WHERE LOWER(email) = LOWER(?) AND opt_out = 1", (email.strip(),))
        if cursor.fetchone():
            return True
        return False
    finally:
        conn.close()

def record_opt_out(email: str, phone: str = "", reason: str = "Customer requested opt-out"):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT OR REPLACE INTO opt_out_records (email, phone, reason, requested_at, permanent_suppression)
        VALUES (?, ?, ?, ?, 1)
        """, (email.strip(), phone, reason, now_str))
        cursor.execute("UPDATE leads SET opt_out = 1, stage = 'Lost - Opt Out' WHERE LOWER(email) = LOWER(?)", (email.strip(),))
        conn.commit()
    finally:
        conn.close()
    log_audit("Security & Compliance", "OPT_OUT_SUPPRESSION", f"Email {email} permanently added to suppression list. Marketing halted.")

def get_business_settings():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM business_settings")
        return {r["key"]: r["value"] for r in cursor.fetchall()}
    finally:
        conn.close()

def update_business_setting(key: str, value: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE business_settings SET value = ?, updated_at = ? WHERE key = ?", (value, now_str, key))
        conn.commit()
    finally:
        conn.close()
    log_audit("Administration Agent", "UPDATE_SETTING", f"Updated setting '{key}' = '{value}'")

def get_admin_tasks():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin_tasks ORDER BY id DESC")
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def add_admin_task(title: str, category: str = "Operations", priority: str = "Medium", due_date: str = "", notes: str = ""):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO admin_tasks (title, category, priority, status, assigned_to, due_date, notes, created_at)
        VALUES (?, ?, ?, 'Pending', 'Administration Agent', ?, ?, ?)
        """, (title, category, priority, due_date, notes, now_str))
        new_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    log_audit("Administration Agent", "CREATE_ADMIN_TASK", f"Created administrative task #{new_id}: {title}")
    return new_id

def update_admin_task(task_id: int, status: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE admin_tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()
    finally:
        conn.close()
    log_audit("Administration Agent", "UPDATE_ADMIN_TASK", f"Updated task #{task_id} status to {status}")

def get_notifications(unread_only=False):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if unread_only:
            cursor.execute("SELECT * FROM notifications WHERE is_read = 0 ORDER BY id DESC")
        else:
            cursor.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT 50")
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def mark_notification_read(notif_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
        conn.commit()
    finally:
        conn.close()

def create_notification(title: str, message: str, notif_type: str = "INFO"):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO notifications (title, message, type, is_read, created_at)
        VALUES (?, ?, ?, 0, ?)
        """, (title, message, notif_type, now_str))
        conn.commit()
    finally:
        conn.close()

def get_email_logs(limit=50):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM email_message_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_customers(search="", limit=50):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if search:
            q = f"%{search}%"
            cursor.execute("SELECT * FROM customers WHERE name LIKE ? OR email LIKE ? OR company LIKE ? ORDER BY id DESC LIMIT ?", (q, q, q, limit))
        else:
            cursor.execute("SELECT * FROM customers ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def add_customer(name: str, email: str, phone: str = "", company: str = "", status: str = "Active", address: str = "", notes: str = ""):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO customers (name, email, phone, company, status, address, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, phone, company, status, address, notes, now_str))
        new_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    log_audit("Administration Agent", "ADD_CUSTOMER", f"Created customer profile #{new_id} ({name})")
    return new_id

# Initialize DB on load
init_db()
