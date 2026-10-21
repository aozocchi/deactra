"""Small, immutable data models used by Deactra."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CashFlow:
    """A cash flow amount occurring at ``time`` years."""

    amount: float
    time: float


@dataclass(frozen=True, slots=True)
class IterationRecord:
    """A diagnostic record for one numerical iteration."""

    iteration: int
    rate: float
    npv: float
    derivative: float
    method: str


@dataclass(frozen=True, slots=True)
class SolverResult:
    """Structured solver outcome; a rate is set only on convergence."""

    converged: bool
    rate: float | None
    status: str
    message: str
    iterations: int
    npv: float | None
    records: tuple[IterationRecord, ...] = ()
    roots_found: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class EquivalentRates:
    """Rates equivalent to an effective annual interest rate."""

    effective_annual: float
    discount_factor: float
    effective_discount: float
    force_of_interest: float
    nominal_semiannual: float
    nominal_quarterly: float
    nominal_monthly: float
