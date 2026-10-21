"""Cash-flow input validation and diagnostics."""

from __future__ import annotations

import math
from collections.abc import Sequence

from deactra.models import CashFlow


class InputError(ValueError):
    """Raised when cash-flow data cannot be used by the solver."""


def validate_cash_flows(cash_flows: Sequence[CashFlow]) -> None:
    """Validate the input required for a conventional real-rate search.

    Times are measured in years and must be non-negative. Time values are
    paired with cash flows by position; they are never silently re-ordered.
    """
    if not cash_flows:
        raise InputError("At least one cash flow is required.")

    for index, cash_flow in enumerate(cash_flows, start=1):
        if not math.isfinite(cash_flow.amount):
            raise InputError(f"Cash flow #{index} amount must be finite.")
        if not math.isfinite(cash_flow.time):
            raise InputError(f"Cash flow #{index} time must be finite.")
        if cash_flow.time < 0:
            raise InputError(
                f"Cash flow #{index} has negative time {cash_flow.time}. "
                "Times must be non-negative and expressed in years."
            )

    if not any(cf.amount > 0 for cf in cash_flows):
        raise InputError("Cash flows must include at least one positive amount.")
    if not any(cf.amount < 0 for cf in cash_flows):
        raise InputError("Cash flows must include at least one negative amount.")
    if not any(cf.amount != 0 and cf.time > 0 for cf in cash_flows):
        raise InputError("At least one non-zero cash flow must occur after time zero.")


def cash_flow_diagnostic(cash_flows: Sequence[CashFlow]) -> dict[str, int | str]:
    """Return a basic sign-change diagnostic in chronological order.

    Sign changes can indicate multiple IRRs, but this diagnostic cannot prove
    how many real roots exist.
    """
    amounts = [cf.amount for cf in sorted(cash_flows, key=lambda cf: cf.time) if cf.amount != 0]
    sign_changes = sum(
        1 for left, right in zip(amounts, amounts[1:]) if (left < 0 < right or right < 0 < left)
    )
    if sign_changes <= 0:
        note = "No sign change in chronological cash flows; a conventional IRR may not exist."
    elif sign_changes == 1:
        note = "One sign change; the cash-flow pattern is conventional, though uniqueness is not guaranteed by this check alone."
    else:
        note = "Multiple sign changes; multiple IRRs or no admissible IRR may occur."
    return {"sign_changes": sign_changes, "diagnostic": note}
