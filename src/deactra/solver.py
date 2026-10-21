"""NPV functions and a safeguarded Newton-Raphson IRR solver."""

from __future__ import annotations

import math
from collections.abc import Sequence

from deactra.cashflows import InputError, validate_cash_flows
from deactra.models import CashFlow, IterationRecord, SolverResult


def npv(rate: float, cash_flows: Sequence[CashFlow]) -> float:
    """Present value sum(CF * (1 + rate) ** -time), for rate > -1."""
    if not math.isfinite(rate) or rate <= -1.0:
        raise ValueError("Rate must be finite and greater than -1.")

    log_base = math.log1p(rate)
    terms: list[float] = []
    for cf in cash_flows:
        try:
            terms.append(cf.amount * math.exp(-cf.time * log_base))
        except OverflowError:
            return math.copysign(math.inf, cf.amount)
    try:
        return math.fsum(terms)
    except OverflowError:
        return math.copysign(math.inf, terms[0] if terms else 1.0)


def npv_derivative(rate: float, cash_flows: Sequence[CashFlow]) -> float:
    """Derivative of NPV with respect to the annual effective rate."""
    if not math.isfinite(rate) or rate <= -1.0:
        raise ValueError("Rate must be finite and greater than -1.")

    log_base = math.log1p(rate)
    terms: list[float] = []
    for cf in cash_flows:
        if cf.time == 0.0 or cf.amount == 0.0:
            continue
        try:
            terms.append(-cf.time * cf.amount * math.exp((-cf.time - 1.0) * log_base))
        except OverflowError:
            return math.copysign(math.inf, -cf.amount)
    try:
        return math.fsum(terms)
    except OverflowError:
        return math.copysign(math.inf, terms[0] if terms else 0.0)


def _opposite_signs(a: float, b: float) -> bool:
    return (a < 0.0 < b) or (b < 0.0 < a)


def find_brackets(
    cash_flows: Sequence[CashFlow],
    *,
    min_rate: float = -0.999999,
    max_rate: float = 100.0,
    samples: int = 1600,
) -> list[tuple[float, float]]:
    """Scan for NPV sign-changing intervals on a log(1 + rate) grid.

    This is a numerical diagnostic, not a proof that every root has been
    found. Roots that touch zero without changing sign may be missed.
    """
    if not (-1.0 < min_rate < max_rate):
        raise ValueError("Require -1 < min_rate < max_rate.")
    if samples < 2:
        raise ValueError("samples must be at least 2.")

    low_x = math.log1p(min_rate)
    high_x = math.log1p(max_rate)
    brackets: list[tuple[float, float]] = []
    prev_rate = min_rate
    prev_value = npv(prev_rate, cash_flows)

    for index in range(1, samples + 1):
        x = low_x + (high_x - low_x) * index / samples
        rate = math.expm1(x)
        value = npv(rate, cash_flows)
        if math.isfinite(prev_value) and math.isfinite(value):
            if prev_value == 0.0:
                brackets.append((prev_rate, prev_rate))
            elif value == 0.0:
                brackets.append((rate, rate))
            elif _opposite_signs(prev_value, value):
                brackets.append((prev_rate, rate))
        prev_rate, prev_value = rate, value

    # Remove exact/adjacent duplicates caused by a root landing on a sample.
    unique: list[tuple[float, float]] = []
    for bracket in brackets:
        if not unique or abs(bracket[0] - unique[-1][1]) > 1e-14:
            unique.append(bracket)
        else:
            unique[-1] = (unique[-1][0], bracket[1])
    return unique


def _bisect(
    cash_flows: Sequence[CashFlow],
    low: float,
    high: float,
    *,
    max_iterations: int,
    rate_tolerance: float,
    npv_tolerance: float,
) -> tuple[float | None, int, tuple[IterationRecord, ...]]:
    records: list[IterationRecord] = []
    f_low = npv(low, cash_flows)
    f_high = npv(high, cash_flows)

    if f_low == 0.0:
        return low, 0, ()
    if f_high == 0.0:
        return high, 0, ()
    if not (math.isfinite(f_low) and math.isfinite(f_high) and _opposite_signs(f_low, f_high)):
        return None, 0, ()

    for iteration in range(1, max_iterations + 1):
        mid = low + (high - low) / 2.0
        f_mid = npv(mid, cash_flows)
        derivative = npv_derivative(mid, cash_flows)
        records.append(IterationRecord(iteration, mid, f_mid, derivative, "bisection"))

        if abs(f_mid) <= npv_tolerance or abs(high - low) <= rate_tolerance * max(1.0, abs(mid)):
            return mid, iteration, tuple(records)
        if not math.isfinite(f_mid):
            return None, iteration, tuple(records)
        if _opposite_signs(f_low, f_mid):
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return None, max_iterations, tuple(records)


def solve_bracketed_roots(
    cash_flows: Sequence[CashFlow],
    *,
    min_rate: float = -0.999999,
    max_rate: float = 100.0,
    samples: int = 1600,
    max_iterations: int = 200,
    rate_tolerance: float = 1e-12,
    npv_tolerance: float = 1e-9,
) -> list[float]:
    """Return roots found by scanning sign changes and solving each bracket."""
    roots: list[float] = []
    for low, high in find_brackets(
        cash_flows, min_rate=min_rate, max_rate=max_rate, samples=samples
    ):
        if low == high:
            root = low
        else:
            root, _, _ = _bisect(
                cash_flows, low, high, max_iterations=max_iterations,
                rate_tolerance=rate_tolerance, npv_tolerance=npv_tolerance,
            )
            if root is None:
                continue
        if not any(abs(root - other) <= 1e-7 * max(1.0, abs(root)) for other in roots):
            roots.append(root)
    return sorted(roots)


def solve_rate(
    cash_flows: Sequence[CashFlow],
    *,
    initial_guess: float = 0.10,
    max_iterations: int = 100,
    rate_tolerance: float = 1e-12,
    npv_tolerance: float = 1e-9,
    derivative_tolerance: float = 1e-14,
    min_rate: float = -0.999999,
    max_rate: float = 100.0,
    scan_for_roots: bool = True,
) -> SolverResult:
    """Solve NPV(rate)=0 using damped Newton and bracketed fallback.

    If root scanning finds multiple sign-changing roots, the successful
    Newton result is retained when it is valid. If Newton fails, the nearest
    detected bracket is used for bisection. Root scan results are diagnostic.
    """
    validate_cash_flows(cash_flows)
    if not math.isfinite(initial_guess) or initial_guess <= -1.0:
        raise InputError("Initial guess must be finite and greater than -1.")
    if max_iterations < 1:
        raise InputError("max_iterations must be at least 1.")
    if rate_tolerance <= 0 or npv_tolerance <= 0 or derivative_tolerance <= 0:
        raise InputError("Tolerances must be positive.")
    if not (-1.0 < min_rate < max_rate):
        raise InputError("Require -1 < min_rate < max_rate.")

    brackets = find_brackets(cash_flows, min_rate=min_rate, max_rate=max_rate) if scan_for_roots else []
    detected_roots: list[float] = []
    if scan_for_roots:
        for bracket_low, bracket_high in brackets:
            if bracket_low == bracket_high:
                candidate_root = bracket_low
            else:
                candidate_root, _, _ = _bisect(
                    cash_flows, bracket_low, bracket_high,
                    max_iterations=max_iterations,
                    rate_tolerance=rate_tolerance,
                    npv_tolerance=npv_tolerance,
                )
                if candidate_root is None:
                    continue
            if not any(
                abs(candidate_root - old_root) <= 1e-7 * max(1.0, abs(candidate_root))
                for old_root in detected_roots
            ):
                detected_roots.append(candidate_root)
    roots_found = tuple(sorted(detected_roots))

    rate = min(max(initial_guess, min_rate), max_rate)
    records: list[IterationRecord] = []
    failure_status = "max_iterations"
    failure_message = "Maximum iteration count reached without confirmed convergence."

    for iteration in range(1, max_iterations + 1):
        value = npv(rate, cash_flows)
        derivative = npv_derivative(rate, cash_flows)
        if math.isfinite(value) and abs(value) <= npv_tolerance:
            return SolverResult(True, rate, "converged", "NPV residual is within tolerance.",
                                iteration - 1, value, tuple(records), roots_found)
        if not math.isfinite(value):
            failure_status = "non_finite_npv"
            failure_message = "NPV became non-finite; trying a bracketed fallback."
            break
        if not math.isfinite(derivative) or abs(derivative) < derivative_tolerance:
            failure_status = "small_derivative"
            failure_message = "Derivative is zero, non-finite, or too small; trying a bracketed fallback."
            break

        step = value / derivative
        accepted_rate: float | None = None
        accepted_npv: float | None = None
        damping = 1.0
        for _ in range(60):
            trial = rate - damping * step
            if min_rate < trial <= max_rate and math.isfinite(trial):
                trial_value = npv(trial, cash_flows)
                if math.isfinite(trial_value) and abs(trial_value) < abs(value):
                    accepted_rate, accepted_npv = trial, trial_value
                    break
            damping *= 0.5

        if accepted_rate is None or accepted_npv is None:
            failure_status = "newton_stalled"
            failure_message = "Newton step did not reduce |NPV|; trying a bracketed fallback."
            break

        records.append(IterationRecord(
            iteration, accepted_rate, accepted_npv,
            npv_derivative(accepted_rate, cash_flows),
            "newton" if damping == 1.0 else "damped-newton",
        ))
        if roots_found:
            current_root_distance = min(abs(rate - root) for root in roots_found)
            candidate_root_distance = min(abs(accepted_rate - root) for root in roots_found)
            if candidate_root_distance > current_root_distance * 1.25 + rate_tolerance:
                failure_status = "newton_moving_away_from_root"
                failure_message = (
                    "Newton step moved farther from every detected root; "
                    "switching to the nearest bracketed root."
                )
                break
        step_is_small = abs(accepted_rate - rate) <= rate_tolerance * max(1.0, abs(accepted_rate))
        if step_is_small:
            if abs(accepted_npv) <= npv_tolerance:
                return SolverResult(True, accepted_rate, "converged",
                                    "Rate step and NPV residual are within tolerance.",
                                    iteration, accepted_npv, tuple(records), roots_found)
            failure_status = "newton_stalled"
            failure_message = (
                "Newton step stagnated while the NPV residual remained above tolerance; "
                "trying a bracketed fallback."
            )
            break
        rate = accepted_rate

    if brackets:
        fallback_target = min(max(initial_guess, min_rate), max_rate)
        low, high = min(
            brackets,
            key=lambda bracket: 0.0 if bracket[0] <= fallback_target <= bracket[1]
            else min(abs(fallback_target - bracket[0]), abs(fallback_target - bracket[1])),
        )
        if low == high:
            residual = npv(low, cash_flows)
            return SolverResult(True, low, "converged", "A sampled point has zero NPV.",
                                len(records), residual, tuple(records), roots_found)
        root, _, bisect_records = _bisect(
            cash_flows, low, high, max_iterations=max_iterations,
            rate_tolerance=rate_tolerance, npv_tolerance=npv_tolerance,
        )
        iteration_offset = len(records)
        records.extend(IterationRecord(
            iteration_offset + index, rec.rate, rec.npv, rec.derivative, rec.method
        ) for index, rec in enumerate(bisect_records, start=1))
        if root is not None and abs(npv(root, cash_flows)) <= max(npv_tolerance * 10, 1e-8):
            return SolverResult(True, root, "converged", "Solved using bracketed bisection fallback.",
                                len(records), npv(root, cash_flows), tuple(records), roots_found)

    return SolverResult(False, None, failure_status, failure_message, len(records),
                        npv(rate, cash_flows), tuple(records), roots_found)
