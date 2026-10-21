"""Actuarial interest-rate conversions."""

from __future__ import annotations
import math

from deactra.models import EquivalentRates


def equivalent_rates(effective_annual: float) -> EquivalentRates:
    """Convert effective annual interest i into common equivalent rates.

    ``i`` must be greater than -1. Nominal rates are annual rates convertible
    m times per year, for m = 2, 4, and 12.
    """
    i = effective_annual
    if not math.isfinite(i) or i <= -1.0:
        raise ValueError("Effective annual rate must be finite and greater than -1.")

    base = 1.0 + i
    return EquivalentRates(
        effective_annual=i,
        discount_factor=1.0 / base,
        effective_discount=i / base,
        force_of_interest=math.log1p(i),
        nominal_semiannual=2.0 * math.expm1(math.log1p(i) / 2.0),
        nominal_quarterly=4.0 * math.expm1(math.log1p(i) / 4.0),
        nominal_monthly=12.0 * math.expm1(math.log1p(i) / 12.0),
    )
