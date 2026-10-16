"""Daily entry point: fetch yesterday's PR comments, label them, write a report.

    python run_daily.py --repo owner/name [--repo owner/other] [--day 2026-10-15]

Writes out/<day>/results.jsonl and out/<day>/report.md. The day is a UTC
calendar day, so a cron that runs a few minutes late never misses or
double-counts comments.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sentiment.classifier import Classifier, dump_results
from sentiment.github_client import GitHubClient, collect_inputs
from sentiment.report import render_markdown


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", action="append", default=[], help="owner/name; repeatable. Defaults to $REPOS (comma-separated).")
    p.add_argument("--day", help="UTC day to process, YYYY-MM-DD. Defaults to yesterday.")
    p.add_argument("--out", default="out", help="Output directory.")
    p.add_argument("--effort", default="medium", help="Effort for the first pass.")
    p.add_argument("--workers", type=int, default=4)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    repos = args.repo or [r.strip() for r in os.environ.get("REPOS", "").split(",") if r.strip()]
    if not repos:
        raise SystemExit("No repos given: pass --repo owner/name or set REPOS.")

    if args.day:
        start = datetime.fromisoformat(args.day).replace(tzinfo=timezone.utc)
    else:
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start = today - timedelta(days=1)
    end = start + timedelta(days=1)
    day = start.date().isoformat()

    inputs = collect_inputs(GitHubClient(), repos, start, end)
    print(f"{len(inputs)} comments in {', '.join(repos)} on {day}")
    results = Classifier(effort=args.effort).classify_all(inputs, workers=args.workers)

    out_dir = Path(args.out) / day
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.jsonl").write_text(dump_results(results))
    report = render_markdown(results, day)
    (out_dir / "report.md").write_text(report)
    print(f"Wrote {out_dir}/report.md")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(report)


if __name__ == "__main__":
    main()
