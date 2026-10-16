"""Label PR comments in one or more repos and write a report.

    python run.py --repo owner/name                       # comments from yesterday (UTC)
    python run.py --repo a/b --repo c/d --since 2026-10-01 --until 2026-10-08
    python run.py --repo owner/name --pr 123 --pr 456     # every comment on these PRs

Dates are UTC calendar days; --until is exclusive and defaults to the day
after --since. With --pr and no dates, all comments on those PRs are labelled.
Fetching uses the gh CLI, so run `gh auth login` first.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sentiment.classifier import Classifier, dump_results
from sentiment.github_client import GitHubClient, collect_inputs
from sentiment.report import render_markdown


def _day(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", action="append", required=True, help="owner/name; repeatable.")
    p.add_argument("--pr", action="append", type=int, help="Only these PR numbers; repeatable. Needs a single --repo.")
    p.add_argument("--since", type=_day, help="First UTC day to include, YYYY-MM-DD. Default: yesterday.")
    p.add_argument("--until", type=_day, help="UTC day to stop before, YYYY-MM-DD. Default: --since + 1 day.")
    p.add_argument("--out", default="out", help="Output directory.")
    p.add_argument("--effort", default="medium", help="Effort for the first pass.")
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    if args.pr and len(args.repo) > 1:
        p.error("--pr works with exactly one --repo")
    return args


def window(args: argparse.Namespace) -> tuple[datetime, datetime]:
    if args.pr and not args.since and not args.until:
        return datetime(1970, 1, 1, tzinfo=timezone.utc), datetime(9999, 1, 1, tzinfo=timezone.utc)
    if args.since:
        start = args.since
    else:
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start = today - timedelta(days=1)
    return start, args.until or start + timedelta(days=1)


def main() -> None:
    args = parse_args()
    start, end = window(args)
    if args.pr and not args.since and not args.until:
        label = f"{args.repo[0].replace('/', '_')}_pr_{'_'.join(map(str, args.pr))}"
    else:
        label = f"{start.date()}_to_{(end - timedelta(days=1)).date()}"

    inputs = collect_inputs(GitHubClient(), args.repo, start, end, args.pr)
    print(f"{len(inputs)} comments to look at in {', '.join(args.repo)}")
    results = Classifier(effort=args.effort).classify_all(inputs, workers=args.workers)

    out_dir = Path(args.out) / label
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.jsonl").write_text(dump_results(results))
    report = render_markdown(results, label.replace("_", " "))
    (out_dir / "report.md").write_text(report)
    print(report)
    print(f"Wrote {out_dir}/report.md and results.jsonl")


if __name__ == "__main__":
    main()
