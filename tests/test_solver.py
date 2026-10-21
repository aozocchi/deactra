import math
import pytest

from deactra.cashflows import InputError, validate_cash_flows
from deactra.models import CashFlow
from deactra.solver import find_brackets, npv, npv_derivative, solve_bracketed_roots, solve_rate


def test_known_rate_from_single_payment():
    expected = 0.10
    flows = [CashFlow(-100.0, 0.0), CashFlow(110.0, 1.0)]
    result = solve_rate(flows)
    assert result.converged
    assert result.rate == pytest.approx(expected, abs=1e-10)
    assert abs(result.npv) < 1e-8


def test_known_rate_from_two_payments():
    flows = [CashFlow(-1000, 0), CashFlow(600, 1), CashFlow(600, 2)]
    result = solve_rate(flows)
    assert result.converged
    assert result.rate == pytest.approx(0.1306623863, abs=1e-9)
    assert abs(npv(result.rate, flows)) < 1e-7


def test_derivative_matches_finite_difference():
    flows = [CashFlow(-1200, 0), CashFlow(700, 1), CashFlow(600, 2.5)]
    rate = 0.07
    h = 1e-6
    numeric = (npv(rate + h, flows) - npv(rate - h, flows)) / (2 * h)
    assert npv_derivative(rate, flows) == pytest.approx(numeric, rel=1e-6)


def test_input_validation():
    with pytest.raises(InputError):
        validate_cash_flows([CashFlow(-100, 0), CashFlow(-10, 1)])
    with pytest.raises(InputError):
        validate_cash_flows([CashFlow(-100, 0), CashFlow(110, -1)])


def test_times_pair_by_position_and_need_not_be_sorted():
    flows = [CashFlow(-100, 1), CashFlow(110, 0)]
    # Valid input, and NPV respects the supplied pairing rather than sorting.
    validate_cash_flows(flows)
    assert npv(0.1, flows) == pytest.approx(110.0 - 100.0 / 1.1)


def test_bracket_scan_finds_known_root():
    flows = [CashFlow(-100, 0), CashFlow(110, 1)]
    roots = solve_bracketed_roots(flows)
    assert roots == pytest.approx([0.1], abs=1e-8)


def test_no_root_returns_explicit_failure():
    # Mathematically invalid for validation because all signs are equal.
    with pytest.raises(InputError):
        solve_rate([CashFlow(-100, 0), CashFlow(-10, 1)])


def test_user_example_converges():
    flows = [CashFlow(-1000, 9), CashFlow(2426, 2), CashFlow(2093, 3), CashFlow(300, 7)]
    result = solve_rate(flows)
    assert result.converged
    assert result.rate is not None and result.rate > -1
    assert abs(npv(result.rate, flows)) < 1e-6


def test_root_scan_reports_multiple_irr_candidates():
    # NPV = -100 + 230/(1+i) - 132/(1+i)^2 has roots 10% and 20%.
    flows = [CashFlow(-100, 0), CashFlow(230, 1), CashFlow(-132, 2)]
    roots = solve_bracketed_roots(flows)
    assert roots == pytest.approx([0.1, 0.2], abs=1e-7)
