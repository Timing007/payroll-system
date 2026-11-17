"""Employee models for the Payroll Management System.

This module defines the abstract base class ``Employee`` and its three concrete
subclasses: ``FullTimeEmployee``, ``PartTimeEmployee``, and ``ContractEmployee``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Union


# ---------------------------------------------------------------------------
# Abstract Base Class
# ---------------------------------------------------------------------------


class Employee(ABC):
    """Abstract base class representing a generic employee.

    Args:
        emp_id: Unique employee identifier.
        name: Full name of the employee.
        department: Department the employee belongs to.
        base_pay: Base pay amount (monthly salary, 0.0 for part-time, etc.).
        emp_type: Discriminator string used by ``from_dict`` to restore the
            correct subclass.

    Raises:
        ValueError: If any argument fails validation.
    """

    def __init__(
        self,
        emp_id: str,
        name: str,
        department: str,
        base_pay: float,
        emp_type: str,
    ) -> None:
        self.emp_id = emp_id
        self.name = name
        self.department = department
        self.base_pay = base_pay
        self._emp_type = emp_type  # set directly; subclasses supply the literal

    # ------------------------------------------------------------------
    # Properties — emp_id
    # ------------------------------------------------------------------

    @property
    def emp_id(self) -> str:
        """str: Unique employee identifier."""
        return self._emp_id

    @emp_id.setter
    def emp_id(self, value: str) -> None:
        """Set the employee ID.

        Args:
            value: Non-empty string identifier.

        Raises:
            ValueError: If ``value`` is not a str or is empty.
        """
        if not isinstance(value, str) or not value:
            raise ValueError("emp_id must be a non-empty string.")
        self._emp_id = value

    # ------------------------------------------------------------------
    # Properties — name
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """str: Full name of the employee."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Set the employee name.

        Args:
            value: Non-empty string name.

        Raises:
            ValueError: If ``value`` is not a str or is empty.
        """
        if not isinstance(value, str) or not value:
            raise ValueError("name must be a non-empty string.")
        self._name = value

    # ------------------------------------------------------------------
    # Properties — department
    # ------------------------------------------------------------------

    @property
    def department(self) -> str:
        """str: Department the employee belongs to."""
        return self._department

    @department.setter
    def department(self, value: str) -> None:
        """Set the department.

        Args:
            value: Non-empty string department name.

        Raises:
            ValueError: If ``value`` is not a str or is empty.
        """
        if not isinstance(value, str) or not value:
            raise ValueError("department must be a non-empty string.")
        self._department = value

    # ------------------------------------------------------------------
    # Properties — base_pay
    # ------------------------------------------------------------------

    @property
    def base_pay(self) -> float:
        """float: Base pay amount."""
        return self._base_pay

    @base_pay.setter
    def base_pay(self, value: Union[int, float]) -> None:
        """Set the base pay.

        Args:
            value: Numeric value that is ≥ 0.

        Raises:
            ValueError: If ``value`` is not a number or is negative.
        """
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("base_pay must be a numeric value.")
        if value < 0:
            raise ValueError("base_pay must be >= 0.")
        self._base_pay = float(value)

    # ------------------------------------------------------------------
    # Properties — emp_type
    # ------------------------------------------------------------------

    @property
    def emp_type(self) -> str:
        """str: Employee type discriminator."""
        return self._emp_type

    @emp_type.setter
    def emp_type(self, value: str) -> None:
        """Set the employee type.

        Args:
            value: Non-empty string type identifier.

        Raises:
            ValueError: If ``value`` is not a str or is empty.
        """
        if not isinstance(value, str) or not value:
            raise ValueError("emp_type must be a non-empty string.")
        self._emp_type = value

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def calculate_net_pay(self) -> float:
        """Calculate and return the net pay for this employee.

        Returns:
            Net pay as a float.
        """

    @abstractmethod
    def payslip_lines(self) -> list[str]:
        """Return itemized lines for the employee's payslip.

        Returns:
            A list of strings, each representing one payslip line item.
        """

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the employee to a plain dictionary.

        Subclasses override this method to add their own fields and should
        call ``super().to_dict()`` to obtain the base dictionary.

        Returns:
            A dict with keys ``emp_id``, ``name``, ``department``,
            ``base_pay``, and ``emp_type``.
        """
        return {
            "emp_id": self._emp_id,
            "name": self._name,
            "department": self._department,
            "base_pay": self._base_pay,
            "emp_type": self._emp_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Employee:
        """Instantiate the correct ``Employee`` subclass from a dictionary.

        The ``emp_type`` key in ``d`` is used to dispatch to the right
        subclass constructor.

        Args:
            d: Dictionary previously produced by ``to_dict()``.

        Returns:
            An instance of the appropriate ``Employee`` subclass.

        Raises:
            ValueError: If ``d["emp_type"]`` is not a recognised type.
        """
        dispatch: dict[str, type[Employee]] = {
            "full_time": FullTimeEmployee,
            "part_time": PartTimeEmployee,
            "contract": ContractEmployee,
        }
        emp_type = d.get("emp_type", "")
        klass = dispatch.get(emp_type)
        if klass is None:
            raise ValueError(
                f"Unknown emp_type '{emp_type}'. "
                f"Expected one of: {list(dispatch.keys())}."
            )
        return klass._from_dict(d)

    @classmethod
    def _from_dict(cls, d: dict) -> Employee:
        """Internal factory used by subclasses; override in each subclass.

        Args:
            d: Raw dictionary from ``to_dict()``.

        Returns:
            A new instance of *cls*.
        """
        raise NotImplementedError(f"{cls.__name__} must implement _from_dict.")


# ---------------------------------------------------------------------------
# FullTimeEmployee
# ---------------------------------------------------------------------------


class FullTimeEmployee(Employee):
    """An employee on a full-time monthly salary.

    Net pay formula::

        gross      = base_pay * (1 + hra_pct/100 + da_pct/100)
        deductions = base_pay * (tax_pct/100 + pf_pct/100)
        net        = gross - deductions

    Args:
        emp_id: Unique employee identifier.
        name: Full name of the employee.
        department: Department name.
        base_pay: Monthly gross salary (≥ 0).
        hra_pct: House Rent Allowance as a percentage of base pay (0–100).
        da_pct: Dearness Allowance as a percentage of base pay (0–100).
        tax_pct: Income-tax deduction as a percentage of base pay (0–100).
        pf_pct: Provident Fund deduction as a percentage of base pay (0–100).

    Raises:
        ValueError: If any argument fails validation.
    """

    def __init__(
        self,
        emp_id: str,
        name: str,
        department: str,
        base_pay: float,
        hra_pct: float = 0.0,
        da_pct: float = 0.0,
        tax_pct: float = 0.0,
        pf_pct: float = 0.0,
    ) -> None:
        super().__init__(emp_id, name, department, base_pay, "full_time")
        self.hra_pct = hra_pct
        self.da_pct = da_pct
        self.tax_pct = tax_pct
        self.pf_pct = pf_pct

    # ------------------------------------------------------------------
    # Percentage helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_pct(name: str, value: float) -> float:
        """Validate that *value* is a float in [0, 100].

        Args:
            name: Attribute name, used in the error message.
            value: Candidate value.

        Returns:
            The validated value cast to float.

        Raises:
            ValueError: If the value is not numeric or outside [0, 100].
        """
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{name} must be a numeric value.")
        if not (0 <= value <= 100):
            raise ValueError(f"{name} must be between 0 and 100 (got {value}).")
        return float(value)

    # ------------------------------------------------------------------
    # Properties — hra_pct
    # ------------------------------------------------------------------

    @property
    def hra_pct(self) -> float:
        """float: House Rent Allowance percentage."""
        return self.__hra_pct

    @hra_pct.setter
    def hra_pct(self, value: float) -> None:
        self.__hra_pct = self._validate_pct("hra_pct", value)

    # ------------------------------------------------------------------
    # Properties — da_pct
    # ------------------------------------------------------------------

    @property
    def da_pct(self) -> float:
        """float: Dearness Allowance percentage."""
        return self.__da_pct

    @da_pct.setter
    def da_pct(self, value: float) -> None:
        self.__da_pct = self._validate_pct("da_pct", value)

    # ------------------------------------------------------------------
    # Properties — tax_pct
    # ------------------------------------------------------------------

    @property
    def tax_pct(self) -> float:
        """float: Income-tax deduction percentage."""
        return self.__tax_pct

    @tax_pct.setter
    def tax_pct(self, value: float) -> None:
        self.__tax_pct = self._validate_pct("tax_pct", value)

    # ------------------------------------------------------------------
    # Properties — pf_pct
    # ------------------------------------------------------------------

    @property
    def pf_pct(self) -> float:
        """float: Provident Fund deduction percentage."""
        return self.__pf_pct

    @pf_pct.setter
    def pf_pct(self, value: float) -> None:
        self.__pf_pct = self._validate_pct("pf_pct", value)

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------

    def calculate_net_pay(self) -> float:
        """Calculate net monthly pay for the full-time employee.

        Returns:
            Net pay (gross minus deductions) as a float.
        """
        gross = self._base_pay * (1 + self.__hra_pct / 100 + self.__da_pct / 100)
        deductions = self._base_pay * (self.__tax_pct / 100 + self.__pf_pct / 100)
        return gross - deductions

    def payslip_lines(self) -> list[str]:
        """Return itemized payslip lines for the full-time employee.

        Returns:
            A list of human-readable strings describing each pay component.
        """
        gross = self._base_pay * (1 + self.__hra_pct / 100 + self.__da_pct / 100)
        hra_amt = (self.__hra_pct / 100) * self._base_pay
        da_amt = (self.__da_pct / 100) * self._base_pay
        tax_amt = (self.__tax_pct / 100) * self._base_pay
        pf_amt = (self.__pf_pct / 100) * self._base_pay
        net = gross - tax_amt - pf_amt
        return [
            f"Employee : {self._name} ({self._emp_id})",
            f"Department: {self._department}",
            f"Type      : Full-Time",
            "─" * 40,
            f"Basic Pay : {self._base_pay:>10.2f}",
            f"HRA ({self.__hra_pct:.1f}%): {hra_amt:>10.2f}",
            f"DA  ({self.__da_pct:.1f}%): {da_amt:>10.2f}",
            f"Gross Pay : {gross:>10.2f}",
            "─" * 40,
            f"Tax ({self.__tax_pct:.1f}%): -{tax_amt:>9.2f}",
            f"PF  ({self.__pf_pct:.1f}%): -{pf_amt:>9.2f}",
            "─" * 40,
            f"Net Pay   : {net:>10.2f}",
        ]

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a dict, including percentage fields.

        Returns:
            Base dict plus ``hra_pct``, ``da_pct``, ``tax_pct``, ``pf_pct``.
        """
        base = super().to_dict()
        base.update(
            {
                "hra_pct": self.__hra_pct,
                "da_pct": self.__da_pct,
                "tax_pct": self.__tax_pct,
                "pf_pct": self.__pf_pct,
            }
        )
        return base

    @classmethod
    def _from_dict(cls, d: dict) -> FullTimeEmployee:
        """Reconstruct a ``FullTimeEmployee`` from a dict.

        Args:
            d: Dictionary produced by ``to_dict()``.

        Returns:
            A new ``FullTimeEmployee`` instance.
        """
        return cls(
            emp_id=d["emp_id"],
            name=d["name"],
            department=d["department"],
            base_pay=d["base_pay"],
            hra_pct=d.get("hra_pct", 0.0),
            da_pct=d.get("da_pct", 0.0),
            tax_pct=d.get("tax_pct", 0.0),
            pf_pct=d.get("pf_pct", 0.0),
        )


# ---------------------------------------------------------------------------
# PartTimeEmployee
# ---------------------------------------------------------------------------


class PartTimeEmployee(Employee):
    """An employee paid by the hour, with overtime for hours beyond 40.

    Net pay formula::

        if hours_worked <= 40:
            pay = hourly_rate * hours_worked
        else:
            pay = hourly_rate * 40 + hourly_rate * 1.5 * (hours_worked - 40)

    Args:
        emp_id: Unique employee identifier.
        name: Full name of the employee.
        department: Department name.
        hourly_rate: Pay per hour (≥ 0).
        hours_worked: Total hours worked in the pay period (≥ 0).
        base_pay: Unused for pay calculation; defaults to 0.0.

    Raises:
        ValueError: If any argument fails validation.
    """

    def __init__(
        self,
        emp_id: str,
        name: str,
        department: str,
        hourly_rate: float,
        hours_worked: float,
        base_pay: float = 0.0,
    ) -> None:
        super().__init__(emp_id, name, department, base_pay, "part_time")
        self.hourly_rate = hourly_rate
        self.hours_worked = hours_worked

    # ------------------------------------------------------------------
    # Properties — hourly_rate
    # ------------------------------------------------------------------

    @property
    def hourly_rate(self) -> float:
        """float: Pay per hour."""
        return self.__hourly_rate

    @hourly_rate.setter
    def hourly_rate(self, value: float) -> None:
        """Set the hourly rate.

        Args:
            value: Non-negative numeric value.

        Raises:
            ValueError: If ``value`` is not numeric or is negative.
        """
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("hourly_rate must be a numeric value.")
        if value < 0:
            raise ValueError("hourly_rate must be >= 0.")
        self.__hourly_rate = float(value)

    # ------------------------------------------------------------------
    # Properties — hours_worked
    # ------------------------------------------------------------------

    @property
    def hours_worked(self) -> float:
        """float: Total hours worked in the pay period."""
        return self.__hours_worked

    @hours_worked.setter
    def hours_worked(self, value: float) -> None:
        """Set the hours worked.

        Args:
            value: Non-negative numeric value.

        Raises:
            ValueError: If ``value`` is not numeric or is negative.
        """
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("hours_worked must be a numeric value.")
        if value < 0:
            raise ValueError("hours_worked must be >= 0.")
        self.__hours_worked = float(value)

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------

    def calculate_net_pay(self) -> float:
        """Calculate net pay for the part-time employee.

        Overtime (hours beyond 40) is paid at 1.5× the regular hourly rate.

        Returns:
            Total pay as a float.
        """
        if self.__hours_worked <= 40:
            return self.__hourly_rate * self.__hours_worked
        return (
            self.__hourly_rate * 40
            + self.__hourly_rate * 1.5 * (self.__hours_worked - 40)
        )

    def payslip_lines(self) -> list[str]:
        """Return itemized payslip lines for the part-time employee.

        Returns:
            A list of human-readable strings describing each pay component.
        """
        regular_hours = min(self.__hours_worked, 40.0)
        overtime_hours = max(self.__hours_worked - 40.0, 0.0)
        regular_pay = self.__hourly_rate * regular_hours
        overtime_pay = self.__hourly_rate * 1.5 * overtime_hours
        net = regular_pay + overtime_pay
        lines = [
            f"Employee  : {self._name} ({self._emp_id})",
            f"Department: {self._department}",
            f"Type      : Part-Time",
            "─" * 40,
            f"Hourly Rate   : {self.__hourly_rate:>8.2f}",
            f"Regular Hours : {regular_hours:>8.2f}",
            f"Regular Pay   : {regular_pay:>8.2f}",
        ]
        if overtime_hours > 0:
            lines += [
                f"Overtime Hours: {overtime_hours:>8.2f}",
                f"Overtime Pay  : {overtime_pay:>8.2f}",
            ]
        lines += [
            "─" * 40,
            f"Net Pay       : {net:>8.2f}",
        ]
        return lines

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a dict, including hourly rate and hours worked.

        Returns:
            Base dict plus ``hourly_rate`` and ``hours_worked``.
        """
        base = super().to_dict()
        base.update(
            {
                "hourly_rate": self.__hourly_rate,
                "hours_worked": self.__hours_worked,
            }
        )
        return base

    @classmethod
    def _from_dict(cls, d: dict) -> PartTimeEmployee:
        """Reconstruct a ``PartTimeEmployee`` from a dict.

        Args:
            d: Dictionary produced by ``to_dict()``.

        Returns:
            A new ``PartTimeEmployee`` instance.
        """
        return cls(
            emp_id=d["emp_id"],
            name=d["name"],
            department=d["department"],
            hourly_rate=d["hourly_rate"],
            hours_worked=d["hours_worked"],
            base_pay=d.get("base_pay", 0.0),
        )


# ---------------------------------------------------------------------------
# ContractEmployee
# ---------------------------------------------------------------------------


class ContractEmployee(Employee):
    """An employee paid a fixed project fee with 10% TDS deducted.

    Net pay formula::

        net = project_fee * 0.90

    Args:
        emp_id: Unique employee identifier.
        name: Full name of the employee.
        department: Department name.
        project_fee: Agreed project fee (≥ 0).
        base_pay: Unused for pay calculation; defaults to 0.0.

    Raises:
        ValueError: If any argument fails validation.
    """

    def __init__(
        self,
        emp_id: str,
        name: str,
        department: str,
        project_fee: float,
        base_pay: float = 0.0,
    ) -> None:
        super().__init__(emp_id, name, department, base_pay, "contract")
        self.project_fee = project_fee

    # ------------------------------------------------------------------
    # Properties — project_fee
    # ------------------------------------------------------------------

    @property
    def project_fee(self) -> float:
        """float: Agreed project fee before TDS deduction."""
        return self.__project_fee

    @project_fee.setter
    def project_fee(self, value: float) -> None:
        """Set the project fee.

        Args:
            value: Non-negative numeric value.

        Raises:
            ValueError: If ``value`` is not numeric or is negative.
        """
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("project_fee must be a numeric value.")
        if value < 0:
            raise ValueError("project_fee must be >= 0.")
        self.__project_fee = float(value)

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------

    def calculate_net_pay(self) -> float:
        """Calculate net pay after 10% TDS deduction.

        Returns:
            Net pay (90% of project fee) as a float.
        """
        return self.__project_fee * 0.90

    def payslip_lines(self) -> list[str]:
        """Return itemized payslip lines for the contract employee.

        Returns:
            A list of human-readable strings describing each pay component.
        """
        tds = self.__project_fee * 0.10
        net = self.__project_fee * 0.90
        return [
            f"Employee   : {self._name} ({self._emp_id})",
            f"Department : {self._department}",
            f"Type       : Contract",
            "─" * 40,
            f"Project Fee: {self.__project_fee:>10.2f}",
            f"TDS (10%)  : -{tds:>9.2f}",
            "─" * 40,
            f"Net Pay    : {net:>10.2f}",
        ]

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a dict, including the project fee.

        Returns:
            Base dict plus ``project_fee``.
        """
        base = super().to_dict()
        base["project_fee"] = self.__project_fee
        return base

    @classmethod
    def _from_dict(cls, d: dict) -> ContractEmployee:
        """Reconstruct a ``ContractEmployee`` from a dict.

        Args:
            d: Dictionary produced by ``to_dict()``.

        Returns:
            A new ``ContractEmployee`` instance.
        """
        return cls(
            emp_id=d["emp_id"],
            name=d["name"],
            department=d["department"],
            project_fee=d["project_fee"],
            base_pay=d.get("base_pay", 0.0),
        )
