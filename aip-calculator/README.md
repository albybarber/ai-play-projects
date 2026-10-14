# aip-calculator

A simple browser-based Annual Incentive Plan (AIP) bonus calculator with proration support.

## Usage

[Open live demo](https://albybarber.github.io/ai-play-projects/aip-calculator/aip-calculator.html) or open `aip-calculator.html` locally in a browser.

## Inputs

- **Fiscal Year Start / End** — Defaults to November 29, 2025 through November 27, 2026 (364 days); both dates are editable
- **Start Date** — Your start date within the fiscal year
- **I was employed for the full fiscal year** — Unchecked by default. Check to use 100% proration for the selected fiscal year without entering a start date. This is self-declared, with no anniversary checks. The start-date input is disabled but its value is retained; unchecking restores start-date validation against the current fiscal year.
- **Annual Salary** — Your base annual salary
- **AIP Target %** — Your target bonus percentage
- **Corporate Performance Factor %** — Company performance multiplier (default: 100%)
- **Individual Performance Factor %** — Your personal performance multiplier

## How it works

1. Validates the fiscal year range and counts days inclusively
2. Prorates the bonus target based on days worked vs total days, or uses 100% when full-fiscal-year employment is checked
3. Applies corporate and individual performance factors
4. Outputs the final estimated AIP payout

Full-year results explicitly show **Full fiscal year (self-declared)** and **100.00%** proration. Editing fiscal dates still requires a valid range in either mode; salary, AIP target, and both performance factors apply unchanged.

## Development

Run browser regression tests with Node.js 22+ and Google Chrome on macOS (no packages required):

```bash
node --test tests/aip-calculator.test.mjs
```

On other platforms, set `BROWSER_PATH` to your Chrome or Chromium executable.
