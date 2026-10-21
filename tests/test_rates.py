import math
import pytest

from deactra.rates import equivalent_rates


def test_equivalent_rates_identity_at_zero():
    rates = equivalent_rates(0.0)
    assert rates.effective_annual == 0.0
    assert rates.discount_factor == 1.0
    assert rates.effective_discount == 0.0
    assert rates.force_of_interest == 0.0
    assert rates.nominal_semiannual == 0.0
    assert rates.nominal_quarterly == 0.0
    assert rates.nominal_monthly == 0.0


def test_equivalent_rates_are_equivalent():
    i = 0.08
    rates = equivalent_rates(i)
    assert math.isclose((1 + rates.nominal_semiannual / 2) ** 2, 1 + i)
    assert math.isclose((1 + rates.nominal_quarterly / 4) ** 4, 1 + i)
    assert math.isclose((1 + rates.nominal_monthly / 12) ** 12, 1 + i)
    assert math.isclose(rates.discount_factor, 1 / (1 + i))
    assert math.isclose(rates.effective_discount, i / (1 + i))
    assert math.isclose(rates.force_of_interest, math.log1p(i))


@pytest.mark.parametrize("rate", [-1.0, -1.5, math.nan, math.inf])
def test_equivalent_rates_reject_invalid_rate(rate):
    with pytest.raises(ValueError):
        equivalent_rates(rate)
