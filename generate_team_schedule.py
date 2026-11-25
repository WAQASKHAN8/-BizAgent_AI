import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import os
import csv

# Workbook initialization
wb = openpyxl.Workbook()

# Sheet 1: 3-Day Work Plan
ws = wb.active
ws.title = "3-Day Project Schedule"

# Title block
ws.merge_cells("A1:G1")
title_cell = ws["A1"]
title_cell.value = "HCCDA AI — TEAM 3: 3-DAY PROJECT WORK PLAN & TASK BREAKDOWN"
title_cell.font = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
title_cell.fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
title_cell.alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 36

# Subtitle block
ws.merge_cells("A2:G2")
sub_cell = ws["A2"]
sub_cell.value = "Project: BizAgent AI (Intelligent Multi-Agent Business Assistant) | Scenario: Customer Support, Sales, Appointments & Reporting"
sub_cell.font = Font(name="Calibri", size=10, italic=True, color="FFFFFF")
sub_cell.fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
sub_cell.alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[2].height = 22

# Headers
headers = [
    "Day",
    "Team Member",
    "Qualification / Skill Level",
    "Task Sheet Topic",
    "Assigned Tasks & Responsibilities",
    "Key Deliverables",
    "Status"
]

header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
header_font = Font(name="Calibri", size=11, bold=True, color="000000")
thin_border = Border(
    left=Side(style='thin', color='D9D9D9'),
    right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'),
    bottom=Side(style='thin', color='D9D9D9')
)

ws.row_dimensions[4].height = 26
for col_idx, header in enumerate(headers, start=1):
    cell = ws.cell(row=4, column=col_idx)
    cell.value = header
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = thin_border

# Schedule Data
data = [
    # DAY 1 - R&D (All Members)
    [
        "Day 1",
        "All Team Members (Waqas, Bilawal, Kaif, Esha, Ateeq)",
        "Team Brainstorming & Research",
        "Business Scenario & Tool Selection",
        "• Deep dive into Task Sheet requirements & HCCDA AI assessment criteria.\n• Identify 5 real business problems & operational impacts.\n• Research Gemini API capabilities, Agentic workflows vs basic chatbots.\n• Brainstorm the 4+ specialized agents needed for business automation.\n• Review tech stack (Python, Streamlit, SQLite, Google GenAI SDK).",
        "Research Notes, Problem Statement Matrix, Selected Architecture Plan",
        "Completed"
    ],
    # DAY 2 - SRS & Core Dev
    [
        "Day 2",
        "M. Kaif ul Hassan (Khaf)",
        "Intermediate",
        "SRS Document & Functional Specs",
        "• Lead authoring of Software Requirements Specification (SRS).\n• Define functional & non-functional requirements for Support and Sales.\n• Document user stories, agent boundary definitions, and acceptance criteria.",
        "SRS Document Draft v1.0 (Functional Specifications)",
        "Completed"
    ],
    [
        "Day 2",
        "Esha Mushtaq",
        "Basic",
        "SRS Document & System Flow",
        "• Co-author SRS document with Kaif.\n• Map appointment booking workflows and customer inquiry flowcharts.\n• Document business assumptions and constraints for routine administration.",
        "SRS Section on Workflow Diagrams & User Journey",
        "Completed"
    ],
    [
        "Day 2",
        "Waqas Islam",
        "Data Analyst (Knows all things / Lead Dev)",
        "Core Development & Architecture",
        "• Initialize project structure, virtual environment, and dependencies.\n• Build SQLite database schema (`database/db.py`) with WAL mode.\n• Implement core Master Coordinator Agent (`agents/coordinator.py`).\n• Setup Google GenAI connection with model fallback in `config.py`.\n• Build initial Streamlit executive dashboard framework in `app.py`.",
        "Database Engine, Coordinator Architecture, Core Project Scaffolding",
        "Completed"
    ],
    [
        "Day 2",
        "Ateeq Qadir",
        "Intermediate",
        "Development Support & Tooling",
        "• Collaborate with Waqas on CRM and Calendar tool design.\n• Define SQLite database seed data (sample leads, tickets, appointments).\n• Assist in testing environment variables and initial API connectivity.",
        "Seed Data Scripts, Calendar Tool Helper Modules",
        "Completed"
    ],
    [
        "Day 2",
        "Syed Bilawal",
        "Basic",
        "Development Support & Environment",
        "• Assist Waqas with repository setup, `.gitignore`, and `requirements.txt`.\n• Test local Python virtual environment activation across team laptops.\n• Review basic prompt templates for Customer Support & General Admin.",
        "Virtual Environment Setup Guide, Initial Prompt Templates",
        "Completed"
    ],
    # DAY 3 - Specialized Division by Qualification
    [
        "Day 3",
        "Waqas Islam",
        "Data Analyst (Knows all things / Lead Dev)",
        "Tasks 5 & 7: End-to-End Integration, Analytics & Reporting",
        "• Implement Business Reporting Agent (`agents/reporting_agent.py`) with KPI metrics.\n• Build interactive KPI tiles & distribution charts in Streamlit.\n• Integrate dynamic multi-agent dispatcher with Gemini LLM reasoning.\n• Wire up Human Approval Center (HITL) with real-time database state.\n• Create CLI runner (`run_agent.py`) for live terminal execution.\n• Lead end-to-end prototype demo readiness for assessment.",
        "Reporting Agent, Executive Charts, End-to-End Integration, CLI Runner",
        "Completed"
    ],
    [
        "Day 3",
        "Ateeq Qadir",
        "Intermediate",
        "Task 6: Security, Guardrails & Testing",
        "• Implement Security Guardrails (`tools/security_tool.py`) with PII masking.\n• Develop regex defenses against prompt injection attacks.\n• Execute automated test suite (`tests/test_agents.py`) using pytest.\n• Verify Human-in-the-Loop discount escalation (15% policy threshold).\n• Ensure zero test failures across all 7 verification test cases.",
        "Security Guardrail Layer, Pytest Test Suite (7/7 Passed)",
        "Completed"
    ],
    [
        "Day 3",
        "M. Kaif ul Hassan (Khaf)",
        "Intermediate",
        "Tasks 2 & 4: Sales & Support Logic Verification",
        "• Finalize SRS documentation with technical architecture diagrams.\n• Verify Sales Agent automated follow-up sequences & CAN-SPAM opt-out handling.\n• Test Customer Support Agent ticket creation and sentiment triage.\n• Review inter-agent information exchange between Sales and Appointments.",
        "Finalized SRS Dossier, Opt-Out Validation Matrix, Sales Agent Docs",
        "Completed"
    ],
    [
        "Day 3",
        "Esha Mushtaq",
        "Basic",
        "Tasks 2 & 3: Appointments, UI Review & Presentation",
        "• Test Appointment Coordinator Agent (booking slots & conflict prevention).\n• Proofread SRS formatting, tables, and deliverable compliance.\n• Assist in preparing project presentation slides for Dawley Institute review.\n• Conduct end-user UI verification on the Streamlit dashboard.",
        "Appointment Agent Test Log, Polished SRS Formatting, Slide Drafts",
        "Completed"
    ],
    [
        "Day 3",
        "Syed Bilawal",
        "Basic",
        "Task 1 & Presentation Delivery",
        "• Document Task 1 deliverable: 'Basic Chatbot vs Autonomous AI Agent'.\n• Structure team presentation outline addressing all 7 assigned tasks.\n• Perform end-to-end manual user walkthrough in Streamlit UI.\n• Prepare Q&A responses for individual assessment questioning.",
        "Task 1 Comparison Section, Presentation Slide Deck, Demo Script",
        "Completed"
    ]
]

# Write data rows
row_start = 5
for r_idx, row_values in enumerate(data, start=row_start):
    ws.row_dimensions[r_idx].height = 48 if len(row_values[4]) > 100 else 30
    for c_idx, val in enumerate(row_values, start=1):
        cell = ws.cell(row=r_idx, column=c_idx)
        cell.value = val
        cell.font = Font(name="Calibri", size=10)
        cell.border = thin_border
        
        # Alignment
        if c_idx in [1, 2, 7]:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        elif c_idx == 3:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.font = Font(name="Calibri", size=10, bold=True)
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        # Status badge styling
        if c_idx == 7:
            cell.fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
            cell.font = Font(name="Calibri", size=10, bold=True, color="375623")

        # Color row accents by Day
        if c_idx == 1:
            if "Day 1" in val:
                cell.fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
            elif "Day 2" in val:
                cell.fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
            elif "Day 3" in val:
                cell.fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
            cell.font = Font(name="Calibri", size=10, bold=True)

# Set Column Widths
col_widths = {
    1: 12,  # Day
    2: 24,  # Team Member
    3: 26,  # Qualification
    4: 28,  # Task Topic
    5: 55,  # Assigned Tasks
    6: 35,  # Deliverables
    7: 15   # Status
}
for col_idx, width in col_widths.items():
    ws.column_dimensions[get_column_letter(col_idx)].width = width

# Sheet 2: Member Skills & Task Ownership Matrix
ws2 = wb.create_sheet(title="Member Skill Matrix")
ws2.merge_cells("A1:E1")
ws2["A1"] = "HCCDA AI — TEAM 3: MEMBER SKILL & RESPONSIBILITY MATRIX"
ws2["A1"].font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
ws2["A1"].fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 32

matrix_headers = ["Team Member", "Assessed Score", "Assigned Role", "Skill Level", "Core Project Responsibilities"]
ws2.row_dimensions[3].height = 24
for col_idx, h in enumerate(matrix_headers, start=1):
    c = ws2.cell(row=3, column=col_idx)
    c.value = h
    c.fill = header_fill
    c.font = header_font
    c.alignment = Alignment(horizontal="center", vertical="center")
    c.border = thin_border

matrix_data = [
    ["Waqas Islam", "95.0", "Lead Developer & Data Analyst", "Knows All Things (Expert)", "Overall architecture, Master Coordinator Agent, Reporting Agent, Database engine, KPI charts, CLI runner, end-to-end integration."],
    ["Ateeq Qadir", "Not provided", "Security & QA Engineer", "Intermediate", "Task 6 Security guardrails, PII masking, Prompt injection protection, Human Approval Center (HITL) policies, Pytest test suite."],
    ["M. Kaif ul Hassan (Khaf)", "95.0", "Technical Writer & Agent Specialist", "Intermediate", "SRS Document lead author, Task 4 Sales follow-up process & Opt-out compliance, Support ticket workflows, agent interaction diagrams."],
    ["Syed Bilawal", "97.5", "Team Coordinator & Presenter", "Basic", "Task 1 Chatbot vs AI Agent comparison, presentation slide deck, team coordination, UI manual walkthrough, presentation lead."],
    ["Esha Mushtaq", "93.5", "Business Analyst & UI Tester", "Basic", "SRS Document co-author, Appointment Coordinator Agent validation, conflict prevention testing, slide formatting, usability review."]
]

for r_idx, row in enumerate(matrix_data, start=4):
    ws2.row_dimensions[r_idx].height = 36
    for c_idx, val in enumerate(row, start=1):
        cell = ws2.cell(row=r_idx, column=c_idx)
        cell.value = val
        cell.font = Font(name="Calibri", size=10)
        cell.border = thin_border
        if c_idx in [1, 2, 4]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        elif c_idx == 3:
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.font = Font(name="Calibri", size=10, bold=True)
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

matrix_col_widths = {1: 22, 2: 15, 3: 30, 4: 25, 5: 60}
for col_idx, w in matrix_col_widths.items():
    ws2.column_dimensions[get_column_letter(col_idx)].width = w

# Save Excel file
excel_path = os.path.join(os.path.dirname(__file__), "Team3_Project_Work_Plan.xlsx")
wb.save(excel_path)
print(f"Excel file successfully generated at: {excel_path}")

# Also generate a clean CSV file
csv_path = os.path.join(os.path.dirname(__file__), "Team3_Project_Work_Plan.csv")
with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    for r in data:
        # Clean line breaks for CSV readability
        cleaned_row = [r[0], r[1], r[2], r[3], r[4].replace("\n", " "), r[5], r[6]]
        writer.writerow(cleaned_row)
print(f"CSV file successfully generated at: {csv_path}")
