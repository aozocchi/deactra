# Deactra

**A lightweight, cross-platform actuarial interest-rate solver.**

Deactra solves for the annual effective interest rate `i` that makes the net present value of a set of cash flows equal to zero:

$$
\sum_{k=1}^{n} CF_k(1+i)^{-t_k}=0, \qquad i>-1.
$$

It uses a safeguarded Newton-Raphson method and can fall back to bisection when it finds a sign-changing bracket. It also reports common equivalent actuarial rates. Deactra requires Python 3.10+ and has no third-party runtime dependencies.

## Quick start

Cash-flow values are positional arguments; `-t` / `--times` supplies the matching times in years. Items are paired **by position** and are not automatically reordered.

```bash
deactra -1000 600 600 -t 0 1 2
```

Example with a custom cash-flow schedule:

```bash
deactra -1000 2426 2093 300 -t 9 2 3 7
```

In that command, `-1000` is paired with time `9`, `2426` with time `2`, and so on. Double-check that this pairing reflects the intended cash-flow schedule before interpreting the result.

## Install for development

### Linux / macOS (Bash or Zsh)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
deactra --help
```

### Linux / macOS (Fish)

```fish
python3 -m venv .venv
source .venv/bin/activate.fish
python -m pip install -e ".[test]"
deactra --help
```

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
deactra --help
```

If PowerShell blocks activation scripts, use Command Prompt instead:

```bat
.venv\Scripts\activate.bat
python -m pip install -e ".[test]"
deactra --help
```

Once the environment is activated and the package is installed, the command is the same on Linux, Windows, and macOS: `deactra`. Windows creates a `deactra.exe` console launcher, which PowerShell and Command Prompt can resolve from the name `deactra`.

### Install as a user-level command

If you want `deactra` available in regular terminals without activating this repository's virtual environment, install it with [pipx](https://pipx.pypa.io/):

```bash
pipx install .
deactra --help
```

Run this from the repository root after installing pipx and ensuring its application directory is on `PATH`. Use the environment-based method above for development; use pipx for an isolated command-line installation.

## CLI options

```text
deactra CASH_FLOW [CASH_FLOW ...] -t YEARS [YEARS ...]
        [--guess RATE]
        [--max-iterations N]
        [--rate-tolerance VALUE]
        [--npv-tolerance VALUE]
        [--min-rate VALUE]
        [--max-rate VALUE]
        [--no-root-scan]
        [--verbose]
        [--roots]
        [--json]
```

Examples:

```bash
# Print iteration details
deactra -1000 600 600 -t 0 1 2 --verbose

# Report roots detected by sign-change scanning
deactra -1000 600 600 -t 0 1 2 --roots

# JSON output for scripts
deactra -1000 600 600 -t 0 1 2 --json

# Run as a Python module (also works after installation)
python -m deactra -1000 600 600 -t 0 1 2
```

Run `deactra` without arguments to use interactive input, or `deactra --help` for the full options.

## What it reports

- Effective annual interest rate `i`.
- Discount factor `v = 1 / (1 + i)`.
- Effective discount rate `d = i / (1 + i)`.
- Force of interest `delta = ln(1 + i)`.
- Nominal rates convertible semi-annually, quarterly, and monthly.
- Solver convergence status, NPV residual, and optional iteration trace.
- Optional sampled root diagnostics for cash-flow schedules with potential multiple IRRs.

## Numerical notes and limitations

- Newton-Raphson is damped when a full step does not reduce absolute NPV. When the step stalls and a sign-changing interval was detected, Deactra tries bisection.
- The root scan is a diagnostic, not a proof that every root has been found. Roots touching zero without changing sign may be missed, and results depend on the configured search range.
- Cash flows with multiple sign changes can have multiple IRRs. The root returned by the main solver is not guaranteed to be the only economically meaningful rate.
- NPV tolerance is expressed in the same monetary units as the input cash flows. Select a tolerance appropriate to the scale of the amounts.
- Cash-flow times are expected in years and must be non-negative. Amounts and times are paired by position, not sorted.
- Deactra is an educational and analytical tool, not a substitute for independent validation for regulated or high-stakes financial decisions.

## Development

```bash
python -m pip install -e ".[test]"
python -m pytest
```

GitHub Actions is configured to run tests on Linux, Windows, and macOS across Python 3.10, 3.12, and 3.13.

## Project structure

```text
src/deactra/       Core package and CLI
  cashflows.py     Validation and cash-flow diagnostics
  models.py        Immutable data models
  rates.py         Equivalent actuarial rate conversions
  solver.py        NPV, derivative, Newton-Raphson, bisection, root scan
  cli.py           Cross-platform command-line interface
tests/             Automated tests
.github/workflows/ Cross-platform CI
```

## License

MIT. See [LICENSE](LICENSE).
