import csv
import os
from src.database import get_connection

def import_employees_csv(filepath: str) -> int:
    """Reads employee data from CSV and syncs with SQLite."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    inserted_count = 0
    with open(filepath, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        with get_connection() as conn:
            cur = conn.cursor()
            for row in reader:
                cur.execute("""
                    INSERT INTO employees (id, name, department, monthly_base, allowances, hourly_ot_rate, tax_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        department=excluded.department,
                        monthly_base=excluded.monthly_base,
                        allowances=excluded.allowances,
                        hourly_ot_rate=excluded.hourly_ot_rate,
                        tax_rate=excluded.tax_rate
                """, (
                    int(row["emp_id"]),
                    row["name"].strip(),
                    row["department"].strip(),
                    float(row["monthly_base"]),
                    float(row.get("allowances", 0.0) or 0.0),
                    float(row.get("hourly_ot_rate", 0.0) or 0.0),
                    float(row.get("tax_rate", 0.05) or 0.05)
                ))
                inserted_count += 1
            conn.commit()

    return inserted_count


def import_attendance_csv(filepath: str) -> int:
    """Reads raw attendance logs from CSV and imports into SQLite."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    inserted_count = 0
    valid_statuses = {"Present", "Half-day", "Leave", "Absent"}

    with open(filepath, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        with get_connection() as conn:
            cur = conn.cursor()
            for row in reader:
                status = row["status"].strip()
                if status not in valid_statuses:
                    continue  # skip or log invalid entries

                cur.execute("""
                    INSERT INTO attendance (emp_id, date, status, ot_hours)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(emp_id, date) DO UPDATE SET
                        status=excluded.status,
                        ot_hours=excluded.ot_hours
                """, (
                    int(row["emp_id"]),
                    row["date"].strip(),
                    status,
                    float(row.get("ot_hours", 0.0) or 0.0)
                ))
                inserted_count += 1
            conn.commit()

    return inserted_count