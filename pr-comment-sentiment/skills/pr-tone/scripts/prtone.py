#!/usr/bin/env python3
"""Helper for the pr-tone skill. Read-only towards GitHub; writes only to the local reports folder.

Every GitHub call is `gh api --method GET` on a fixed set of endpoints. The
only files written are under $PR_TONE_HOME (default ~/pr-tone-reports), which
must not be inside a git working tree unless git ignores it.

    prtone.py fetch --repo owner/name [--author login ...] [--since YYYY-MM-DD] [--until YYYY-MM-DD]
    prtone.py fetch --org acme --author alice --author bob --since 2026-10-01
    prtone.py fetch --repo owner/name --pr 123
    prtone.py fetch ... --offset 20 --run <run-id>   # next page, added to the same run
    prtone.py report --run <run-id> [--open] < labels.jsonl
    prtone.py show --run <run-id> --id review_comment:123
    prtone.py runs
    prtone.py calibrate             # print the labelled eval cases, without their answers
    prtone.py score < labels.jsonl  # score {"case": n, "tone": ..., ...} lines read from stdin
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator
from urllib.parse import quote

PER_PAGE = 100
MAX_CONTEXT_CHARS = 1500  # non-target comments are context; long ones are trimmed
MAX_TARGET_CHARS = 8000
MAX_HUNK_LINES = 15
MAX_CONTEXT_PER_PR = 30000  # chars of context per PR in fetch output; `show` prints everything
SEARCH_CAP = 1000  # GitHub search returns at most this many results per query
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


def pages(get: Runner, path: str, params: str = "", key: str | None = None,
          max_pages: int | None = None, meta: dict | None = None) -> Iterator[dict]:
    """Yield items page by page. With `key`, the response is an object (search) and `meta` gets its other fields."""
    page = 1
    while True:
        sep = "&" if params else ""
        data = json.loads(get(f"{path}?{params}{sep}per_page={PER_PAGE}&page={page}"))
        items = data[key] if key else data
        if meta is not None and key:
            meta.update({k: v for k, v in data.items() if k != key})
        yield from items
        if len(items) < PER_PAGE or (max_pages and page >= max_pages):
            return
        page += 1


def search_prs(get: Runner, scope: list[str], authors: list[str], since: str) -> tuple[list[dict], bool]:
    """PRs updated since `since` in scope, involving or reviewed by any author. Newest first.

    Also returns whether any query hit the search API's 1000-result cap (asking for page 11 is an error).
    """
    base = " ".join([f"is:pr updated:>={since}", *scope])
    queries = [f"{base} {q}:{a}" for a in authors for q in ("involves", "reviewed-by")] or [base]
    found: dict[str, dict] = {}
    capped = False
    for q in queries:
        meta: dict = {}
        for item in pages(get, "search/issues", f"q={quote(q)}&sort=updated&order=desc", key="items",
                          max_pages=SEARCH_CAP // PER_PAGE, meta=meta):
            repo = item["repository_url"].split("/repos/", 1)[1]
            found[f"{repo}#{item['number']}"] = {
                "repo": repo,
                "number": item["number"],
                "title": item["title"],
                "author": (item.get("user") or {}).get("login", "ghost"),
                "url": item["html_url"],
                "updated_at": item["updated_at"],
            }
        capped = capped or meta.get("total_count", 0) > SEARCH_CAP or bool(meta.get("incomplete_results"))
    return sorted(found.values(), key=lambda p: p["updated_at"], reverse=True), capped


def list_repo_prs(get: Runner, repo: str, since: datetime) -> list[dict]:
    """PRs in one repo updated at or after `since`, via the repo's own list endpoint (stops early)."""
    out = []
    for pr in pages(get, f"repos/{repo}/pulls", "state=all&sort=updated&direction=desc"):
        if _ts(pr["updated_at"]) < since:
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


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def mark_targets(comments: list[dict], start: datetime, end: datetime, authors: set[str], skipped: Counter) -> int:
    """Set c["target"] on comments to label; returns how many.

    The window is about when a comment was posted. An old comment edited inside the window is not a target,
    and a comment posted inside it but edited later still is (it is labelled as it reads now, marked edited).
    """
    n = 0
    for c in comments:
        ts = _ts(c["created_at"])
        c["target"] = False
        if not (start <= ts < end) or (authors and c["author"].lower() not in authors):
            continue
        reason = skip_reason(c)
        if reason:
            c["skip"] = reason
            skipped[reason] += 1
            continue
        c["target"] = True
        n += 1
    return n


# ---------------------------------------------------------------- rendering


def _attr(v: object) -> str:
    return str(v).replace('"', "'")


OUR_TAGS_RE = re.compile(r"<(\s*/?\s*(?:comment|pr|case|diff_hunk|omitted)\b)", re.IGNORECASE)


def _text(s: str) -> str:
    # Comment bodies are untrusted: stop them from opening or closing our tags (e.g. a forged
    # <comment ... target="yes"> attributed to someone else), in any letter case.
    return OUR_TAGS_RE.sub(r"&lt;\1", s)


def _edited(c: dict) -> bool:
    return bool(c.get("updated_at")) and c["updated_at"] != c["created_at"]


def _context_to_show(comments: list[dict], budget: int | None) -> set[int]:
    """Indexes of non-target comments to print. Over the budget, keep those in a target's review thread,
    then those nearest a target, and leave out the rest (the agent can use `show` for the full thread)."""
    shown = [i for i, c in enumerate(comments) if c["body"].strip()]
    context = [i for i in shown if not comments[i].get("target")]
    if budget is None:
        return set(context)
    targets = [i for i in shown if comments[i].get("target")]
    threads = {comments[i]["thread"] for i in targets} - {"conversation"}

    def rank(i: int) -> tuple:
        return comments[i]["thread"] not in threads, min((abs(i - t) for t in targets), default=0), -i

    keep, used = set(), 0
    for i in sorted(context, key=rank):
        used += min(len(comments[i]["body"].strip()), MAX_CONTEXT_CHARS)
        if used > budget:
            break
        keep.add(i)
    return keep


def render_pr(pr: dict, comments: list[dict], budget: int | None = None) -> str:
    lines = [f'<pr repo="{pr["repo"]}" number="{pr["number"]}" author="{_attr(pr["author"])}" '
             f'url="{pr["url"]}" title="{_text(_attr(pr["title"]))}">']
    keep = _context_to_show(comments, budget)
    omitted = 0
    for i, c in enumerate(comments):
        if not c["body"].strip():
            continue
        if not c.get("target") and i not in keep:
            omitted += 1
            continue
        if omitted:
            lines.append(f'<omitted comments="{omitted}"/>')
            omitted = 0
        attrs = [f'id="{c["id"]}"', f'author="{c["author"]}"', f'kind="{c["kind"]}"',
                 f'at="{c["created_at"]}"', f'thread="{c["thread"]}"']
        for k in ("file", "review_state"):
            if c.get(k):
                attrs.append(f'{k}="{_text(_attr(c[k]))}"')
        if _edited(c):
            attrs.append('edited="yes"')
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
    if omitted:
        lines.append(f'<omitted comments="{omitted}"/>')
    lines.append("</pr>")
    return "\n".join(lines)


# ---------------------------------------------------------------- local run storage


def reports_home() -> Path:
    return Path(os.environ.get("PR_TONE_HOME") or Path.home() / "pr-tone-reports").expanduser().resolve()


def ensure_untracked(path: Path) -> None:
    """Refuse to write inside a git working tree unless git ignores the path: reports must never be committed."""
    probe = path
    while not probe.exists():
        probe = probe.parent
    try:
        inside = subprocess.run(["git", "-C", str(probe), "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, text=True)
    except FileNotFoundError:
        return  # no git installed, so nothing here can be committed
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return
    # trailing slash: a not-yet-created folder must still match directory patterns like "reports/"
    ignored = subprocess.run(["git", "-C", str(probe), "check-ignore", "-q", str(path) + "/"])
    if ignored.returncode != 0:
        sys.exit(f"refusing to write reports to {path}: it is inside a git repository and not ignored. "
                 "Set PR_TONE_HOME to a folder outside any repo (default ~/pr-tone-reports).")


def run_dir(run_id: str) -> Path:
    # must start with a letter or digit, so "." and ".." can't reach outside the reports folder
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id):
        sys.exit(f"bad run id {run_id!r}")
    return reports_home() / run_id


def _private_mkdir(path: Path) -> None:
    ensure_untracked(path)
    path.mkdir(parents=True, exist_ok=True)
    for p in (path, reports_home()):
        os.chmod(p, 0o700)  # comment text and judgements about people: owner-only


def _private_write(path: Path, text: str) -> None:
    path.write_text(text)
    os.chmod(path, 0o600)


def new_run_id(args: argparse.Namespace) -> str:
    bits = [r.split("/")[1] for r in args.repo] + args.org + args.author + [f"pr{n}" for n in args.pr or []]
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", "-".join(bits))[:60].strip("-") or "run"
    base = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slug}"
    run_id, n = base, 1
    while run_dir(run_id).exists():  # two fetches in the same second must not merge into one run
        n += 1
        run_id = f"{base}-{n}"
    return run_id


def load_run(run_id: str) -> dict:
    path = run_dir(run_id) / "threads.json"
    if not path.exists():
        sys.exit(f"no run {run_id!r} in {reports_home()}; use `prtone.py runs` to list them")
    return json.loads(path.read_text())


def _scope(args: argparse.Namespace) -> dict:
    return {"repos": args.repo, "orgs": args.org, "authors": args.author, "prs": args.pr or []}


def _window(start: datetime, end: datetime) -> dict:
    return {"start": start.date().isoformat(), "end": (end - timedelta(days=1)).date().isoformat()}


def _same_scope(a: dict, b: dict) -> bool:
    def norm(s: dict) -> tuple:
        return (sorted(r.lower() for r in s["repos"]), sorted(o.lower() for o in s["orgs"]),
                sorted(x.lower() for x in s["authors"]), sorted(s["prs"]))
    return norm(a) == norm(b)


def existing_run(args: argparse.Namespace) -> dict | None:
    """The run named by --run, if it exists, after checking this page asks for the same scope (and dates, if given)."""
    if not args.run:
        return None
    path = run_dir(args.run) / "threads.json"
    if not path.exists():
        return None
    run = json.loads(path.read_text())
    w = run["window"]
    dates_differ = ((args.since and args.since.date().isoformat() != w["start"])
                    or (args.until and (args.until - timedelta(days=1)).date().isoformat() != w["end"]))
    if not _same_scope(run["scope"], _scope(args)) or dates_differ:
        sys.exit(f"run {args.run} was fetched with a different scope or date range "
                 f"({run['scope']}, {w}); repeat the original arguments, or drop --run to start a new run")
    return run


def save_fetch(args: argparse.Namespace, start: datetime, end: datetime, fetched: list[dict],
               pr_list: list[dict], run: dict | None = None, capped: bool = False) -> str:
    """Store the threads so report/show can use them later. Pages fetched with --run are merged in.

    The full PR list from the first page is stored too, so later pages use the same list: re-listing
    could shift PRs between pages as they get updated, and would repeat the search calls.
    """
    run_id = args.run or new_run_id(args)
    d = run_dir(run_id)
    _private_mkdir(d)
    path = d / "threads.json"
    data = run or {
        "run": run_id,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": _scope(args),
        "window": _window(start, end),
        "prs": {},
    }
    data.setdefault("pr_list", pr_list)
    data["search_capped"] = data.get("search_capped", False) or capped
    for item in fetched:
        data["prs"][f"{item['pr']['repo']}#{item['pr']['number']}"] = item
    _private_write(path, json.dumps(data))
    return run_id


LABEL_FIELDS = {
    "tone": {"kind", "neutral", "mean", "toxic"},
    "helpfulness": {"helpful", "somewhat_helpful", "not_helpful"},
    "conflict": {"none", "respectful_disagreement", "contradicts_earlier"},
    "confidence": {"low", "medium", "high"},
}


def label_problems(lab: dict, body: str, known_ids: set[str]) -> list[str]:
    """Checks that keep the report fair: every concern needs an exact quote, and every dispute its reason."""
    out = []
    evidence = (lab.get("evidence") or "").strip()
    concern = lab["tone"] in ("mean", "toxic") or lab["conflict"] == "contradicts_earlier" or lab.get("disputed")
    if evidence and evidence not in body:
        out.append("evidence is not an exact quote from the comment")
    elif concern and not evidence:
        out.append("a concern needs evidence: an exact quote from the comment")
    if lab.get("disputed") and not (lab.get("charitable_reading") or "").strip():
        out.append("disputed but no charitable_reading")
    if lab["conflict"] == "contradicts_earlier" and lab.get("conflicts_with") not in known_ids:
        out.append("contradicts_earlier needs conflicts_with set to the id of a comment in the same PR")
    return out


def parse_labels(lines: list[str], run: dict, saved: dict | None = None) -> tuple[dict, list[dict], list[str]]:
    """Split stdin lines into per-comment labels, notes (summary/person), and problems.

    With `saved` (an earlier labels.json), its labels and notes are kept unless a line replaces them.
    """
    bodies, pr_ids = {}, {}
    for item in run["prs"].values():
        ids = {c["id"] for c in item["comments"]}
        for c in item["comments"]:
            if c.get("target"):
                bodies[c["id"]], pr_ids[c["id"]] = c["body"], ids - {c["id"]}
    labels = dict((saved or {}).get("labels", {}))
    notes = list((saved or {}).get("notes", []))
    problems, seen = [], set()
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"line {n}: not JSON ({e})")
            continue
        if not isinstance(obj, dict):
            problems.append(f"line {n}: expected a JSON object")
            continue
        if obj.get("type") in ("summary", "person"):
            def same(x: dict) -> bool:
                return x.get("type") == obj["type"] and (
                    obj["type"] == "summary" or str(x.get("login", "")).lower() == str(obj.get("login", "")).lower())
            notes = [x for x in notes if not same(x)] + [obj]
            continue
        cid = obj.get("id")
        if cid not in bodies:
            problems.append(f"line {n}: {cid!r} is not a target comment in this run")
            continue
        bad = [f for f, ok in LABEL_FIELDS.items() if obj.get(f) not in ok]
        if bad:
            problems.append(f"line {n} ({cid}): missing or invalid {', '.join(bad)}")
            continue
        for k in ("evidence", "rationale", "charitable_reading"):
            if obj.get(k) is not None and not isinstance(obj[k], str):
                obj[k] = json.dumps(obj[k])  # free text; keep it, but as text the report can escape and match
        if cid in seen:
            problems.append(f"line {n} ({cid}): labelled more than once; the last line wins")
        seen.add(cid)
        problems += [f"line {n} ({cid}): {p}" for p in label_problems(obj, bodies[cid], pr_ids[cid])]
        labels[cid] = obj
    targets = set(bodies)
    missing = targets - labels.keys()
    if missing:
        problems.append(f"{len(missing)} target comments have no label: {', '.join(sorted(missing)[:10])}"
                        + (" ..." if len(missing) > 10 else ""))
    return labels, notes, problems


def open_file(path: Path) -> None:
    opener = {"Darwin": ["open"], "Windows": ["cmd", "/c", "start", ""]}.get(platform.system(), ["xdg-open"])
    try:
        subprocess.Popen([*opener, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def cmd_report(args: argparse.Namespace) -> str:
    from report_html import render_report  # noqa: PLC0415 - sibling module, only needed here

    run = load_run(args.run)
    saved_path = run_dir(args.run) / "labels.json"
    saved = json.loads(saved_path.read_text()) if args.merge and saved_path.exists() else None
    labels, notes, problems = parse_labels(sys.stdin.read().splitlines(), run, saved)
    d = run_dir(args.run)
    _private_mkdir(d)
    _private_write(d / "labels.json", json.dumps({"labels": labels, "notes": notes}))
    out = d / "report.html"
    _private_write(out, render_report(run, labels, notes))
    if args.open:
        open_file(out)
    lines = [f"report: {out}", f"url: {out.as_uri()}", f"labelled {len(labels)} comments"]
    lines += [f"WARNING {p}" for p in problems]
    return "\n".join(lines) + "\n"


def cmd_show(args: argparse.Namespace) -> str:
    """Print the full PR thread around one comment, with any saved labels, for digging deeper."""
    run = load_run(args.run)
    saved = run_dir(args.run) / "labels.json"
    labels = json.loads(saved.read_text())["labels"] if saved.exists() else {}
    for item in run["prs"].values():
        ids = [c["id"] for c in item["comments"]]
        if args.id in ids:
            comments = [{**c, "target": c["id"] == args.id} for c in item["comments"]]
            out = [render_pr(item["pr"], comments)]
            if args.id in labels:
                out.append("# saved label: " + json.dumps(labels[args.id]))
            related = [c for c in item["comments"] if c["id"] in labels and c["id"] != args.id]
            for c in related:
                out.append(f"# other label in this PR: {c['id']} by {c['author']}: {labels[c['id']]['tone']}")
            return "\n".join(out) + "\n"
    sys.exit(f"comment {args.id!r} not found in run {args.run}")


def cmd_runs(_: argparse.Namespace) -> str:
    home = reports_home()
    rows = []
    for d in sorted(home.glob("*/threads.json"), reverse=True):
        run = json.loads(d.read_text())
        has = "report" if (d.parent / "report.html").exists() else "no report yet"
        scope = run["scope"]
        who = ", ".join(scope["repos"] + [f"org:{o}" for o in scope["orgs"]]) or "-"
        people = ", ".join(scope["authors"]) or "everyone"
        rows.append(f"{run['run']}  {run['window']['start']}..{run['window']['end']}  {who}  [{people}]  {has}")
    return "\n".join(rows or [f"no runs in {home}"]) + "\n"


# ---------------------------------------------------------------- commands


def _day(s: str) -> datetime:
    d = date.fromisoformat(s)  # YYYY-MM-DD only: a time or offset here would silently shift the window
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


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
    if args.offset < 0 or args.limit < 1:
        sys.exit("--offset must be 0 or more and --limit at least 1")
    ensure_untracked(reports_home())  # fail before any GitHub calls, not after

    run = existing_run(args)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if run:  # a later page of an existing run keeps its window, even if the date has changed since
        start = _day(run["window"]["start"])
        end = _day(run["window"]["end"]) + timedelta(days=1)
    elif args.pr and not args.since:
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)
    else:
        start = args.since or today - timedelta(days=7)
    if not run:
        end = args.until or today + timedelta(days=1)
    if end <= start:
        sys.exit("--until must be after --since (--until is the first day NOT included)")
    authors = {a.lower() for a in args.author}

    capped = bool(run and run.get("search_capped"))
    if run and "pr_list" in run:
        prs = run["pr_list"]
    elif args.pr:
        prs = [get_pr(get, args.repo[0], n) for n in args.pr]
    elif args.repo and not args.org:
        # Listing each repo's PRs directly avoids search-index lag and the 1000-result cap.
        prs = sorted((p for r in args.repo for p in list_repo_prs(get, r, start)),
                     key=lambda p: p["updated_at"], reverse=True)
    else:
        scope = [f"repo:{r}" for r in args.repo] + [f"org:{o}" for o in args.org]
        prs, capped = search_prs(get, scope, args.author, start.date().isoformat())
    total = len(prs)
    window = prs[args.offset: args.offset + args.limit]

    skipped: Counter = Counter()
    blocks, targets, fetched = [], 0, []
    for pr in window:
        comments = pr_comments(get, pr["repo"], pr["number"])
        n = mark_targets(comments, start, end, authors, skipped)
        if n:
            targets += n
            blocks.append(render_pr(pr, comments, budget=MAX_CONTEXT_PER_PR))
            fetched.append({"pr": pr, "comments": comments})

    run_id = save_fetch(args, start, end, fetched, prs, run, capped)
    shown_to = args.offset + len(window)
    head = [
        f"# run: {run_id}",
        f"# window: {start.date()} to {(end - timedelta(days=1)).date()} (UTC, inclusive)",
        f"# authors: {', '.join(args.author) or 'everyone'}",
        f"# PRs {args.offset + 1 if window else 0}-{shown_to} of {total}; "
        f"{len(blocks)} with comments to label; {targets} target comments",
        f"# skipped before labelling: {dict(skipped) or 'none'}",
    ]
    if shown_to < total:
        head.append(f"# MORE: run the same command again with --offset {shown_to} --run {run_id} "
                    f"for the next {args.limit} PRs")
    if capped:
        head.append(f"# WARNING: GitHub search returns at most {SEARCH_CAP} PRs per query and some were left out; "
                    "split the date range into smaller runs, or use --repo")
    if any("<omitted " in b for b in blocks):
        head.append("# NOTE: some long threads are shortened (<omitted comments=\"n\"/>); "
                    "use `show --run <run> --id <comment-id>` to read one in full")
    return "\n".join(head) + "\n\n" + "\n\n".join(blocks) + "\n"


def load_cases() -> list[dict]:
    return [json.loads(l) for l in EVAL_FILE.read_text().splitlines() if l.strip()]


CASE_KINDS = {"issue_comment": "comment", "review_comment": "inline"}


def _case_comment(c: dict) -> dict:
    """An eval case comment in the same shape `fetch` prints, so calibration looks like the real thing."""
    kind = c.get("kind", "comment")
    return {**c, "kind": CASE_KINDS.get(kind, kind), "file": c.get("path"),
            "thread": c.get("thread_id", "conversation")}


def cmd_calibrate(_: argparse.Namespace) -> str:
    out = []
    for i, row in enumerate(load_cases(), 1):
        inp = row["input"]
        comments = [_case_comment(c) for c in inp["prior_comments"]] + [{**_case_comment(inp["target"]), "target": True}]
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
    f.add_argument("--run", help="add this page to an existing run instead of starting a new one")
    r = sub.add_parser("report", help="build the HTML report from labels on stdin")
    r.add_argument("--run", required=True)
    r.add_argument("--open", action="store_true", help="open the report in the default browser")
    r.add_argument("--merge", action="store_true",
                   help="keep this run's saved labels and notes; lines on stdin add to or replace them")
    sh = sub.add_parser("show", help="print the full thread around one comment")
    sh.add_argument("--run", required=True)
    sh.add_argument("--id", required=True)
    sub.add_parser("runs", help="list saved runs")
    sub.add_parser("calibrate", help="print eval cases without answers")
    sub.add_parser("score", help="score answers read from stdin")
    args = p.parse_args(argv)
    run = {"fetch": cmd_fetch, "report": cmd_report, "show": cmd_show, "runs": cmd_runs,
           "calibrate": cmd_calibrate, "score": cmd_score}[args.cmd]
    sys.stdout.write(run(args))


if __name__ == "__main__":
    main()
