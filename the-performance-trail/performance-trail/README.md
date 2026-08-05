# The Performance Trail

An Oregon Trail themed performance review assistant.

## Prerequisites

- Python 3.12+
- Anthropic API key

## Setup and Run

Install dependencies:
```bash
pip install -r requirements.txt
```

Run with your API key:
```bash
export ANTHROPIC_API_KEY=sk-...
python app.py
# open http://localhost:5000
```

Run in mock mode (no API key needed for testing):
```bash
MOCK=1 python app.py
```

## Input Files

Place your labeled-block input files in the `inputs/` directory. This directory is gitignored, so employee performance data is never committed to version control.
