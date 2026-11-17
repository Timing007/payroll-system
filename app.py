"""Flask web application for the Payroll Management System."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from services.payroll_service import PayrollService
from storage.csv_repository import CSVRepository

import shutil

app = Flask(__name__)
app.secret_key = "payroll-secret-key-2024"

BASE_DIR = Path(__file__).parent

# On Vercel serverless environment, use /tmp for mutable CSV and payslip file writes
IS_VERCEL = bool(os.environ.get("VERCEL"))
if IS_VERCEL:
    TEMP_DIR = Path("/tmp")
    DATA_DIR = TEMP_DIR / "data"
    OUTPUT_DIR = TEMP_DIR / "output" / "payslips"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    orig_emp = BASE_DIR / "data" / "employees.csv"
    orig_logs = BASE_DIR / "data" / "payroll_logs.csv"
    target_emp = DATA_DIR / "employees.csv"
    target_logs = DATA_DIR / "payroll_logs.csv"

    if orig_emp.exists() and not target_emp.exists():
        shutil.copy2(orig_emp, target_emp)
    if orig_logs.exists() and not target_logs.exists():
        shutil.copy2(orig_logs, target_logs)
else:
    DATA_DIR = BASE_DIR / "data"
    OUTPUT_DIR = BASE_DIR / "output" / "payslips"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

repo = CSVRepository(
    str(DATA_DIR / "employees.csv"),
    str(DATA_DIR / "payroll_logs.csv"),
)
service = PayrollService(repo)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    employees = repo.get_all_employees()
    total_employees = len(employees)

    logs = repo.get_payroll_logs()
    recent_logs = logs[-10:][::-1]

    # Department summary: from latest run if logs exist, otherwise projected
    department_summary = service.department_summary()
    if not department_summary:
        analytics_data = service.get_analytics()
        department_summary = {d["department"]: d["total_net"] for d in analytics_data["departments"]}

    dept_set = {e.get("department", "") for e in employees if e.get("department")}

    last_run_date = ""
    if logs:
        last_run_date = logs[-1].get("run_date", "")

    return render_template(
        "index.html",
        total_employees=total_employees,
        departments=sorted(dept_set),
        department_summary=department_summary,
        recent_logs=recent_logs,
        last_run_date=last_run_date,
    )


# ---------------------------------------------------------------------------
# Employees (with Search, Filtering & Pagination)
# ---------------------------------------------------------------------------

@app.route("/employees")
def employees():
    all_employees = repo.get_all_employees()
    
    # Query parameters
    search = request.args.get("search", "").strip().lower()
    dept_filter = request.args.get("dept", "").strip()
    type_filter = request.args.get("type", "").strip()
    
    filtered = all_employees
    if search:
        filtered = [
            e for e in filtered
            if search in e.get("name", "").lower()
            or search in e.get("emp_id", "").lower()
            or search in e.get("department", "").lower()
        ]
    if dept_filter:
        filtered = [e for e in filtered if e.get("department") == dept_filter]
    if type_filter:
        filtered = [e for e in filtered if e.get("emp_type") == type_filter]

    # Unique departments for dropdown
    all_depts = sorted({e.get("department", "") for e in all_employees if e.get("department")})

    # Pagination
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
        
    try:
        per_page = int(request.args.get("per_page", 25))
    except (ValueError, TypeError):
        per_page = 25

    total_filtered = len(filtered)
    total_pages = max(1, (total_filtered + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_items = filtered[start_idx:end_idx]

    return render_template(
        "employees.html",
        employees=page_items,
        total_count=len(all_employees),
        filtered_count=total_filtered,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        search=request.args.get("search", ""),
        current_dept=dept_filter,
        current_type=type_filter,
        all_departments=all_depts,
    )


@app.route("/employees/add", methods=["GET", "POST"])
def add_employee():
    if request.method == "POST":
        try:
            row = _build_row_from_form(request.form)
            repo.add_employee(row)
            flash(f"Employee {row['emp_id']} added successfully.", "success")
            return redirect(url_for("employees"))
        except ValueError as exc:
            flash(str(exc), "danger")
    return render_template("add_employee.html")


@app.route("/employees/<emp_id>/edit", methods=["GET", "POST"])
def edit_employee(emp_id: str):
    employee = repo.get_employee(emp_id)
    if employee is None:
        flash(f"Employee {emp_id} not found.", "warning")
        return redirect(url_for("employees"))

    if request.method == "POST":
        try:
            row = _build_row_from_form(request.form)
            repo.update_employee(emp_id, row)
            flash(f"Employee {emp_id} updated successfully.", "success")
            return redirect(url_for("employees"))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template("edit_employee.html", employee=employee)


@app.route("/employees/<emp_id>/delete", methods=["POST"])
def delete_employee(emp_id: str):
    deleted = repo.delete_employee(emp_id)
    if deleted:
        flash(f"Employee {emp_id} deleted.", "success")
    else:
        flash(f"Employee {emp_id} not found.", "warning")
    return redirect(url_for("employees"))


# ---------------------------------------------------------------------------
# Payroll
# ---------------------------------------------------------------------------

@app.route("/payroll/run", methods=["GET", "POST"])
def run_payroll():
    results = None
    error = None
    if request.method == "POST":
        try:
            results = service.run_monthly_payroll()
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            flash(f"Payroll run failed: {error}", "danger")
    return render_template("run_payroll.html", results=results, error=error)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@app.route("/analytics")
def analytics():
    analytics_data = service.get_analytics()
    return render_template("analytics.html", analytics=analytics_data)


# ---------------------------------------------------------------------------
# Payslips
# ---------------------------------------------------------------------------

@app.route("/payslips")
def payslips():
    files = []
    if OUTPUT_DIR.exists():
        files = sorted(
            [f.name for f in OUTPUT_DIR.iterdir() if f.suffix == ".txt"],
            reverse=True,
        )
    return render_template("payslips.html", files=files, content=None, filename=None)


@app.route("/payslips/<filename>")
def view_payslip(filename: str):
    # Safety: only allow simple filenames (no path traversal)
    safe_name = Path(filename).name
    file_path = OUTPUT_DIR / safe_name
    content = None
    if file_path.exists() and file_path.suffix == ".txt":
        content = file_path.read_text(encoding="utf-8")
    else:
        flash("Payslip file not found.", "warning")

    files = sorted(
        [f.name for f in OUTPUT_DIR.iterdir() if f.suffix == ".txt"],
        reverse=True,
    ) if OUTPUT_DIR.exists() else []

    return render_template(
        "payslips.html", files=files, content=content, filename=safe_name
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_row_from_form(form) -> dict:
    """Build a CSV row dict from submitted form data."""
    emp_type = form.get("emp_type", "full_time")
    row: dict[str, str] = {
        "emp_id": form.get("emp_id", "").strip(),
        "name": form.get("name", "").strip(),
        "department": form.get("department", "").strip(),
        "emp_type": emp_type,
        "base_pay": "0",
        "extra1": "0",
        "extra2": "0",
        "extra3": "0",
        "extra4": "0",
    }
    if emp_type == "full_time":
        row["base_pay"] = form.get("base_pay", "0").strip()
        row["extra1"] = form.get("hra_pct", "0").strip()
        row["extra2"] = form.get("da_pct", "0").strip()
        row["extra3"] = form.get("tax_pct", "0").strip()
        row["extra4"] = form.get("pf_pct", "0").strip()
    elif emp_type == "part_time":
        row["extra1"] = form.get("hourly_rate", "0").strip()
        row["extra2"] = form.get("hours_worked", "0").strip()
    elif emp_type == "contract":
        row["extra1"] = form.get("project_fee", "0").strip()
    return row


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
