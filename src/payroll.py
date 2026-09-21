import calendar
from src.database import get_connection

ATTENDANCE_THRESHOLD_PCT = 75.0  # Alert threshold

def process_employee_payroll(emp_id: int, year: int, month: int) -> dict:
    _, days_in_month = calendar.monthrange(year, month)
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{days_in_month:02d}"

    with get_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM employees WHERE id = ?", (emp_id,))
        emp = cur.fetchone()
        if not emp:
            raise ValueError(f"Employee #{emp_id} not found.")

        # Pull attendance summary
        cur.execute("""
            SELECT 
                status, 
                COUNT(*) as count,
                SUM(ot_hours) as total_ot
            FROM attendance 
            WHERE emp_id = ? AND date BETWEEN ? AND ?
            GROUP BY status
        """, (emp_id, start_date, end_date))
        rows = cur.fetchall()

    status_counts = {r["status"]: r["count"] for r in rows}
    total_ot_hours = sum(r["total_ot"] or 0.0 for r in rows)

    present_days = status_counts.get("Present", 0)
    half_days = status_counts.get("Half-day", 0)
    paid_leaves = status_counts.get("Leave", 0)
    recorded_absents = status_counts.get("Absent", 0)

    # Calculate effective attended days
    effective_attended_days = present_days + (half_days * 0.5) + paid_leaves
    total_recorded = present_days + half_days + paid_leaves + recorded_absents
    unrecorded_days = max(0, days_in_month - total_recorded)
    total_absent_days = recorded_absents + (half_days * 0.5) + unrecorded_days

    # 1. Attendance Percentage
    attendance_pct = round((effective_attended_days / days_in_month) * 100, 2)
    below_threshold = attendance_pct < ATTENDANCE_THRESHOLD_PCT

    # 2. Overtime Pay
    ot_pay = round(total_ot_hours * emp["hourly_ot_rate"], 2)

    # 3. Loss of Pay (LOP) & Final Salary
    daily_rate = emp["monthly_base"] / days_in_month
    lop_deduction = round(total_absent_days * daily_rate, 2)
    
    gross_earnings = round(emp["monthly_base"] + emp["allowances"] + ot_pay, 2)
    taxable_income = max(0.0, gross_earnings - lop_deduction)
    tax_deduction = round(taxable_income * emp["tax_rate"], 2)
    
    final_salary = round(gross_earnings - lop_deduction - tax_deduction, 2)

    return {
        "emp_id": emp["id"],
        "name": emp["name"],
        "department": emp["department"],
        "monthly_base": emp["monthly_base"],
        "allowances": emp["allowances"],
        "days_in_month": days_in_month,
        "effective_days": effective_attended_days,
        "absent_days": total_absent_days,
        "attendance_pct": attendance_pct,
        "below_threshold": below_threshold,
        "ot_hours": total_ot_hours,
        "ot_pay": ot_pay,
        "lop_deduction": lop_deduction,
        "tax_deduction": tax_deduction,
        "final_salary": final_salary
    }