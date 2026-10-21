"""Deactra: a lightweight actuarial interest rate solver."""

from deactra.models import CashFlow, EquivalentRates, IterationRecord, SolverResult
from deactra.rates import equivalent_rates
from deactra.solver import npv, npv_derivative, solve_rate

__all__ = [
    "CashFlow",
    "EquivalentRates",
    "IterationRecord",
    "SolverResult",
    "equivalent_rates",
    "npv",
    "npv_derivative",
    "solve_rate",
]

__version__ = "0.1.0"
