# aip-calculator

A simple browser-based Annual Incentive Plan (AIP) bonus calculator with proration support.

## Usage

[Open live demo](https://albybarber.github.io/ai-play-projects/aip-calculator/aip-calculator.html) or open `aip-calculator.html` locally in a browser.

## Inputs

- **Fiscal Year Start / End** — Defaults to November 29, 2025 through November 27, 2026 (364 days); both dates are editable
- **Start Date** — Your start date within the fiscal year
- **Annual Salary** — Your base annual salary
- **AIP Target %** — Your target bonus percentage
- **Corporate Performance Factor %** — Company performance multiplier (default: 100%)
- **Individual Performance Factor %** — Your personal performance multiplier

## How it works

1. Calculates days worked within the fiscal year period
2. Prorates the bonus target based on days worked vs total days
3. Applies corporate and individual performance factors
4. Outputs the final estimated AIP payout
