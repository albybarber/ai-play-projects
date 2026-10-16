#!/usr/bin/env python3
"""Read-only helper for the pr-tone skill.

Every GitHub call goes through `gh api --method GET` on a fixed set of
endpoints; this script never writes to GitHub or to disk. It only prints.

    prtone.py fetch --repo owner/name [--author login ...] [--since YYYY-MM-DD] [--until YYYY-MM-DD]
    prtone.py fetch --org acme --author alice --author bob --since 2026-10-01
    prtone.py fetch --repo owner/name --pr 123
    prtone.py calibrate             # print the labelled eval cases, without their answers
    prtone.py score < labels.jsonl  # score {"case": n, "tone": ..., ...} lines read from stdin
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator
from urllib.parse import quote

PER_PAGE = 100
MAX_CONTEXT_CHARS = 1500  # non-target comments are context; long ones are trimmed
MAX_TARGET_CHARS = 8000
MAX_HUNK_LINES = 15
EVAL_FILE = Path(__file__).resolve().parent.parent / "eval" / "labeled.jsonl"

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
NAME_RE = re.compile(r"^[A-Za-z0-9-]+(\[bot\])?$")
TRIVIAL_RE = re.compile(
    r"^\s*(lgtm|looks good( to me)?|ship it|approved?|thanks!?|thank you!?|ty|"
    r"\+1|:\+1:|👍|✅|🚀|done\.?|fixed\.?|nit\.?)\s*[.!]*\s*$",
    re.IGNORECASE,
)
BOT_RE = re.compile(r"(\[bot\]$|-bot$|^dependabot|^renovate|^github-actions|^codecov)", re.IGNORECASE)

Runner = Callable[[str], str]


# ---------------------------------------------------------------- GitHub (GET only)


def gh_get(path: str) -> str:
    """The only way this script talks to GitHub: an HTTP GET through the gh CLI."""
    proc = subprocess.run(["gh", "api", "--method", "GET", path], capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"gh api GET {path} failed: {proc.stderr.strip()}")
    return proc.stdout


def pages(get: Runner, path: str, params: str = "", key: str | None = None) -> Iterator[dict]:
    page = 1
    while True:
        sep = "&" if params else ""
        data = json.loads(get(f"{path}?{params}{sep}per_page={PER_PAGE}&page={page}"))
        items = data[key] if key else data
        yield from items
        if len(items) < PER_PAGE:
            return
        page += 1


def search_prs(get: Runner, scope: list[str], authors: list[str], since: str) -> list[dict]:
    """PRs updated since `since` in scope, involving or reviewed by any author. Newest first."""
    base = " ".join([f"is:pr updated:>={since}", *scope])
    queries = [f"{base} {q}:{a}" for a in authors for q in ("involves", "reviewed-by")] or [base]
    found: dict[str, dict] = {}
    for q in queries:
        for item in pages(get, "search/issues", f"q={quote(q)}&sort=updated&order=desc", key="items"):
            repo = item["repository_url"].split("/repos/", 1)[1]
            found[f"{repo}#{item['number']}"] = {
                "repo": repo,
                "number": item["number"],
                "title": item["title"],
                "author": (item.get("user") or {}).get("login", "ghost"),
                "url": item["html_url"],
                "updated_at": item["updated_at"],
            }
    return sorted(found.values(), key=lambda p: p["updated_at"], reverse=True)


def list_repo_prs(get: Runner, repo: str, since: datetime) -> list[dict]:
    """PRs in one repo updated at or after `since`, via the repo's own list endpoint (stops early)."""
    out = []
    for pr in pages(get, f"repos/{repo}/pulls", "state=all&sort=updated&direction=desc"):
        if datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00")) < since:
            break
        out.append({"repo": repo, "number": pr["number"], "title": pr["title"],
                    "author": (pr.get("user") or {}).get("login", "ghost"),
                    "url": pr["html_url"], "updated_at": pr["updated_at"]})
    return out


def get_pr(get: Runner, repo: str, number: int) -> dict:
    pr = json.loads(get(f"repos/{repo}/pulls/{number}"))
    return {
        "repo": repo,
        "number": number,
        "title": pr["title"],
        "author": (pr.get("user") or {}).get("login", "ghost"),
        "url": pr["html_url"],
        "updated_at": pr["updated_at"],
    }


def _user(c: dict) -> tuple[str, bool]:
    u = c.get("user") or {}
    return u.get("login", "ghost"), u.get("type") == "Bot"


def pr_comments(get: Runner, repo: str, number: int) -> list[dict]:
    """Conversation comments, inline review comments and review summaries, oldest first."""
    out = []
    for c in pages(get, f"repos/{repo}/issues/{number}/comments"):
        login, bot = _user(c)
        out.append({"id": f"issue_comment:{c['id']}", "kind": "comment", "author": login, "bot": bot,
                    "body": c.get("body") or "", "created_at": c["created_at"], "updated_at": c["updated_at"],
                    "url": c["html_url"], "thread": "conversation"})

    review_comments = list(pages(get, f"repos/{repo}/pulls/{number}/comments"))
    by_id = {c["id"]: c for c in review_comments}
    for c in review_comments:
        login, bot = _user(c)
        hunk = "\n".join((c.get("diff_hunk") or "").splitlines()[-MAX_HUNK_LINES:])
        out.append({"id": f"review_comment:{c['id']}", "kind": "inline", "author": login, "bot": bot,
                    "body": c.get("body") or "", "created_at": c["created_at"], "updated_at": c["updated_at"],
                    "url": c["html_url"], "thread": f"review_thread:{thread_root(c, by_id)}",
                    "file": c.get("path"), "diff_hunk": hunk or None})

    for r in pages(get, f"repos/{repo}/pulls/{number}/reviews"):
        if not (r.get("body") or "").strip() or not r.get("submitted_at"):
            continue
        login, bot = _user(r)
        out.append({"id": f"review:{r['id']}", "kind": "review", "author": login, "bot": bot,
                    "body": r["body"], "created_at": r["submitted_at"], "updated_at": r["submitted_at"],
                    "url": r["html_url"], "thread": "conversation", "review_state": r.get("state")})
    out.sort(key=lambda c: c["created_at"])
    return out


def thread_root(c: dict, by_id: dict[int, dict]) -> int:
    seen = set()
    while c.get("in_reply_to_id") in by_id and c["id"] not in seen:
        seen.add(c["id"])
        c = by_id[c["in_reply_to_id"]]
    return c["id"]


# ---------------------------------------------------------------- selection


def skip_reason(c: dict) -> str | None:
    if c.get("bot") or BOT_RE.search(c["author"]):
        return "bot"
    body = c["body"].strip()
    if not body:
        return "empty"
    if TRIVIAL_RE.match(body):
        return "trivial"
    return None


def mark_targets(comments: list[dict], start: datetime, end: datetime, authors: set[str], skipped: Counter) -> int:
    """Set c["target"] on comments to label; returns how many."""
    n = 0
    for c in comments:
        ts = datetime.fromisoformat(c["updated_at"].replace("Z", "+00:00"))
        c["target"] = False
        if not (start <= ts < end) or (authors and c["author"].lower() not in authors):
            continue
        reason = skip_reason(c)
        if reason:
            skipped[reason] += 1
            continue
        c["target"] = True
        n += 1
    return n


# ---------------------------------------------------------------- rendering


def _attr(v: object) -> str:
    return str(v).replace('"', "'")


def _text(s: str) -> str:
    # Comment bodies are untrusted; stop them from closing our tags early.
    return re.sub(r"</(comment|pr|case|diff_hunk)", r"&lt;/\1", s)


def render_pr(pr: dict, comments: list[dict]) -> str:
    lines = [f'<pr repo="{pr["repo"]}" number="{pr["number"]}" author="{_attr(pr["author"])}" '
             f'url="{pr["url"]}" title="{_attr(pr["title"])}">']
    for c in comments:
        if not c["body"].strip():
            continue
        attrs = [f'id="{c["id"]}"', f'author="{c["author"]}"', f'kind="{c["kind"]}"',
                 f'at="{c["created_at"]}"', f'thread="{c["thread"]}"']
        for k in ("file", "review_state"):
            if c.get(k):
                attrs.append(f'{k}="{_attr(c[k])}"')
        if c.get("target"):
            attrs += ['target="yes"', f'url="{c["url"]}"']
        body = c["body"].strip()
        limit = MAX_TARGET_CHARS if c.get("target") else MAX_CONTEXT_CHARS
        if len(body) > limit:
            body = body[:limit] + " …[trimmed]"
        lines.append(f"<comment {' '.join(attrs)}>")
        if c.get("target") and c.get("diff_hunk"):
            lines.append(f"<diff_hunk>\n{_text(c['diff_hunk'])}\n</diff_hunk>")
        lines += [_text(body), "</comment>"]
    lines.append("</pr>")
    return "\n".join(lines)


# ---------------------------------------------------------------- commands


def _day(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def cmd_fetch(args: argparse.Namespace, get: Runner = gh_get) -> str:
    for r in args.repo:
        if not REPO_RE.match(r):
            sys.exit(f"bad --repo {r!r}; expected owner/name")
    for n in args.org + args.author:
        if not NAME_RE.match(n):
            sys.exit(f"bad GitHub name {n!r}")
    if args.pr and len(args.repo) != 1:
        sys.exit("--pr needs exactly one --repo")
    if not (args.repo or args.org or args.author):
        sys.exit("give at least one of --repo, --org or --author")

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if args.pr and not args.since:
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)
    else:
        start = args.since or today - timedelta(days=7)
    end = args.until or today + timedelta(days=1)
    authors = {a.lower() for a in args.author}

    if args.pr:
        prs = [get_pr(get, args.repo[0], n) for n in args.pr]
    elif args.repo and not args.org:
        # Listing each repo's PRs directly avoids search-index lag and the 1000-result cap.
        prs = sorted((p for r in args.repo for p in list_repo_prs(get, r, start)),
                     key=lambda p: p["updated_at"], reverse=True)
    else:
        scope = [f"repo:{r}" for r in args.repo] + [f"org:{o}" for o in args.org]
        prs = search_prs(get, scope, args.author, start.date().isoformat())
    total = len(prs)
    window = prs[args.offset: args.offset + args.limit]

    skipped: Counter = Counter()
    blocks, targets = [], 0
    for pr in window:
        comments = pr_comments(get, pr["repo"], pr["number"])
        n = mark_targets(comments, start, end, authors, skipped)
        if n:
            targets += n
            blocks.append(render_pr(pr, comments))

    shown_to = args.offset + len(window)
    head = [
        f"# window: {start.date()} to {(end - timedelta(days=1)).date()} (UTC, inclusive)",
        f"# authors: {', '.join(args.author) or 'everyone'}",
        f"# PRs {args.offset + 1 if window else 0}-{shown_to} of {total}; "
        f"{len(blocks)} with comments to label; {targets} target comments",
        f"# skipped before labelling: {dict(skipped) or 'none'}",
    ]
    if shown_to < total:
        head.append(f"# MORE: rerun with --offset {shown_to} for the next {args.limit} PRs")
    if total >= 1000:
        head.append("# WARNING: search returns at most 1000 PRs; narrow the dates or scope")
    return "\n".join(head) + "\n\n" + "\n\n".join(blocks) + "\n"


def load_cases() -> list[dict]:
    return [json.loads(l) for l in EVAL_FILE.read_text().splitlines() if l.strip()]


def cmd_calibrate(_: argparse.Namespace) -> str:
    out = []
    for i, row in enumerate(load_cases(), 1):
        inp = row["input"]
        comments = [{**c, "kind": c.get("kind", "comment"), "thread": c.get("thread_id", "conversation")}
                    for c in inp["prior_comments"]]
        comments.append({**inp["target"], "thread": inp["target"].get("thread_id", "conversation"), "target": True})
        out.append(f'<case id="{i}">\n{render_pr(inp["pr"], comments)}\n</case>')
    return "\n\n".join(out) + "\n"


TONES = ["kind", "neutral", "mean", "toxic"]
HARSH = {"mean", "toxic"}
FIELDS = ["tone", "helpfulness", "conflict"]


def score(cases: list[dict], answers: dict[int, dict]) -> str:
    pairs = [(c, answers.get(i)) for i, c in enumerate(cases, 1)]
    n = len(pairs)
    lines = [f"{n} cases, {sum(1 for _, a in pairs if a)} answered"]
    for f in FIELDS:
        ok = sum(1 for c, a in pairs if a and a.get(f) == c["expected"][f])
        lines.append(f"  {f:<12} {ok}/{n} ({ok / n:.0%})")
    tp = sum(1 for c, a in pairs if c["expected"]["tone"] in HARSH and a and a.get("tone") in HARSH)
    fp = sum(1 for c, a in pairs if c["expected"]["tone"] not in HARSH and a and a.get("tone") in HARSH)
    fn = sum(1 for c, a in pairs if c["expected"]["tone"] in HARSH and not (a and a.get("tone") in HARSH))
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    lines.append(f"  mean|toxic   precision {prec:.0%}  recall {rec:.0%}")
    misses = []
    for i, (c, a) in enumerate(pairs, 1):
        wrong = [f for f in FIELDS if not a or a.get(f) != c["expected"][f]]
        if wrong:
            got = {f: (a or {}).get(f) for f in wrong}
            want = {f: c["expected"][f] for f in wrong}
            misses.append(f"  case {i} ({c.get('note', '')}): expected {want}, got {got}")
    if misses:
        lines += ["misses:", *misses]
    return "\n".join(lines) + "\n"


def cmd_score(_: argparse.Namespace) -> str:
    answers = {}
    for line in sys.stdin:
        if line.strip():
            a = json.loads(line)
            answers[int(a["case"])] = a
    return score(load_cases(), answers)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="print PR threads with the comments to label marked target=\"yes\"")
    f.add_argument("--repo", action="append", default=[], help="owner/name; repeatable")
    f.add_argument("--org", action="append", default=[], help="organisation or user; repeatable")
    f.add_argument("--author", action="append", default=[], help="only label comments by these logins; repeatable")
    f.add_argument("--pr", action="append", type=int, help="specific PR numbers (one --repo)")
    f.add_argument("--since", type=_day, help="first UTC day, YYYY-MM-DD (default: 7 days ago)")
    f.add_argument("--until", type=_day, help="UTC day to stop before, YYYY-MM-DD (default: tomorrow)")
    f.add_argument("--offset", type=int, default=0)
    f.add_argument("--limit", type=int, default=20, help="PRs per call")
    sub.add_parser("calibrate", help="print eval cases without answers")
    sub.add_parser("score", help="score answers read from stdin")
    args = p.parse_args(argv)
    run = {"fetch": cmd_fetch, "calibrate": cmd_calibrate, "score": cmd_score}[args.cmd]
    sys.stdout.write(run(args))


if __name__ == "__main__":
    main()
