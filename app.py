from pathlib import Path
import calendar
import sys

import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from src.database import get_connection, init_db
from src.loaders import import_attendance_csv, import_employees_csv
from src.payroll import ATTENDANCE_THRESHOLD_PCT, process_employee_payroll
from src.reporting import generate_monthly_summary


st.set_page_config(page_title="Payline | Payroll operations", page_icon="▦", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --ink: #18252b; --muted: #6d7a7b; --paper: #f7f6f1; --line: #dfe3dc; --accent: #e56c45; }
    .stApp { background: var(--paper); color: var(--ink); }
    [data-testid="stSidebar"] { background: #1d3032; border-right: 0; }
    [data-testid="stSidebar"] * { color: #edf2ec; }
    h1, h2, h3, p, label, .stMarkdown { font-family: 'Manrope', sans-serif; }
    h1 { font-size: 2.65rem !important; letter-spacing: -.06em; line-height: 1.05; }
    h2 { font-size: 1.3rem !important; letter-spacing: -.03em; }
    .eyebrow { color: var(--accent); font: 500 .72rem 'DM Mono', monospace; letter-spacing: .12em; text-transform: uppercase; }
    .lede { color: var(--muted); font-size: .96rem; margin-top: -.4rem; }
    .metric { background: white; border: 1px solid var(--line); border-radius: 10px; padding: 1.05rem 1.15rem; min-height: 112px; }
    .metric-label { color: var(--muted); font: 500 .7rem 'DM Mono', monospace; letter-spacing: .08em; text-transform: uppercase; }
    .metric-value { color: var(--ink); font-size: 1.7rem; font-weight: 800; letter-spacing: -.05em; margin-top: .45rem; }
    .metric-note { color: var(--muted); font-size: .76rem; margin-top: .25rem; }
    .section-rule { border-top: 1px solid var(--line); margin: 2rem 0 1.25rem; }
    .status-alert { color: #bd4a35; font-weight: 700; }
    .stButton > button { border-radius: 7px; border: 0; background: var(--accent); color: white; font-weight: 700; }
    .stButton > button:hover { background: #c95736; color: white; }
    div[data-testid="stDataFrame"] { border: 1px solid var(--line); }
    </style>
    """,
    unsafe_allow_html=True,
)


def money(value: float) -> str:
    return f"${value:,.2f}"


def load_records(year: int, month: int) -> list[dict]:
    with get_connection() as conn:
        employees = conn.execute("SELECT id FROM employees ORDER BY id").fetchall()
    return [process_employee_payroll(row["id"], year, month) for row in employees]


def load_attendance(year: int, month: int) -> pd.DataFrame:
    start = f"{year:04d}-{month:02d}-01"
    end = f"{year:04d}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"
    with get_connection() as conn:
        return pd.read_sql_query(
            """SELECT a.date AS Date, e.name AS Employee, e.department AS Department,
                      a.status AS Status, a.ot_hours AS OT_hours
               FROM attendance a JOIN employees e ON e.id = a.emp_id
               WHERE a.date BETWEEN ? AND ? ORDER BY a.date, e.name""",
            conn,
            params=(start, end),
        )


def metric(label: str, value: str, note: str) -> None:
    st.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)


def overview(records: list[dict], year: int, month: int) -> None:
    month_label = f"{calendar.month_name[month]} {year}"
    if not records:
        st.info("No employees are loaded yet. Use Data sync to import the employee CSV.")
        return
    total_pay = sum(row["final_salary"] for row in records)
    total_ot = sum(row["ot_pay"] for row in records)
    avg_attendance = sum(row["attendance_pct"] for row in records) / len(records)
    alerts = sum(row["below_threshold"] for row in records)
    st.markdown(f'<div class="eyebrow">Payroll control room / {month_label}</div>', unsafe_allow_html=True)
    st.title("A clearer view of payday.")
    st.markdown("<p class='lede'>Attendance signals, salary movement, and exceptions in one calm workspace.</p>", unsafe_allow_html=True)
    st.write("")
    columns = st.columns(4)
    with columns[0]: metric("Net disbursement", money(total_pay), f"Across {len(records)} employees")
    with columns[1]: metric("Overtime payout", money(total_ot), "Added to base payroll")
    with columns[2]: metric("Avg. attendance", f"{avg_attendance:.1f}%", f"Benchmark is {ATTENDANCE_THRESHOLD_PCT:.0f}%")
    with columns[3]: metric("Needs attention", str(alerts), "Below attendance benchmark")
    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    left, right = st.columns([1.5, 1])
    with left:
        st.subheader("Payroll at a glance")
        table = pd.DataFrame(records)[["emp_id", "name", "department", "attendance_pct", "ot_pay", "lop_deduction", "final_salary"]]
        table.columns = ["ID", "Employee", "Department", "Attendance %", "OT pay", "LOP deduction", "Net pay"]
        st.dataframe(table.style.format({"Attendance %": "{:.1f}%", "OT pay": money, "LOP deduction": money, "Net pay": money}), use_container_width=True, hide_index=True)
    with right:
        st.subheader("Attendance watch")
        flagged = [row for row in records if row["below_threshold"]]
        if flagged:
            for row in flagged:
                st.markdown(f"**{row['name']}**  <span class='status-alert'>{row['attendance_pct']:.1f}%</span><br><small>{row['department']} · {row['absent_days']:.1f} absent days</small>", unsafe_allow_html=True)
                st.progress(min(row["attendance_pct"] / 100, 1.0))
        else:
            st.success("Every employee is above the attendance benchmark.")


def main() -> None:
    init_db()
    with st.sidebar:
        st.markdown("## PAYLINE")
        st.caption("Attendance + salary operations")
        st.markdown("---")
        year = st.number_input("Report year", min_value=2020, max_value=2100, value=2026, step=1)
        month = st.selectbox("Report month", range(1, 13), index=8, format_func=lambda value: calendar.month_name[value])
        page = st.radio("Workspace", ["Overview", "Payroll ledger", "Attendance log", "Data sync"], label_visibility="collapsed")
        st.markdown("---")
        st.caption("Source of truth")
        st.code("SQLite / payroll.db", language="text")
    records = load_records(int(year), int(month))
    if page == "Overview":
        overview(records, int(year), int(month))
    elif page == "Payroll ledger":
        st.markdown('<div class="eyebrow">Monthly payroll</div>', unsafe_allow_html=True)
        st.title("Payroll ledger")
        if records:
            ledger = pd.DataFrame(records)[["emp_id", "name", "department", "monthly_base", "allowances", "ot_hours", "ot_pay", "lop_deduction", "tax_deduction", "final_salary"]]
            ledger.columns = ["ID", "Employee", "Department", "Base", "Allowances", "OT hours", "OT pay", "LOP deduction", "Tax", "Net pay"]
            st.dataframe(ledger.style.format({column: money for column in ["Base", "Allowances", "OT pay", "LOP deduction", "Tax", "Net pay"]}), use_container_width=True, hide_index=True)
            if st.button("Generate text report", type="primary"):
                generate_monthly_summary(int(year), int(month))
                st.success(f"Report saved to reports/payroll_summary_{int(year)}_{int(month):02d}.txt")
        else:
            st.info("Import employees to build the ledger.")
    elif page == "Attendance log":
        st.markdown('<div class="eyebrow">Daily records</div>', unsafe_allow_html=True)
        st.title("Attendance log")
        attendance = load_attendance(int(year), int(month))
        if attendance.empty:
            st.info("No attendance records for this period.")
        else:
            st.dataframe(attendance, use_container_width=True, hide_index=True)
            st.caption(f"{len(attendance)} records · {attendance['Employee'].nunique()} employees · {attendance['OT_hours'].sum():.1f} overtime hours")
    else:
        st.markdown('<div class="eyebrow">Bring in the latest files</div>', unsafe_allow_html=True)
        st.title("Data sync")
        st.markdown("<p class='lede'>Import CSV files into the same SQLite database used by payroll calculations.</p>", unsafe_allow_html=True)
        employee_file = st.file_uploader("Employee master", type="csv", key="employees")
        attendance_file = st.file_uploader("Attendance log", type="csv", key="attendance")
        if st.button("Import selected files", type="primary"):
            imported = []
            if employee_file:
                destination = APP_DIR / "data" / "uploaded_employees.csv"
                destination.write_bytes(employee_file.getvalue())
                imported.append(f"{import_employees_csv(str(destination))} employees")
            if attendance_file:
                destination = APP_DIR / "data" / "uploaded_attendance.csv"
                destination.write_bytes(attendance_file.getvalue())
                imported.append(f"{import_attendance_csv(str(destination))} attendance records")
            if imported:
                st.success("Imported " + " and ".join(imported) + ".")
                st.rerun()
            else:
                st.warning("Choose at least one CSV file first.")


if __name__ == "__main__":
    main()