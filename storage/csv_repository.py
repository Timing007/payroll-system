"""CSV-backed repository for the Payroll Management System."""

from __future__ import annotations

import csv
import os
from typing import Optional


# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

EMPLOYEE_FIELDNAMES: list[str] = [
    "emp_id",
    "name",
    "department",
    "emp_type",
    "base_pay",
    "extra1",
    "extra2",
    "extra3",
    "extra4",
]

LOG_FIELDNAMES: list[str] = [
    "run_id",
    "run_date",
    "emp_id",
    "emp_name",
    "department",
    "emp_type",
    "gross_pay",
    "net_pay",
    "payslip_file",
]


class CSVRepository:
    """Thin CSV persistence layer for employees and payroll run logs.

    Attributes:
        employees_path: Absolute or relative path to ``employees.csv``.
        logs_path: Absolute or relative path to ``payroll_logs.csv``.
    """

    def __init__(self, employees_path: str, logs_path: str) -> None:
        """Initialise the repository, creating files with headers if absent.

        Args:
            employees_path: Path to the employees CSV file.
            logs_path: Path to the payroll-logs CSV file.
        """
        self._employees_path = employees_path
        self._logs_path = logs_path
        self._ensure_file(self._employees_path, EMPLOYEE_FIELDNAMES)
        self._ensure_file(self._logs_path, LOG_FIELDNAMES)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_file(self, path: str, fieldnames: list[str]) -> None:
        """Create *path* (and its parent directories) with a header row if missing.

        Args:
            path: Target CSV file path.
            fieldnames: Column names to write as the header.
        """
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()

    def _atomic_write(self, path: str, rows: list[dict], fieldnames: list[str]) -> None:
        """Write *rows* to *path* atomically via a temporary file.

        The data is first written to ``path + ".tmp"`` and then renamed over
        *path* using :func:`os.replace`, which is atomic on all major platforms.

        Args:
            path: Destination CSV file path.
            rows: List of row dicts to write (after the header).
            fieldnames: Column names that determine the CSV header and ordering.
        """
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_path, path)

    def _read_all(self, path: str) -> list[dict]:
        """Read every row from a CSV file as a list of dicts.

        Args:
            path: Path to the CSV file.

        Returns:
            A list of :class:`dict` objects (one per row).  Returns an empty
            list when the file is missing or contains no data rows.
        """
        if not os.path.exists(path):
            return []
        with open(path, "r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        return rows

    # ------------------------------------------------------------------
    # Employee operations
    # ------------------------------------------------------------------

    def add_employee(self, row: dict) -> None:
        """Persist a new employee record.

        Args:
            row: Dict containing at least ``emp_id`` and the remaining
                employee fields.

        Raises:
            ValueError: If an employee with the same ``emp_id`` already exists.
        """
        rows = self._read_all(self._employees_path)
        emp_id = row.get("emp_id", "")
        if any(r["emp_id"] == emp_id for r in rows):
            raise ValueError(f"Employee with emp_id '{emp_id}' already exists.")
        rows.append(row)
        self._atomic_write(self._employees_path, rows, EMPLOYEE_FIELDNAMES)

    def get_employee(self, emp_id: str) -> Optional[dict]:
        """Retrieve a single employee by ID.

        Args:
            emp_id: The unique employee identifier to look up.

        Returns:
            The matching row dict, or ``None`` if no match is found.
        """
        rows = self._read_all(self._employees_path)
        for row in rows:
            if row["emp_id"] == emp_id:
                return row
        return None

    def get_all_employees(self) -> list[dict]:
        """Return every employee record.

        Returns:
            A list of dicts, one per employee; empty if the file has no data.
        """
        return self._read_all(self._employees_path)

    def update_employee(self, emp_id: str, updates: dict) -> bool:
        """Apply *updates* to the employee identified by *emp_id*.

        Args:
            emp_id: The unique employee identifier.
            updates: Dict of field-name → new-value pairs to merge.

        Returns:
            ``True`` if the employee was found and updated; ``False`` otherwise.
        """
        rows = self._read_all(self._employees_path)
        found = False
        for row in rows:
            if row["emp_id"] == emp_id:
                row.update(updates)
                found = True
                break
        if found:
            self._atomic_write(self._employees_path, rows, EMPLOYEE_FIELDNAMES)
        return found

    def delete_employee(self, emp_id: str) -> bool:
        """Remove the employee identified by *emp_id* from the CSV.

        Args:
            emp_id: The unique employee identifier.

        Returns:
            ``True`` if the employee was found and removed; ``False`` otherwise.
        """
        rows = self._read_all(self._employees_path)
        new_rows = [r for r in rows if r["emp_id"] != emp_id]
        if len(new_rows) == len(rows):
            return False
        self._atomic_write(self._employees_path, new_rows, EMPLOYEE_FIELDNAMES)
        return True

    # ------------------------------------------------------------------
    # Payroll-log operations
    # ------------------------------------------------------------------

    def log_payroll_run(self, entry: dict) -> None:
        """Append a single payroll-run record to the logs CSV atomically.

        Args:
            entry: Dict containing the payroll-run fields (``run_id``,
                ``run_date``, ``emp_id``, ``emp_name``, ``department``,
                ``emp_type``, ``gross_pay``, ``net_pay``, ``payslip_file``).
        """
        rows = self._read_all(self._logs_path)
        rows.append(entry)
        self._atomic_write(self._logs_path, rows, LOG_FIELDNAMES)

    def get_payroll_logs(self, department: Optional[str] = None) -> list[dict]:
        """Retrieve payroll-run log entries, optionally filtered by department.

        Args:
            department: When provided, only logs whose ``department`` column
                matches this value (case-sensitive) are returned.

        Returns:
            A list of log-row dicts, possibly empty.
        """
        rows = self._read_all(self._logs_path)
        if department is not None:
            rows = [r for r in rows if r.get("department") == department]
        return rows
