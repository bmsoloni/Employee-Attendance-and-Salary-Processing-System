import os
import calendar
from datetime import datetime
from src.database import get_connection
from src.payroll import process_employee_payroll

REPORTS_DIR = "reports"

def generate_monthly_summary(year: int, month: int):
    os.makedirs(REPORTS_DIR, exist_ok=True)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM employees ORDER BY id ASC")
        employees = cur.fetchall()

    if not employees:
        print("No registered employees found to process.")
        return

    records = [process_employee_payroll(emp["id"], year, month) for emp in employees]
    below_threshold_list = [r for r in records if r["below_threshold"]]

    total_base = sum(r["monthly_base"] for r in records)
    total_ot_paid = sum(r["ot_pay"] for r in records)
    total_lop = sum(r["lop_deduction"] for r in records)
    total_disbursed = sum(r["final_salary"] for r in records)

    month_name = calendar.month_name[month]
    filename = f"payroll_summary_{year}_{month:02d}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append(f"          EXECUTIVE PAYROLL & ATTENDANCE SUMMARY: {month_name.upper()} {year}")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Total Employees Processed: {len(records)}\n")

    # Table of All Employees
    header = f"{'ID':<4} {'Name':<16} {'Dept':<12} {'Attn %':<8} {'OT (Hrs)':<9} {'OT Pay':<9} {'LOP':<9} {'Final Pay':<10}"
    report_lines.append(header)
    report_lines.append("-" * 80)
    for r in records:
        line = (f"{r['emp_id']:<4} {r['name']:<16} {r['department']:<12} "
                f"{r['attendance_pct']:>6.1f}%  {r['ot_hours']:>6.1f}h  "
                f"${r['ot_pay']:>7.2f}  -${r['lop_deduction']:>6.2f}  ${r['final_salary']:>9.2f}")
        report_lines.append(line)

    # Flagged Threshold Violations
    report_lines.append("\n" + "-" * 80)
    report_lines.append("⚠️  CRITICAL: EMPLOYEES BELOW MINIMUM ATTENDANCE THRESHOLD (< 75%)")
    report_lines.append("-" * 80)
    if below_threshold_list:
        for b in below_threshold_list:
            report_lines.append(
                f"• #{b['emp_id']:02d} {b['name']} ({b['department']}) -> Attendance: {b['attendance_pct']}% "
                f"({b['effective_days']:.1f}/{b['days_in_month']} days) | Absent: {b['absent_days']:.1f} days"
            )
    else:
        report_lines.append("✓ All employees met or exceeded the 75% attendance benchmark.")

    # High-level Financial Summary
    report_lines.append("\n" + "=" * 80)
    report_lines.append("FINANCIAL TOTALS FOR DISBURSEMENT")
    report_lines.append("-" * 80)
    report_lines.append(f"Total Base Commitment : ${total_base:>12,.2f}")
    report_lines.append(f"Total Overtime Payout : +${total_ot_paid:>11,.2f}")
    report_lines.append(f"Total LOP Deductions  : -${total_lop:>11,.2f}")
    report_lines.append(f"NET CASH DISBURSEMENT : ${total_disbursed:>12,.2f}")
    report_lines.append("=" * 80)

    final_content = "\n".join(report_lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(final_content)
    print(f"\n[✓] Report saved successfully to: {filepath}\n")