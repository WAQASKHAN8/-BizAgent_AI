from datetime import datetime, timedelta
from database.db import get_connection, log_audit, create_approval_request, get_business_settings, create_notification
from tools.calendar_tool import CalendarTool

class AppointmentAgent:
    """
    Agent 4: Appointment & Scheduling Agent
    
    Responsibilities:
    - Receive appointment requests.
    - Check available time slots.
    - Retrieve business working hours.
    - Suggest suitable appointment times.
    - Create appointment bookings.
    - Detect and prevent scheduling conflicts (double-booking).
    - Reschedule or cancel appointments.
    - Send appointment reminders.
    - Notify relevant business staff.
    
    Restrictions:
    - Never double-book appointments under any circumstance.
    - Require approval for cancellations of VIP / Enterprise client meetings.
    - Never confirm unavailable time slots.
    """
    NAME = "Appointment & Scheduling Agent"
    ROLE = "Calendar Coordination, Slot Checking & Conflict Prevention"
    PERMITTED_ACTIONS = [
        "check_availability",
        "check_slots",
        "book_appointment",
        "book_meeting",
        "reschedule_meeting",
        "cancel_meeting",
        "detect_conflicts",
        "send_reminder"
    ]

    @classmethod
    def get_working_hours(cls) -> str:
        settings = get_business_settings()
        return settings.get("business_hours", "09:00 - 18:00 (Mon-Fri)")

    @classmethod
    def get_open_slots(cls, target_date_str: str = None) -> list:
        slots = CalendarTool.get_available_slots(target_date_str)
        log_audit(cls.NAME, "CHECK_SLOTS", f"Queried open slots for date: {target_date_str or 'tomorrow'}")
        return slots

    @classmethod
    def schedule_meeting(cls, client_name: str, email: str, service: str, slot_time: str, notes: str = "", phone: str = "") -> dict:
        result = CalendarTool.book_appointment(client_name, email, service, slot_time, notes)
        if result["success"]:
            create_notification(
                title="New Confirmed Appointment",
                message=f"Meeting scheduled with {client_name} for {slot_time} ({service}).",
                notif_type="INFO"
            )
        return result

    @classmethod
    def reschedule_meeting(cls, appointment_id: int, new_slot_time: str) -> dict:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            # Conflict check for new slot
            cursor.execute("SELECT id, client_name FROM appointments WHERE slot_time = ? AND status = 'Confirmed' AND id != ?", (new_slot_time, appointment_id))
            conflict = cursor.fetchone()
            if conflict:
                return {
                    "success": False,
                    "message": f"Conflict detected: Slot {new_slot_time} is already booked by {conflict['client_name']}."
                }

            cursor.execute("UPDATE appointments SET slot_time = ?, status = 'Rescheduled' WHERE id = ?", (new_slot_time, appointment_id))
            affected = cursor.rowcount
            conn.commit()

            if affected > 0:
                log_audit(cls.NAME, "RESCHEDULE_MEETING", f"Rescheduled appointment #{appointment_id} to {new_slot_time}")
                return {"success": True, "message": f"Appointment #{appointment_id} successfully rescheduled to {new_slot_time}."}
            return {"success": False, "message": f"Appointment #{appointment_id} not found."}
        finally:
            conn.close()

    @classmethod
    def cancel_meeting(cls, appointment_id: int, reason: str = "Client requested cancellation", is_vip: bool = False) -> dict:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
            appt = cursor.fetchone()
            if not appt:
                return {"success": False, "message": f"Appointment #{appointment_id} not found."}

            appt_dict = dict(appt)

            # If VIP or high priority, require Human Approval
            if is_vip or "Enterprise" in appt_dict.get("service", ""):
                app_id = create_approval_request(
                    agent_name=cls.NAME,
                    action_type="APPOINTMENT_CANCELLATION",
                    title=f"Cancel VIP Meeting: {appt_dict['client_name']}",
                    description=f"Request to cancel appointment #{appointment_id} for {appt_dict['client_name']} ({appt_dict['slot_time']}). Reason: {reason}",
                    risk_level="High",
                    proposed_operation=f"UPDATE appointments SET status='Cancelled' WHERE id={appointment_id}",
                    payload={"appointment_id": appointment_id, "client": appt_dict["client_name"], "reason": reason}
                )
                return {
                    "success": False,
                    "approval_required": True,
                    "approval_id": app_id,
                    "message": f"Cancelling Enterprise appointment #{appointment_id} requires manager authorization. Request #{app_id} created."
                }

            cursor.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (appointment_id,))
            conn.commit()

            log_audit(cls.NAME, "CANCEL_MEETING", f"Cancelled appointment #{appointment_id}")
            return {"success": True, "message": f"Appointment #{appointment_id} has been cancelled."}
        finally:
            conn.close()
