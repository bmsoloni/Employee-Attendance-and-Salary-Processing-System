import sqlite3
import os

DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "payroll.db")

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cur = conn.cursor()

        # Employees table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                monthly_base REAL NOT NULL,
                allowances REAL DEFAULT 0.0,
                hourly_ot_rate REAL NOT NULL,
                tax_rate REAL DEFAULT 0.05
            )
        """)

        # Attendance logs: captures daily hours worked and overtime
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                status TEXT CHECK(status IN ('Present', 'Half-day', 'Leave', 'Absent')) NOT NULL,
                ot_hours REAL DEFAULT 0.0,
                UNIQUE(emp_id, date),
                FOREIGN KEY(emp_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)
        conn.commit()