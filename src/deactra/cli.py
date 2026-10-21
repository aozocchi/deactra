"""Command-line interface for Deactra."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict
from collections.abc import Sequence

from deactra.cashflows import InputError, cash_flow_diagnostic, validate_cash_flows
from deactra.models import CashFlow, SolverResult
from deactra.rates import equivalent_rates
from deactra.solver import solve_rate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deactra",
        description="Calculate an effective annual interest rate from cash flows.",
        epilog=(
            "Example: deactra -1000 600 600 -t 0 1 2\n"
            "Times are paired with cash flows by position and are measured in years."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("cash_flows", nargs="*", type=float, metavar="CASH_FLOW",
                        help="cash-flow amounts, in order")
    parser.add_argument("-t", "--times", nargs="+", type=float, metavar="YEARS",
                        help="time in years for each cash flow")
    parser.add_argument("--guess", type=float, default=0.10,
                        help="initial rate guess as a decimal (default: 0.10)")
    parser.add_argument("--max-iterations", type=int, default=100,
                        help="maximum Newton or bisection iterations (default: 100)")
    parser.add_argument("--rate-tolerance", type=float, default=1e-12,
                        help="rate convergence tolerance (default: 1e-12)")
    parser.add_argument("--npv-tolerance", type=float, default=1e-9,
                        help="absolute NPV convergence tolerance (default: 1e-9)")
    parser.add_argument("--min-rate", type=float, default=-0.999999,
                        help="minimum rate to scan; must be greater than -1")
    parser.add_argument("--max-rate", type=float, default=100.0,
                        help="maximum rate to scan (100 means 10000%%)")
    parser.add_argument("--no-root-scan", action="store_true",
                        help="skip root-scan diagnostics (faster for repeated calls)")
    parser.add_argument("--verbose", action="store_true", help="show iteration log")
    parser.add_argument("--roots", action="store_true",
                        help="list roots detected by sign-change scanning")
    parser.add_argument("--json", action="store_true", help="write machine-readable JSON")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    return parser


def _interactive_input() -> list[CashFlow]:
    print("Deactra | Actuarial Rate Solver")
    print("Enter cash flows and times in years, separated by spaces.\n")
    try:
        amounts = [float(value) for value in input("Cash flows : ").split()]
        times = [float(value) for value in input("Times      : ").split()]
    except ValueError as exc:
        raise InputError("Please enter numeric values separated by spaces.") from exc
    if len(amounts) != len(times):
        raise InputError(f"Data mismatch: {len(amounts)} cash flows vs {len(times)} times.")
    return [CashFlow(amount, time) for amount, time in zip(amounts, times)]


def _report(cash_flows: Sequence[CashFlow], result: SolverResult,
            *, verbose: bool, show_roots: bool) -> None:
    print("Deactra | Actuarial Rate Solver")
    print("Equation: sum(CF[k] * (1 + i)^(-t[k])) = 0")
    print(f"Cash flows: {len(cash_flows)}")
    print(f"Cash-flow sign changes: {cash_flow_diagnostic(cash_flows)['sign_changes']}")

    if verbose:
        print("\nIteration log")
        print(f"{'#':>4}  {'method':<14} {'rate':>16} {'NPV':>16} {'derivative':>16}")
        print("-" * 74)
        for rec in result.records:
            print(f"{rec.iteration:>4}  {rec.method:<14} {rec.rate:>16.10f} "
                  f"{rec.npv:>16.7g} {rec.derivative:>16.7g}")

    print("\nSolver status")
    print(f"  Status     : {result.status}")
    print(f"  Converged  : {'yes' if result.converged else 'no'}")
    print(f"  Iterations : {result.iterations}")
    print(f"  Message    : {result.message}")

    if result.converged and result.rate is not None:
        rates = equivalent_rates(result.rate)
        print("\nEquivalent rates")
        print(f"  Effective annual rate (i) : {rates.effective_annual:.10f} ({rates.effective_annual * 100:.8f}%)")
        print(f"  Discount factor (v)       : {rates.discount_factor:.12f}")
        print(f"  Effective discount (d)    : {rates.effective_discount:.10f} ({rates.effective_discount * 100:.8f}%)")
        print(f"  Force of interest (delta) : {rates.force_of_interest:.10f} ({rates.force_of_interest * 100:.8f}%)")
        print("\nNominal annual rates")
        print(f"  Convertible semi-annually : {rates.nominal_semiannual:.10f} ({rates.nominal_semiannual * 100:.8f}%)")
        print(f"  Convertible quarterly     : {rates.nominal_quarterly:.10f} ({rates.nominal_quarterly * 100:.8f}%)")
        print(f"  Convertible monthly       : {rates.nominal_monthly:.10f} ({rates.nominal_monthly * 100:.8f}%)")
        print(f"\n  Final NPV residual        : {result.npv:.12g}")

    if show_roots:
        print("\nDetected roots (sign-change scan; not guaranteed exhaustive)")
        if result.roots_found:
            for root in result.roots_found:
                print(f"  {root:.12f} ({root * 100:.8f}%)")
        else:
            print("  No roots detected in the configured rate range.")
    print("\nNote: times are paired by position; Deactra does not reorder cash flows.")


def _json_safe_result(result: SolverResult) -> dict[str, object]:
    return {
        "converged": result.converged,
        "rate": result.rate,
        "status": result.status,
        "message": result.message,
        "iterations": result.iterations,
        "npv": result.npv if result.npv is None or math.isfinite(result.npv) else None,
        "records": [asdict(record) for record in result.records],
        "roots_found": list(result.roots_found),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if not args.cash_flows and args.times is None:
            cash_flows = _interactive_input()
        elif not args.cash_flows or args.times is None:
            raise InputError("Provide cash flows and -t/--times together, or run without arguments for interactive mode.")
        else:
            if len(args.cash_flows) != len(args.times):
                raise InputError(f"Data mismatch: {len(args.cash_flows)} cash flows vs {len(args.times)} times.")
            cash_flows = [CashFlow(amount, time) for amount, time in zip(args.cash_flows, args.times)]

        validate_cash_flows(cash_flows)
        result = solve_rate(
            cash_flows,
            initial_guess=args.guess,
            max_iterations=args.max_iterations,
            rate_tolerance=args.rate_tolerance,
            npv_tolerance=args.npv_tolerance,
            min_rate=args.min_rate,
            max_rate=args.max_rate,
            scan_for_roots=not args.no_root_scan,
        )

        if args.json:
            payload: dict[str, object] = {
                "project": "Deactra",
                "version": "0.1.0",
                "cash_flows": [asdict(cf) for cf in cash_flows],
                "cash_flow_diagnostic": cash_flow_diagnostic(cash_flows),
                "solver_result": _json_safe_result(result),
                "equivalent_rates": asdict(equivalent_rates(result.rate))
                if result.converged and result.rate is not None else None,
            }
            print(json.dumps(payload, indent=2, allow_nan=False))
        else:
            _report(cash_flows, result, verbose=args.verbose, show_roots=args.roots)
        return 0 if result.converged else 2
    except (InputError, ValueError) as exc:
        print(f"deactra: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
