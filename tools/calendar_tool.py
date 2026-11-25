from datetime import datetime, timedelta
from database.db import get_connection, log_audit

class CalendarTool:
    """Tooling for Appointment Coordination, Slot Checking, and Conflict Resolution."""

    @staticmethod
    def get_all_appointments():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appointments ORDER BY slot_time ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_available_slots(target_date_str: str = None) -> list:
        """
        Calculates open 30-min booking slots for a given day,
        excluding existing confirmed appointments.
        """
        if not target_date_str:
            target_date = (datetime.now() + timedelta(days=1)).date()
        else:
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = (datetime.now() + timedelta(days=1)).date()

        standard_slots = ["09:00", "10:00", "11:00", "13:30", "14:30", "15:30", "16:30"]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT slot_time FROM appointments WHERE status = 'Confirmed'")
        booked_times = [r[0] for r in cursor.fetchall()]
        conn.close()

        available = []
        for slot in standard_slots:
            full_slot_str = f"{target_date} {slot}"
            if full_slot_str not in booked_times:
                available.append(full_slot_str)

        return available

    @staticmethod
    def book_appointment(client_name: str, email: str, service: str, slot_time: str, notes: str = "") -> dict:
        """Books an appointment if no conflict exists."""
        conn = get_connection()
        cursor = conn.cursor()

        # Conflict check
        cursor.execute("SELECT id, client_name FROM appointments WHERE slot_time = ? AND status = 'Confirmed'", (slot_time,))
        conflict = cursor.fetchone()
        if conflict:
            conn.close()
            log_audit("Appointment Agent", "BOOKING_CONFLICT", f"Conflict for {slot_time} with {conflict['client_name']}", status="FAILED")
            return {
                "success": False,
                "message": f"Time slot {slot_time} is already booked by {conflict['client_name']}. Please select an alternative slot."
            }

        cursor.execute("""
        INSERT INTO appointments (client_name, email, service, slot_time, duration_minutes, status, notes)
        VALUES (?, ?, ?, ?, 30, 'Confirmed', ?)
        """, (client_name, email, service, slot_time, notes))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()

        log_audit("Appointment Agent", "APPOINTMENT_CONFIRMED", f"Appointment #{new_id} booked for {client_name} at {slot_time}")
        return {
            "success": True,
            "appointment_id": new_id,
            "message": f"Appointment confirmed for {client_name} on {slot_time} ({service})."
        }
