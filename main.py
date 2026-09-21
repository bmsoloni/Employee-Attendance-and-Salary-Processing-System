from src.database import init_db
from src.loaders import import_employees_csv, import_attendance_csv
from src.reporting import generate_monthly_summary

def main():
    init_db()

    while True:
        print("\n=== Payroll & Attendance Management System ===")
        print("1. Import Employees from CSV")
        print("2. Import Attendance Logs from CSV")
        print("3. Generate Monthly Payroll & Summary Report")
        print("4. Exit")

        choice = input("Enter choice (1-4): ").strip()

        if choice == "1":
            path = input("CSV Path [Default: data/employees.csv]: ").strip() or "data/employees.csv"
            try:
                count = import_employees_csv(path)
                print(f"[✓] Successfully imported/updated {count} employees from '{path}'.")
            except Exception as e:
                print(f"[!] Error: {e}")

        elif choice == "2":
            path = input("CSV Path [Default: data/attendance_sep_2026.csv]: ").strip() or "data/attendance_sep_2026.csv"
            try:
                count = import_attendance_csv(path)
                print(f"[✓] Successfully imported {count} attendance records from '{path}'.")
            except Exception as e:
                print(f"[!] Error: {e}")

        elif choice == "3":
            try:
                yr = int(input("Year (e.g. 2026): ").strip())
                mo = int(input("Month (1-12): ").strip())
                generate_monthly_summary(yr, mo)
            except ValueError:
                print("[!] Please enter valid numerical values for year and month.")

        elif choice == "4":
            print("Shutting down.")
            break
        else:
            print("Invalid selection.")

if __name__ == "__main__":
    main()