"""Pytest test suite for the Payroll Management System.

Tests cover:
- Employee model calculations and validations.
- CSVRepository CRUD operations.
- PayrollService.run_monthly_payroll() end-to-end.
"""

import pytest, os, csv
from models.employee import FullTimeEmployee, PartTimeEmployee, ContractEmployee
from storage.csv_repository import CSVRepository
from services.payroll_service import PayrollService


# ---------------------------------------------------------------------------
# Helper: build a tmp CSVRepository
# ---------------------------------------------------------------------------

def _make_repo(tmp_path):
    """Return a CSVRepository backed by temp files."""
    emp_csv = str(tmp_path / "employees.csv")
    log_csv = str(tmp_path / "payroll_logs.csv")
    return CSVRepository(emp_csv, log_csv)


# ---------------------------------------------------------------------------
# Employee model — net pay calculations
# ---------------------------------------------------------------------------


def test_full_time_net_pay():
    """base=50000, hra=20, da=10, tax=10, pf=12 → net=54000.0"""
    emp = FullTimeEmployee(
        emp_id="FT001",
        name="Alice",
        department="Engineering",
        base_pay=50_000,
        hra_pct=20,
        da_pct=10,
        tax_pct=10,
        pf_pct=12,
    )
    # gross = 50000 + 10000 + 5000 = 65000
    # deductions = 5000 + 6000 = 11000
    # net = 65000 - 11000 = 54000
    assert emp.calculate_net_pay() == pytest.approx(54_000.0)


def test_part_time_regular():
    """rate=200, hours=35 (≤40) → net=7000.0"""
    emp = PartTimeEmployee(
        emp_id="PT001",
        name="Bob",
        department="HR",
        hourly_rate=200,
        hours_worked=35,
    )
    assert emp.calculate_net_pay() == pytest.approx(7_000.0)


def test_part_time_overtime():
    """rate=200, hours=50 → 200*40 + 200*1.5*10 = 8000+3000 = 11000.0"""
    emp = PartTimeEmployee(
        emp_id="PT002",
        name="Carol",
        department="HR",
        hourly_rate=200,
        hours_worked=50,
    )
    assert emp.calculate_net_pay() == pytest.approx(11_000.0)


def test_contract_tds():
    """fee=100000 → net=90000.0 (10% TDS)"""
    emp = ContractEmployee(
        emp_id="CT001",
        name="Dave",
        department="IT",
        project_fee=100_000,
    )
    assert emp.calculate_net_pay() == pytest.approx(90_000.0)


# ---------------------------------------------------------------------------
# Employee model — validation errors
# ---------------------------------------------------------------------------


def test_negative_base_pay():
    """base_pay < 0 raises ValueError."""
    with pytest.raises(ValueError):
        FullTimeEmployee(
            emp_id="FT002",
            name="Eve",
            department="Finance",
            base_pay=-1,
        )


def test_empty_name():
    """Empty name raises ValueError."""
    with pytest.raises(ValueError):
        FullTimeEmployee(
            emp_id="FT003",
            name="",
            department="Finance",
            base_pay=40_000,
        )


def test_negative_hours():
    """hours_worked < 0 raises ValueError."""
    with pytest.raises(ValueError):
        PartTimeEmployee(
            emp_id="PT003",
            name="Frank",
            department="Ops",
            hourly_rate=100,
            hours_worked=-5,
        )


# ---------------------------------------------------------------------------
# CSVRepository — CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_employee(tmp_path):
    """Add a row and retrieve it back."""
    repo = _make_repo(tmp_path)
    row = {
        "emp_id": "E001",
        "name": "Grace",
        "department": "Marketing",
        "emp_type": "full_time",
        "base_pay": "60000",
        "extra1": "20",
        "extra2": "10",
        "extra3": "10",
        "extra4": "12",
    }
    repo.add_employee(row)
    result = repo.get_employee("E001")
    assert result is not None
    assert result["name"] == "Grace"
    assert result["emp_id"] == "E001"


def test_duplicate_emp_id(tmp_path):
    """Adding the same emp_id twice raises ValueError."""
    repo = _make_repo(tmp_path)
    row = {
        "emp_id": "E002",
        "name": "Heidi",
        "department": "Legal",
        "emp_type": "contract",
        "base_pay": "0",
        "extra1": "80000",
        "extra2": "0",
        "extra3": "0",
        "extra4": "0",
    }
    repo.add_employee(row)
    with pytest.raises(ValueError):
        repo.add_employee(row)


def test_update_employee(tmp_path):
    """Update a field and verify the change persists."""
    repo = _make_repo(tmp_path)
    row = {
        "emp_id": "E003",
        "name": "Ivan",
        "department": "Security",
        "emp_type": "part_time",
        "base_pay": "0",
        "extra1": "150",
        "extra2": "30",
        "extra3": "0",
        "extra4": "0",
    }
    repo.add_employee(row)
    updated = repo.update_employee("E003", {"name": "Ivan Updated"})
    assert updated is True
    result = repo.get_employee("E003")
    assert result is not None
    assert result["name"] == "Ivan Updated"


def test_delete_employee(tmp_path):
    """Delete an employee and verify they are gone."""
    repo = _make_repo(tmp_path)
    row = {
        "emp_id": "E004",
        "name": "Judy",
        "department": "Research",
        "emp_type": "full_time",
        "base_pay": "55000",
        "extra1": "15",
        "extra2": "8",
        "extra3": "10",
        "extra4": "12",
    }
    repo.add_employee(row)
    deleted = repo.delete_employee("E004")
    assert deleted is True
    assert repo.get_employee("E004") is None


# ---------------------------------------------------------------------------
# PayrollService — end-to-end run
# ---------------------------------------------------------------------------


def test_payroll_service_run(tmp_path):
    """Seed 1 employee of each type, run payroll, verify 3 result dicts."""
    repo = _make_repo(tmp_path)

    # Full-time: base=50000, hra=20, da=10, tax=10, pf=12 → net=54000
    repo.add_employee({
        "emp_id": "FT001",
        "name": "Alice FT",
        "department": "Engineering",
        "emp_type": "full_time",
        "base_pay": "50000",
        "extra1": "20",   # hra_pct
        "extra2": "10",   # da_pct
        "extra3": "10",   # tax_pct
        "extra4": "12",   # pf_pct
    })

    # Part-time: rate=200, hours=35 → net=7000
    repo.add_employee({
        "emp_id": "PT001",
        "name": "Bob PT",
        "department": "HR",
        "emp_type": "part_time",
        "base_pay": "0",
        "extra1": "200",  # hourly_rate
        "extra2": "35",   # hours_worked
        "extra3": "0",
        "extra4": "0",
    })

    # Contract: fee=100000 → net=90000
    repo.add_employee({
        "emp_id": "CT001",
        "name": "Carol CT",
        "department": "IT",
        "emp_type": "contract",
        "base_pay": "0",
        "extra1": "100000",  # project_fee
        "extra2": "0",
        "extra3": "0",
        "extra4": "0",
    })

    # Override payslips dir to tmp so we don't pollute the real output/
    payslips_dir = tmp_path / "payslips"
    payslips_dir.mkdir()

    import services.payroll_service as svc_mod
    original_dir = svc_mod._PAYSLIPS_DIR
    svc_mod._PAYSLIPS_DIR = str(payslips_dir)

    try:
        service = PayrollService(repo)
        results = service.run_monthly_payroll()
    finally:
        svc_mod._PAYSLIPS_DIR = original_dir

    assert len(results) == 3

    by_id = {r["emp_id"]: r for r in results}

    assert by_id["FT001"]["net_pay"] == pytest.approx(54_000.0)
    assert by_id["PT001"]["net_pay"] == pytest.approx(7_000.0)
    assert by_id["CT001"]["net_pay"] == pytest.approx(90_000.0)

    # Payslip files should exist
    for r in results:
        assert os.path.isfile(str(payslips_dir / r["payslip_file"]))


def test_analytics_summary(tmp_path):
    """Verify get_analytics computes correct KPIs, departments, and type distributions."""
    repo = _make_repo(tmp_path)
    repo.add_employee({
        "emp_id": "FT100",
        "name": "Dev One",
        "department": "Engineering",
        "emp_type": "full_time",
        "base_pay": "60000",
        "extra1": "20",
        "extra2": "10",
        "extra3": "10",
        "extra4": "12",
    })
    repo.add_employee({
        "emp_id": "PT100",
        "name": "Support One",
        "department": "Support",
        "emp_type": "part_time",
        "base_pay": "0",
        "extra1": "200",
        "extra2": "44",  # 40 reg + 4 ot
        "extra3": "0",
        "extra4": "0",
    })

    service = PayrollService(repo)
    analytics = service.get_analytics()

    assert analytics["kpis"]["total_employees"] == 2
    assert analytics["kpis"]["total_overtime_hours"] == 4.0
    assert analytics["kpis"]["total_overtime_pay"] == 200 * 1.5 * 4
    assert len(analytics["departments"]) == 2
    assert "full_time" in analytics["employment_types"]
    assert "part_time" in analytics["employment_types"]
    assert len(analytics["top_earners"]) == 2
