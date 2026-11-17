"""Payroll service layer for the Payroll Management System.

This module provides the ``PayrollService`` class which orchestrates the
monthly payroll run, payslip generation, log persistence, and reporting.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime

from models.employee import Employee, FullTimeEmployee, PartTimeEmployee, ContractEmployee
from storage.csv_repository import CSVRepository

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Absolute path to the project root (one level above this file's package dir)
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if os.environ.get("VERCEL"):
    _PAYSLIPS_DIR = "/tmp/output/payslips"
else:
    _PAYSLIPS_DIR = os.path.join(_PROJECT_ROOT, "output", "payslips")


# ---------------------------------------------------------------------------
# PayrollService
# ---------------------------------------------------------------------------


class PayrollService:
    """Orchestrates payroll calculation, payslip generation, and reporting.

    Args:
        repository: An initialised :class:`~storage.csv_repository.CSVRepository`
            that provides access to the employees and log CSV files.
    """

    def __init__(self, repository: CSVRepository) -> None:
        self._repo = repository

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _csv_row_to_dict(row: dict) -> dict:
        """Translate a raw CSV employee row into an Employee-ready dict.

        The CSV storage uses generic ``extra1``–``extra4`` columns whose
        meaning depends on ``emp_type``:

        * ``full_time``  — extra1=hra_pct, extra2=da_pct, extra3=tax_pct, extra4=pf_pct
        * ``part_time``  — extra1=hourly_rate, extra2=hours_worked
        * ``contract``   — extra1=project_fee

        Args:
            row: Raw dict as returned by :class:`~storage.csv_repository.CSVRepository`.

        Returns:
            A normalised dict suitable for passing to ``Employee.from_dict()``.
        """
        emp_type = row.get("emp_type", "")
        base: dict = {
            "emp_id": row.get("emp_id", ""),
            "name": row.get("name", ""),
            "department": row.get("department", ""),
            "emp_type": emp_type,
            "base_pay": float(row.get("base_pay", 0) or 0),
        }

        def _f(key: str) -> float:
            val = row.get(key, 0) or 0
            return float(val)

        if emp_type == "full_time":
            base["hra_pct"] = _f("extra1")
            base["da_pct"] = _f("extra2")
            base["tax_pct"] = _f("extra3")
            base["pf_pct"] = _f("extra4")
        elif emp_type == "part_time":
            base["hourly_rate"] = _f("extra1")
            base["hours_worked"] = _f("extra2")
        elif emp_type == "contract":
            base["project_fee"] = _f("extra1")

        return base

    @staticmethod
    def _gross_pay(emp: Employee) -> float:
        """Derive gross pay from an Employee instance.

        * ``FullTimeEmployee``: base_pay × (1 + hra_pct/100 + da_pct/100)
        * ``PartTimeEmployee``: same as net pay (no deductions)
        * ``ContractEmployee``: project_fee (before TDS)

        Args:
            emp: A concrete Employee subclass instance.

        Returns:
            Gross pay as a float.
        """
        if isinstance(emp, FullTimeEmployee):
            return emp.base_pay * (1 + emp.hra_pct / 100 + emp.da_pct / 100)
        if isinstance(emp, ContractEmployee):
            return emp.project_fee
        # PartTimeEmployee — no deductions, gross == net
        return emp.calculate_net_pay()

    @staticmethod
    def _type_label(emp: Employee) -> str:
        """Return a human-readable type label for the payslip header.

        Args:
            emp: Any Employee subclass.

        Returns:
            One of "Full Time", "Part Time", or "Contract".
        """
        mapping = {
            "full_time": "Full Time",
            "part_time": "Part Time",
            "contract": "Contract",
        }
        return mapping.get(emp.emp_type, emp.emp_type.replace("_", " ").title())

    @staticmethod
    def _format_payslip(emp: Employee, run_date: str) -> str:
        """Render a payslip as a formatted string.

        Uses ``payslip_lines()`` from the Employee subclass to obtain the
        itemised body of the slip, then wraps it in the standard header /
        footer.

        Args:
            emp: The Employee instance whose payslip is being generated.
            run_date: ISO date string (YYYY-MM-DD) for the footer.

        Returns:
            The complete payslip text as a single string.
        """
        lines = emp.payslip_lines()
        body = "\n".join(f"  {line}" for line in lines)
        return (
            "========================================\n"
            "           PAYSLIP\n"
            "========================================\n"
            f"Employee ID : {emp.emp_id}\n"
            f"Name        : {emp.name}\n"
            f"Department  : {emp.department}\n"
            f"Type        : {PayrollService._type_label(emp)}\n"
            "\n"
            f"{body}\n"
            "\n"
            "========================================\n"
            f"Run Date: {run_date}\n"
            "========================================\n"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reconstruct(self, row: dict) -> Employee:
        """Factory: maps a CSV row dict to the correct Employee subclass.

        Translates the raw CSV columns (``extra1``–``extra4``) to their
        type-specific field names and delegates to ``Employee.from_dict()``.

        Args:
            row: A raw employee row dict from :class:`CSVRepository`.

        Returns:
            The appropriate :class:`~models.employee.Employee` subclass instance.

        Raises:
            ValueError: If the ``emp_type`` field is unrecognised.
        """
        normalised = self._csv_row_to_dict(row)
        return Employee.from_dict(normalised)

    def run_monthly_payroll(self) -> list[dict]:
        """Execute the monthly payroll run for all employees.

        For each employee the method:

        1. Reconstructs an Employee object from the CSV row.
        2. Calculates net pay (and gross pay).
        3. Writes a payslip ``.txt`` file to ``output/payslips/``.
        4. Appends an entry to ``payroll_logs.csv``.

        Returns:
            A list of result dicts, one per employee, with keys:
            ``emp_id``, ``emp_name``, ``department``, ``emp_type``,
            ``gross_pay``, ``net_pay``, ``payslip_file``.
        """
        run_id = str(uuid.uuid4())
        run_date_full = datetime.now().isoformat()
        run_date_short = run_date_full[:10]  # YYYY-MM-DD for display

        os.makedirs(_PAYSLIPS_DIR, exist_ok=True)

        results: list[dict] = []

        for raw_row in self._repo.get_all_employees():
            emp = self.reconstruct(raw_row)
            net_pay = emp.calculate_net_pay()
            gross_pay = self._gross_pay(emp)

            # ---- payslip file ----
            payslip_filename = f"{run_id}_{emp.emp_id}.txt"
            payslip_path = os.path.join(_PAYSLIPS_DIR, payslip_filename)
            payslip_text = self._format_payslip(emp, run_date_short)
            with open(payslip_path, "w", encoding="utf-8") as fh:
                fh.write(payslip_text)

            # ---- log entry ----
            log_entry = {
                "run_id": run_id,
                "run_date": run_date_full,
                "emp_id": emp.emp_id,
                "emp_name": emp.name,
                "department": emp.department,
                "emp_type": emp.emp_type,
                "gross_pay": gross_pay,
                "net_pay": net_pay,
                "payslip_file": payslip_filename,
            }
            self._repo.log_payroll_run(log_entry)

            results.append({
                "emp_id": emp.emp_id,
                "emp_name": emp.name,
                "department": emp.department,
                "emp_type": emp.emp_type,
                "gross_pay": gross_pay,
                "net_pay": net_pay,
                "payslip_file": payslip_filename,
            })

        return results

    def get_payslip_path(self, filename: str) -> str:
        """Return the absolute path for a payslip file.

        Args:
            filename: The bare filename (e.g. ``"<run_id>_EMP001.txt"``).

        Returns:
            Absolute path to ``output/payslips/<filename>``.
        """
        return os.path.join(_PAYSLIPS_DIR, filename)

    def department_summary(self) -> dict[str, float]:
        """Aggregate net pay by department from the most recent payroll run.

        Reads all payroll log entries, identifies the most recent ``run_id``
        (last row's run_id), then sums ``net_pay`` per department for that
        run only.

        Returns:
            A dict mapping department name → total net pay (float).
            Returns an empty dict if no logs exist.
        """
        logs = self._repo.get_payroll_logs()
        if not logs:
            return {}

        # Determine the most recent run_id (preserve insertion order: last run_id seen)
        latest_run_id = logs[-1]["run_id"]

        summary: dict[str, float] = {}
        for entry in logs:
            if entry["run_id"] != latest_run_id:
                continue
            dept = entry.get("department", "")
            try:
                net = float(entry.get("net_pay", 0) or 0)
            except (ValueError, TypeError):
                net = 0.0
            summary[dept] = summary.get(dept, 0.0) + net

        return summary

    def get_analytics(self) -> dict:
        """Compute comprehensive analytics and statistics across all employees.

        Analyzes all current employees in the repository, calculating their
        projected/current gross pay, net pay, allowances, deductions, taxes,
        and overtime metrics, aggregated across departments and employment types.

        Returns:
            A structured dict with:
            - 'kpis': summary metrics
            - 'departments': list of dicts with dept metrics and percentages
            - 'employment_types': dict of metrics per employment type
            - 'salary_bands': histogram distribution of net pay
            - 'top_earners': top 10 earners
            - 'statutory_breakdown': tax, PF, TDS, and allowances
        """
        raw_rows = self._repo.get_all_employees()
        total_count = len(raw_rows)
        if total_count == 0:
            return {
                "kpis": {
                    "total_employees": 0,
                    "total_gross": 0.0,
                    "total_net": 0.0,
                    "total_deductions": 0.0,
                    "avg_net": 0.0,
                    "median_net": 0.0,
                    "max_net": 0.0,
                    "min_net": 0.0,
                    "total_tax": 0.0,
                    "total_pf": 0.0,
                    "total_tds": 0.0,
                    "total_allowances": 0.0,
                    "total_overtime_pay": 0.0,
                    "total_overtime_hours": 0.0,
                },
                "departments": [],
                "employment_types": {},
                "salary_bands": {},
                "top_earners": [],
                "statutory_breakdown": {},
            }

        analyzed: list[dict] = []
        total_gross = 0.0
        total_net = 0.0
        total_deductions = 0.0
        total_tax = 0.0
        total_pf = 0.0
        total_tds = 0.0
        total_allowances = 0.0
        total_overtime_pay = 0.0
        total_overtime_hours = 0.0

        # Department aggregators
        dept_data: dict[str, dict] = {}

        # Type aggregators
        type_data: dict[str, dict] = {
            "full_time": {
                "label": "Full Time",
                "count": 0,
                "total_gross": 0.0,
                "total_net": 0.0,
                "total_tax": 0.0,
                "total_pf": 0.0,
                "total_allowances": 0.0,
            },
            "part_time": {
                "label": "Part Time",
                "count": 0,
                "total_gross": 0.0,
                "total_net": 0.0,
                "total_hours": 0.0,
                "regular_hours": 0.0,
                "overtime_hours": 0.0,
                "overtime_pay": 0.0,
            },
            "contract": {
                "label": "Contract",
                "count": 0,
                "total_gross": 0.0,
                "total_net": 0.0,
                "total_tds": 0.0,
            },
        }

        # Salary bands
        salary_bands = {
            "< ₹30,000": 0,
            "₹30k - ₹60k": 0,
            "₹60k - ₹100k": 0,
            "₹100k - ₹150k": 0,
            "> ₹150,000": 0,
        }

        for row in raw_rows:
            emp = self.reconstruct(row)
            net = emp.calculate_net_pay()
            gross = self._gross_pay(emp)
            deduction = gross - net

            total_gross += gross
            total_net += net
            total_deductions += deduction

            # Department init
            d_name = emp.department
            if d_name not in dept_data:
                dept_data[d_name] = {
                    "department": d_name,
                    "count": 0,
                    "total_gross": 0.0,
                    "total_net": 0.0,
                    "total_deductions": 0.0,
                    "full_time_count": 0,
                    "part_time_count": 0,
                    "contract_count": 0,
                }
            d = dept_data[d_name]
            d["count"] += 1
            d["total_gross"] += gross
            d["total_net"] += net
            d["total_deductions"] += deduction

            # Subclass specifics
            if isinstance(emp, FullTimeEmployee):
                d["full_time_count"] += 1
                tax = (emp.tax_pct / 100) * emp.base_pay
                pf = (emp.pf_pct / 100) * emp.base_pay
                hra = (emp.hra_pct / 100) * emp.base_pay
                da = (emp.da_pct / 100) * emp.base_pay
                allowances = hra + da

                total_tax += tax
                total_pf += pf
                total_allowances += allowances

                td = type_data["full_time"]
                td["count"] += 1
                td["total_gross"] += gross
                td["total_net"] += net
                td["total_tax"] += tax
                td["total_pf"] += pf
                td["total_allowances"] += allowances

            elif isinstance(emp, PartTimeEmployee):
                d["part_time_count"] += 1
                reg_hrs = min(emp.hours_worked, 40.0)
                ot_hrs = max(emp.hours_worked - 40.0, 0.0)
                ot_pay = emp.hourly_rate * 1.5 * ot_hrs

                total_overtime_hours += ot_hrs
                total_overtime_pay += ot_pay

                td = type_data["part_time"]
                td["count"] += 1
                td["total_gross"] += gross
                td["total_net"] += net
                td["total_hours"] += emp.hours_worked
                td["regular_hours"] += reg_hrs
                td["overtime_hours"] += ot_hrs
                td["overtime_pay"] += ot_pay

            elif isinstance(emp, ContractEmployee):
                d["contract_count"] += 1
                tds = emp.project_fee * 0.10
                total_tds += tds

                td = type_data["contract"]
                td["count"] += 1
                td["total_gross"] += gross
                td["total_net"] += net
                td["total_tds"] += tds

            # Bins
            if net < 30000:
                salary_bands["< ₹30,000"] += 1
            elif net <= 60000:
                salary_bands["₹30k - ₹60k"] += 1
            elif net <= 100000:
                salary_bands["₹60k - ₹100k"] += 1
            elif net <= 150000:
                salary_bands["₹100k - ₹150k"] += 1
            else:
                salary_bands["> ₹150,000"] += 1

            analyzed.append({
                "emp_id": emp.emp_id,
                "name": emp.name,
                "department": emp.department,
                "emp_type": emp.emp_type,
                "gross_pay": gross,
                "net_pay": net,
                "deductions": deduction,
            })

        # Calculate averages and percentages for departments
        department_list = []
        for d in dept_data.values():
            c = d["count"]
            d["avg_net"] = d["total_net"] / c if c > 0 else 0.0
            d["avg_gross"] = d["total_gross"] / c if c > 0 else 0.0
            d["headcount_pct"] = (c / total_count) * 100
            d["net_payroll_pct"] = (d["total_net"] / total_net * 100) if total_net > 0 else 0.0
            department_list.append(d)

        department_list.sort(key=lambda x: x["total_net"], reverse=True)

        # Calculate averages for types
        for t_key, t_info in type_data.items():
            cnt = t_info["count"]
            t_info["avg_net"] = (t_info["total_net"] / cnt) if cnt > 0 else 0.0
            t_info["pct_of_total"] = (cnt / total_count * 100) if total_count > 0 else 0.0

        # Sort top 10 earners
        analyzed.sort(key=lambda x: x["net_pay"], reverse=True)
        top_earners = analyzed[:10]

        all_nets = sorted(x["net_pay"] for x in analyzed)
        median_net = all_nets[total_count // 2] if total_count > 0 else 0.0

        return {
            "kpis": {
                "total_employees": total_count,
                "total_gross": total_gross,
                "total_net": total_net,
                "total_deductions": total_deductions,
                "avg_net": total_net / total_count,
                "median_net": median_net,
                "max_net": all_nets[-1] if all_nets else 0.0,
                "min_net": all_nets[0] if all_nets else 0.0,
                "total_tax": total_tax,
                "total_pf": total_pf,
                "total_tds": total_tds,
                "total_allowances": total_allowances,
                "total_overtime_pay": total_overtime_pay,
                "total_overtime_hours": total_overtime_hours,
            },
            "departments": department_list,
            "employment_types": type_data,
            "salary_bands": salary_bands,
            "top_earners": top_earners,
            "statutory_breakdown": {
                "Income Tax": total_tax,
                "Provident Fund (PF)": total_pf,
                "TDS (Contractors)": total_tds,
                "Total Statutory Deductions": total_tax + total_pf + total_tds,
                "Total Allowances (HRA + DA)": total_allowances,
            },
        }
