#!/usr/bin/env python3
"""Helper for the pr-tone skill. Read-only towards GitHub; writes only to the local reports folder.

Every GitHub call is `gh api --method GET` on a fixed set of endpoints. The
only files written are under $PR_TONE_HOME (default ~/pr-tone-reports), which
must not be inside a git working tree unless git ignores it.

    prtone.py fetch --repo owner/name [--author login ...] [--since YYYY-MM-DD] [--until YYYY-MM-DD]
    prtone.py fetch --org acme --author alice --author bob --since 2026-10-01
    prtone.py fetch --repo acme/api --team acme/platform --since 2026-10-01
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
import copy
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Lock
from typing import Callable, Iterator
from urllib.parse import quote

from local_store import RunBusy, Store, run_lock

PER_PAGE = 100
MAX_CONTEXT_CHARS = 1500  # non-target comments are context; long ones are trimmed
MAX_TARGET_CHARS = 8000
MAX_HUNK_LINES = 15
MAX_CONTEXT_PER_PR = 30000  # chars of context per PR in fetch output; `show` prints everything
SEARCH_CAP = 1000  # GitHub search returns at most this many results per query
CACHE_HOURS = 24
DEFAULT_BUDGET = 100
WORKERS = 4
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


class GitHubError(RuntimeError):
    def __init__(self, message: str, fatal: bool = False) -> None:
        super().__init__(message)
        self.fatal = fatal


def gh_get(path: str) -> str:
    """The only way this script talks to GitHub: an HTTP GET through the gh CLI."""
    try:
        proc = subprocess.run(["gh", "api", "--method", "GET", path], capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise GitHubError("GitHub CLI not found; install gh and run gh auth login", fatal=True) from exc
    if proc.returncode != 0:
        error = proc.stderr.strip()
        auth = "401" in error or "authentication" in error.lower() or "gh auth login" in error.lower()
        rate = "rate limit" in error.lower() or "429" in error
        hint = (" Authentication failed; run gh auth login." if auth else
                " Rate limited; resume this run later." if rate else
                " GitHub cannot distinguish a missing repository from one you cannot access." if "404" in error else "")
        raise GitHubError(f"gh api GET {path} failed: {error}{hint}", fatal=auth or rate)
    return proc.stdout


class FetchClient:
    def __init__(self, get: Runner, repos: list[str], orgs: list[str]) -> None:
        self.runner, self.repos, self.orgs = get, repos, orgs
        self.requests = 0
        self.checked = False
        self.lock = Lock()
        self.stopped = Event()

    def request(self, path: str) -> str:
        if self.stopped.is_set():
            raise GitHubError("fetch stopped after an authentication or rate-limit failure", fatal=True)
        with self.lock:
            self.requests += 1
        try:
            return self.runner(path)
        except GitHubError as exc:
            if exc.fatal:
                self.stopped.set()
            raise

    def get(self, path: str) -> str:
        # Preflight is lazy: fully cached reports work without network access.
        with self.lock:
            checked = self.checked
        if not checked:
            raise RuntimeError("GitHub access must be checked before starting fetch workers")
        return self.request(path)

    def preflight(self) -> None:
        if self.checked:
            return
        self.request("user")
        for repo in self.repos:
            self.request(f"repos/{repo}")
        for org in self.orgs:
            self.request(f"orgs/{org}")
        self.checked = True


def pages(get: Runner, path: str, params: str = "", key: str | None = None,
          max_pages: int | None = None, meta: dict | None = None, per_page: int = PER_PAGE) -> Iterator[dict]:
    """Yield items page by page. With `key`, the response is an object (search) and `meta` gets its other fields."""
    page = 1
    while True:
        sep = "&" if params else ""
        data = json.loads(get(f"{path}?{params}{sep}per_page={per_page}&page={page}"))
        items = data[key] if key else data
        if meta is not None and key:
            meta.update({k: v for k, v in data.items() if k != key})
        yield from items
        if len(items) < per_page or (max_pages and page >= max_pages):
            return
        page += 1


def search_prs(get: Runner, scope: list[str], authors: list[str], since: str,
               budget: int | None = None, pr_authors: list[str] | None = None) -> tuple[list[dict], bool]:
    """PRs updated since `since`, selected by commenters or explicit PR authors. Newest first.

    Also returns whether any query hit the search API's 1000-result cap (asking for page 11 is an error).
    """
    base = " ".join([f"is:pr updated:>={since}", *scope])
    if pr_authors is not None:
        queries = [f"{base} author:{a}" for a in pr_authors]
    else:
        queries = [f"{base} {q}:{a}" for a in authors for q in ("involves", "reviewed-by")] or [base]
    found: dict[str, dict] = {}
    capped = False
    for q in queries:
        meta: dict = {}
        count = 0
        for item in pages(get, "search/issues", f"q={quote(q)}&sort=updated&order=desc", key="items",
                          max_pages=SEARCH_CAP // min(PER_PAGE, budget or PER_PAGE), meta=meta,
                          per_page=min(PER_PAGE, budget or PER_PAGE)):
            repo = item["repository_url"].split("/repos/", 1)[1]
            found[f"{repo}#{item['number']}"] = {
                "repo": repo,
                "number": item["number"],
                "title": item["title"],
                "author": (item.get("user") or {}).get("login", "ghost"),
                "url": item["html_url"],
                "updated_at": item["updated_at"],
            }
            count += 1
            if budget is not None and count >= budget:
                break
        capped = capped or (budget is not None and count >= budget)
        capped = capped or meta.get("total_count", 0) > SEARCH_CAP or bool(meta.get("incomplete_results"))
    return sorted(found.values(), key=lambda p: p["updated_at"], reverse=True), capped


def team_members(team: str, client: FetchClient, store: Store, refresh: bool) -> tuple[list[str], str, bool]:
    key = _cache_key(team.lower())
    cached = None if refresh else store.get("team", key, CACHE_HOURS)
    if cached:
        return cached.data["members"], cached.fetched_at, True
    client.preflight()
    org, slug = team.split("/")
    try:
        members = sorted({member["login"].lower()
                          for member in pages(client.get, f"orgs/{org}/teams/{slug}/members")})
    except GitHubError as exc:
        raise GitHubError(f"Cannot read team {team!r}: confirm the team exists and gh has access to its "
                          f"organization/team membership (including any required SSO authorization). {exc}",
                          fatal=exc.fatal) from exc
    stamp = store.put("team", key, {"members": members})
    return members, stamp, False


def list_repo_prs(get: Runner, repo: str, since: datetime, budget: int | None = None) -> list[dict]:
    """PRs in one repo updated at or after `since`, via the repo's own list endpoint (stops early)."""
    out = []
    for pr in pages(get, f"repos/{repo}/pulls", "state=all&sort=updated&direction=desc",
                    per_page=min(PER_PAGE, budget or PER_PAGE)):
        if _ts(pr["updated_at"]) < since:
            break
        out.append({"repo": repo, "number": pr["number"], "title": pr["title"],
                    "author": (pr.get("user") or {}).get("login", "ghost"),
                    "url": pr["html_url"], "updated_at": pr["updated_at"]})
        if budget is not None and len(out) >= budget:
            break
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


def mark_targets(comments: list[dict], start: datetime, end: datetime, authors: set[str], skipped: Counter,
                 windows: list[dict] | None = None) -> int:
    """Set c["target"] on comments to label; returns how many.

    The window is about when a comment was posted. An old comment edited inside the window is not a target,
    and a comment posted inside it but edited later still is (it is labelled as it reads now, marked edited).
    """
    n = 0
    for c in comments:
        ts = _ts(c["created_at"])
        c["target"] = False
        c.pop("skip", None)
        if not (start <= ts < end) or (authors and c["author"].lower() not in authors):
            continue
        c["windows"] = [w["name"] for w in windows or []
                        if _day(w["start"]) <= ts < _day(w["end"]) + timedelta(days=1)]
        if windows and not c["windows"]:
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


OUR_TAGS_RE = re.compile(r"<(\s*/?\s*(?:comment|pr|case|diff_hunk|omitted|saved_label)\b)", re.IGNORECASE)


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
    context = [i for i in shown if not (comments[i].get("target") or comments[i].get("label_reused"))]
    if budget is None:
        return set(context)
    targets = [i for i in shown if comments[i].get("target") or comments[i].get("label_reused")]
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


def render_pr(pr: dict, comments: list[dict], budget: int | None = None, labels: dict | None = None) -> str:
    lines = [f'<pr repo="{pr["repo"]}" number="{pr["number"]}" author="{_attr(pr["author"])}" '
             f'url="{pr["url"]}" title="{_text(_attr(pr["title"]))}">']
    keep = _context_to_show(comments, budget)
    omitted = 0
    for i, c in enumerate(comments):
        if not c["body"].strip():
            continue
        if not (c.get("target") or c.get("label_reused")) and i not in keep:
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
        elif c.get("label_reused"):
            attrs += ['labelled="yes"', f'url="{c["url"]}"']
        body = c["body"].strip()
        limit = MAX_TARGET_CHARS if c.get("target") or c.get("label_reused") else MAX_CONTEXT_CHARS
        if len(body) > limit:
            body = body[:limit] + " …[trimmed]"
        lines.append(f"<comment {' '.join(attrs)}>")
        if (c.get("target") or c.get("label_reused")) and c.get("diff_hunk"):
            lines.append(f"<diff_hunk>\n{_text(c['diff_hunk'])}\n</diff_hunk>")
        lines.append(_text(body))
        if c.get("label_reused") and labels and c["id"] in labels:
            lines.append(f"<saved_label>{_text(json.dumps(labels[c['id']]))}</saved_label>")
        lines.append("</comment>")
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
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
            os.chmod(temporary, 0o600)
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def new_run_id(args: argparse.Namespace) -> str:
    bits = [r.split("/")[1] for r in args.repo] + args.org + args.author + [f"pr{n}" for n in args.pr or []]
    if args.team:
        bits.append(args.team)
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
    scope = {"repos": args.repo, "orgs": args.org, "authors": args.author, "prs": args.pr or []}
    if args.team:
        scope["team"] = args.team
    return scope


def _window(start: datetime, end: datetime) -> dict:
    return {"start": start.date().isoformat(), "end": (end - timedelta(days=1)).date().isoformat()}


def _same_scope(a: dict, b: dict) -> bool:
    def norm(s: dict) -> tuple:
        return (sorted(r.lower() for r in s["repos"]), sorted(o.lower() for o in s["orgs"]),
                sorted(x.lower() for x in s["authors"]), sorted(s["prs"]), (s.get("team") or "").lower())
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


def _pr_key(pr: dict) -> str:
    return f"{pr['repo']}#{pr['number']}"


def _cache_key(value: object) -> str:
    host = os.environ.get("GH_HOST", "github.com").lower()
    return hashlib.sha256(json.dumps([host, value], sort_keys=True).encode()).hexdigest()


def _rubric_version() -> str:
    skill = Path(__file__).resolve().parent.parent
    return hashlib.sha256(b"label-schema-1\0" + (skill / "rubric.md").read_bytes()
                          + (skill / "SKILL.md").read_bytes()).hexdigest()


def _import_saved_threads(store: Store) -> None:
    """Seed a new cache from saved complete threads, without trusting old label provenance."""
    migration = _cache_key("saved-threads-v1")
    if store.get("migration", migration):
        return
    host = os.environ.get("GH_HOST", "github.com").lower()
    for path in sorted(reports_home().glob("*/threads.json")):
        try:
            run = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"WARNING: could not import saved evidence from {path}: {exc}\n")
            continue
        if run.get("host", "github.com") != host:
            continue
        for item in run.get("prs", {}).values():
            stamp = item.get("fetched_at", run["created"])
            key = _cache_key(_pr_key(item["pr"]))
            existing = store.get("thread", key)
            if existing is not None and _ts(existing.fetched_at) >= _ts(stamp):
                continue
            raw = {"pr": item["pr"], "comments": [
                {k: v for k, v in c.items() if k not in ("target", "skip", "windows")} for c in item["comments"]
            ]}
            store.put("thread", key, raw, stamp)
    store.put("migration", migration, {})


def _fingerprint(item: dict, version: str) -> str:
    comments = [{k: v for k, v in c.items() if k not in ("target", "skip", "windows")} for c in item["comments"]]
    return _cache_key([version, item["pr"], comments])


def _valid_label(label: dict, comment: dict, comments: list[dict]) -> bool:
    return (all(label.get(k) in values for k, values in LABEL_FIELDS.items())
            and not label_problems(label, comment["body"], {c["id"] for c in comments} - {comment["id"]}))


def _reuse_labels(run: dict, store: Store, saved: dict, version: str) -> dict:
    labels, fingerprints = {}, {}
    for item in run["prs"].values():
        fingerprint = _fingerprint(item, version)
        for comment in item["comments"]:
            if not comment.get("target"):
                continue
            cid = comment["id"]
            fingerprints[cid] = fingerprint
            label = None
            if saved.get("fingerprints", {}).get(cid) == fingerprint:
                label = saved.get("labels", {}).get(cid)
            if label is None:
                cached = store.get("label", _cache_key([cid, fingerprint]))
                label = cached.data if cached else None
            if label is not None and _valid_label(label, comment, item["comments"]):
                labels[cid] = label
    run["fingerprints"] = fingerprints
    return {"labels": labels, "notes": saved.get("notes", []), "fingerprints": fingerprints}


def _checkpoint(run: dict, labels: dict, client: FetchClient, initial_requests: int) -> None:
    # Preserve candidate order even when worker completion order differs.
    run["prs"] = {_pr_key(p): run["prs"][_pr_key(p)] for p in run.get("pr_list", [])
                  if _pr_key(p) in run["prs"]}
    run["stats"]["api_requests"] = initial_requests + client.requests
    run["reused_ids"] = list(labels["labels"])
    run["partial"] = bool(run["discovery_partial"] or run["errors"]
                          or len(run["prs"]) < len(run.get("pr_list", [])))
    d = run_dir(run["run"])
    _private_write(d / "threads.json", json.dumps(run))
    _private_write(d / "labels.json", json.dumps(labels))


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


def _report_locked(args: argparse.Namespace, store: Store) -> str:
    from report_html import render_report  # noqa: PLC0415 - sibling module, only needed here

    run = load_run(args.run)
    saved_path = run_dir(args.run) / "labels.json"
    saved = json.loads(saved_path.read_text()) if saved_path.exists() else {}
    if not args.merge:
        saved = {"labels": {cid: lab for cid, lab in saved.get("labels", {}).items()
                            if cid in run.get("reused_ids", [])},
                 "fingerprints": saved.get("fingerprints", {})}
    version = _rubric_version()
    fingerprints = {c["id"]: _fingerprint(item, version) for item in run["prs"].values()
                    for c in item["comments"] if c.get("target")}
    if saved.get("fingerprints"):
        saved["labels"] = {cid: lab for cid, lab in saved.get("labels", {}).items()
                           if saved["fingerprints"].get(cid) == fingerprints.get(cid)}
    labels, notes, problems = parse_labels(sys.stdin.read().splitlines(), run, saved)
    d = run_dir(args.run)
    _private_mkdir(d)
    _private_write(d / "labels.json", json.dumps({"labels": labels, "notes": notes, "fingerprints": fingerprints}))
    for item in run["prs"].values():
        for comment in item["comments"]:
            cid = comment["id"]
            if comment.get("target") and cid in labels and _valid_label(labels[cid], comment, item["comments"]):
                store.put("label", _cache_key([cid, fingerprints[cid]]), labels[cid])
    out = d / "report.html"
    _private_write(out, render_report(run, labels, notes))
    if args.open:
        open_file(out)
    lines = [f"report: {out}", f"url: {out.as_uri()}", f"labelled {len(labels)} comments"]
    lines += [f"WARNING {p}" for p in problems]
    return "\n".join(lines) + "\n"


def cmd_report(args: argparse.Namespace) -> str:
    load_run(args.run)
    ensure_untracked(reports_home())
    try:
        with run_lock(run_dir(args.run)), closing(Store(reports_home())) as store:
            return _report_locked(args, store)
    except RunBusy as exc:
        sys.exit(str(exc))


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
        if scope.get("team"):
            who += f" · PR author team:{scope['team']}"
        people = ", ".join(scope["authors"]) or "everyone"
        rows.append(f"{run['run']}  {run['window']['start']}..{run['window']['end']}  {who}  [{people}]  {has}")
    return "\n".join(rows or [f"no runs in {home}"]) + "\n"


# ---------------------------------------------------------------- commands


def _day(s: str) -> datetime:
    d = date.fromisoformat(s)  # YYYY-MM-DD only: a time or offset here would silently shift the window
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _named_window(value: str) -> dict:
    try:
        name, since, until = value.split(":")
        start, end = _day(since), _day(until)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected NAME:YYYY-MM-DD:YYYY-MM-DD (end exclusive)") from exc
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name) or end <= start:
        raise argparse.ArgumentTypeError("window needs a simple unique name and an end after its start")
    return {"name": name, **_window(start, end)}


def _current_repo() -> str | None:
    try:
        proc = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    if proc.returncode:
        return None
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([^/\s]+/[^/\s]+?)(?:\.git)?/?",
                         proc.stdout.strip())
    return match[1] if match else None


def _fetch_setup(args: argparse.Namespace) -> tuple[dict | None, datetime, datetime, list[dict]]:
    for name, value in (("budget", None), ("all", None), ("exhaustive", None), ("refresh", None),
                        ("window", []), ("team", None)):
        if not hasattr(args, name):
            setattr(args, name, value)
    if args.run:
        old = load_run(args.run)
        if "config" not in old:
            sys.exit("this legacy run has no saved candidate budget; use report/show, or start a new fetch. "
                     "Its existing files have not been changed.")
        if old.get("host", "github.com") != os.environ.get("GH_HOST", "github.com").lower():
            sys.exit("this run belongs to a different GitHub host; restore GH_HOST or start a new run")
        if not (args.repo or args.org or args.author or args.pr or args.team):
            args.repo, args.org = old["scope"]["repos"], old["scope"]["orgs"]
            args.author, args.pr = old["scope"]["authors"], old["scope"]["prs"] or None
            args.team = old["scope"].get("team")
    elif not (args.repo or args.org):
        if args.team:
            args.org = [args.team.split("/", 1)[0]]
        else:
            inferred = _current_repo()
            if inferred:
                args.repo = [inferred]
    if args.team and not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_-]+", args.team):
        sys.exit(f"bad --team {args.team!r}; expected organization/team-slug")
    for r in args.repo:
        if not REPO_RE.match(r):
            sys.exit(f"bad --repo {r!r}; expected owner/name")
    for n in args.org + args.author:
        if not NAME_RE.match(n):
            sys.exit(f"bad GitHub name {n!r}")
    if args.pr and len(args.repo) != 1:
        sys.exit("--pr needs exactly one --repo")
    if args.pr and any(number < 1 for number in args.pr):
        sys.exit("--pr numbers must be positive")
    if not (args.repo or args.org or args.author):
        sys.exit("give at least one of --repo, --org or --author")
    if args.offset < 0 or args.limit < 1:
        sys.exit("--offset must be 0 or more and --limit at least 1")
    if args.budget is not None and args.budget < 1:
        sys.exit("--budget must be at least 1")
    if args.all and args.budget is not None:
        sys.exit("choose either --all or --budget")
    if args.window and (args.since or args.until):
        sys.exit("use --window or --since/--until, not both")
    if len({w["name"] for w in args.window}) != len(args.window):
        sys.exit("--window names must be unique")
    ensure_untracked(reports_home())  # fail before any GitHub calls, not after

    run = existing_run(args)
    config = (run or {}).get("config", {})
    for name, default in (("budget", DEFAULT_BUDGET), ("all", False), ("exhaustive", False), ("refresh", False)):
        requested = getattr(args, name)
        stored = config.get(name, default)
        if run and requested is not None and requested != stored:
            sys.exit(f"run {args.run} has a different {name}; keep the original configuration or start a new run")
        setattr(args, name, stored if requested is None else requested)
    if args.all:
        args.budget = None
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if run:
        start = _day(run["window"]["start"])
        end = _day(run["window"]["end"]) + timedelta(days=1)
        windows = run.get("windows", [{"name": "requested", **run["window"]}])
        if args.window and args.window != windows:
            sys.exit(f"run {args.run} has different windows; repeat the original windows or omit --window")
    elif args.window:
        windows = args.window
        start = min(_day(w["start"]) for w in windows)
        end = max(_day(w["end"]) for w in windows) + timedelta(days=1)
    elif args.pr and not args.since:
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)
        end = args.until or today + timedelta(days=1)
        windows = [{"name": "requested", **_window(start, end)}]
    else:
        start = args.since or today - timedelta(days=7)
        end = args.until or today + timedelta(days=1)
        windows = [{"name": "requested", **_window(start, end)}]
    if end <= start:
        sys.exit("--until must be after --since (--until is the first day NOT included)")
    return run, start, end, windows


def _discover(args: argparse.Namespace, start: datetime, client: FetchClient, store: Store,
              pr_authors: list[str] | None = None) -> tuple[dict, str, bool]:
    scope = {k: values.lower() if k == "team" else
             sorted({v.lower() for v in values}) if k != "prs" else sorted(set(values))
             for k, values in _scope(args).items()}
    if args.pr or args.team:
        scope["authors"] = []
    if args.pr:
        scope["prs"] = list(dict.fromkeys(args.pr))
    identity = [scope, None if args.pr else start.date().isoformat(), args.exhaustive, args.budget]
    if pr_authors is not None:
        identity.append(pr_authors)
    key = _cache_key(identity)
    cached = None if args.refresh else store.get("discovery", key, CACHE_HOURS)
    if cached:
        return cached.data, cached.fetched_at, True
    partial = False
    stamps = []
    search = not args.pr and (args.team or args.org or not args.repo or (args.author and not args.exhaustive))
    if pr_authors == []:
        prs = []
    elif args.pr:
        numbers = list(dict.fromkeys(args.pr))
        partial = args.budget is not None and len(numbers) > args.budget
        prs = []
        for number in numbers[:args.budget]:
            cached_pr = None if args.refresh else store.get("thread", _cache_key(f"{args.repo[0]}#{number}"),
                                                           CACHE_HOURS)
            if cached_pr:
                prs.append(cached_pr.data["pr"])
                stamps.append(cached_pr.fetched_at)
            else:
                client.preflight()
                prs.append(get_pr(client.get, args.repo[0], number))
    elif search:
        client.preflight()
        qualifiers = [f"repo:{r}" for r in args.repo] + [f"org:{o}" for o in args.org]
        prs, partial = search_prs(client.get, qualifiers, [] if args.exhaustive else args.author,
                                  start.date().isoformat(), args.budget, pr_authors)
    else:
        client.preflight()
        prs = []
        for repo in args.repo:
            found = list_repo_prs(client.get, repo, start, args.budget)
            partial = partial or (args.budget is not None and len(found) >= args.budget)
            prs.extend(found)
    if pr_authors is not None:
        members = set(pr_authors)
        prs = [pr for pr in prs if pr["author"].lower() in members]
    prs = sorted({_pr_key(p): p for p in prs}.values(), key=lambda p: (p["updated_at"], _pr_key(p)), reverse=True)
    if args.budget is not None and len(prs) > args.budget:
        partial = True
    data = {"prs": prs[:args.budget], "partial": bool(partial or search), "search": bool(search),
            "truncated": partial}
    return data, store.put("discovery", key, data, min(stamps) if stamps else None), False


def _fetch_locked(args: argparse.Namespace, run: dict | None, start: datetime, end: datetime,
                  windows: list[dict], get: Runner, store: Store) -> str:
    client = FetchClient(get, args.repo, args.org)
    run = run or {
        "run": args.run, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": _scope(args), "window": _window(start, end), "prs": {},
        "host": os.environ.get("GH_HOST", "github.com").lower(),
    }
    run.setdefault("windows", windows)
    run.setdefault("config", {k: getattr(args, k) for k in ("budget", "all", "exhaustive", "refresh")})
    run.setdefault("errors", {})
    run.setdefault("stats", {"api_requests": 0, "thread_cache_hits": 0, "discovery_cache_hits": 0})
    if args.team:
        run["stats"].setdefault("team_cache_hits", 0)
    run.setdefault("discovery_partial", bool(run.get("search_capped")))
    initial_requests = run["stats"]["api_requests"]
    saved_path = run_dir(args.run) / "labels.json"
    saved = json.loads(saved_path.read_text()) if saved_path.exists() else {}
    version = _rubric_version()
    labels = _reuse_labels(run, store, saved, version)

    def checkpoint() -> None:
        _checkpoint(run, labels, client, initial_requests)

    if "pr_list" not in run:
        checkpoint()
        try:
            if args.team and "team_snapshot" not in run:
                members, stamp, hit = team_members(args.team, client, store, args.refresh)
                run["team_snapshot"] = {"team": args.team, "members": members, "fetched_at": stamp}
                run["stats"]["team_cache_hits"] += int(hit)
                checkpoint()
            pr_authors = run["team_snapshot"]["members"] if args.team else None
            discovery, stamp, hit = _discover(args, start, client, store, pr_authors)
        except GitHubError as exc:
            run["errors"]["discovery"] = str(exc)
            checkpoint()
            sys.exit(f"{exc}\nRun {args.run} saved; resume with fetch --run {args.run}")
        run["pr_list"] = discovery["prs"]
        run["discovery_partial"] = discovery["partial"]
        run["search_capped"] = discovery["truncated"]
        run["search_used"] = discovery["search"]
        run["discovered_at"] = stamp
        run["stats"]["discovery_cache_hits"] += int(hit)
        run["errors"].pop("discovery", None)
    checkpoint()

    authors = {a.lower() for a in args.author}
    selected = [p for p in run["pr_list"][args.offset:] if _pr_key(p) not in run["prs"]][:args.limit]
    pending = []

    def accept(pr: dict, raw: dict, stamp: str, hit: bool) -> None:
        nonlocal labels
        item = copy.deepcopy(raw)
        item["fetched_at"] = stamp
        mark_targets(item["comments"], start, end, authors, Counter(), windows)
        run["prs"][_pr_key(pr)] = item
        run["errors"].pop(_pr_key(pr), None)
        run["stats"]["thread_cache_hits"] += int(hit)
        labels = _reuse_labels(run, store, labels, version)
        checkpoint()

    for pr in selected:
        key = _cache_key(_pr_key(pr))
        cached = None if args.refresh else store.get("thread", key, CACHE_HOURS)
        if cached and _ts(cached.data["pr"]["updated_at"]) >= _ts(pr["updated_at"]):
            accept(pr, cached.data, cached.fetched_at, True)
        else:
            pending.append(pr)

    fatal = None
    if pending:
        try:
            client.preflight()
        except GitHubError as exc:
            run["errors"]["access"] = str(exc)
            checkpoint()
            sys.exit(f"{exc}\nRun {args.run} saved; resume with fetch --run {args.run}")
        run["errors"].pop("access", None)
        iterator = iter(pending)
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            active = {}

            def schedule() -> None:
                while len(active) < WORKERS and not client.stopped.is_set():
                    pr = next(iterator, None)
                    if pr is None:
                        return
                    active[pool.submit(pr_comments, client.get, pr["repo"], pr["number"])] = pr

            try:
                schedule()
                while active:
                    done, _ = wait(active, return_when=FIRST_COMPLETED)
                    for future in done:
                        pr = active.pop(future)
                        try:
                            comments = future.result()
                        except GitHubError as exc:
                            run["errors"][_pr_key(pr)] = str(exc)
                            if exc.fatal:
                                fatal = str(exc)
                                client.stopped.set()
                            checkpoint()
                        else:
                            raw = {"pr": pr, "comments": comments}
                            stamp = store.put("thread", _cache_key(_pr_key(pr)), raw)
                            accept(pr, raw, stamp, False)
                    schedule()
            except KeyboardInterrupt:
                client.stopped.set()
                checkpoint()
                raise
    if len(run["prs"]) == len(run["pr_list"]):
        run["errors"].pop("access", None)
    checkpoint()
    if fatal:
        sys.exit(f"{fatal}\nProgress saved in run {args.run}; resume with fetch --run {args.run}")

    blocks, targets, needs_label_prs, reused = [], 0, 0, len(labels["labels"])
    skipped: Counter = Counter()
    for item in run["prs"].values():
        skipped.update(c["skip"] for c in item["comments"] if c.get("skip"))
        comments = copy.deepcopy(item["comments"])
        for c in comments:
            if c["id"] in labels["labels"]:
                c["target"] = False
                c["label_reused"] = True
        targets += sum(bool(c.get("target")) for c in comments)
        if any(c.get("target") for c in comments):
            needs_label_prs += 1
        if any(c.get("target") or c.get("label_reused") for c in comments):
            blocks.append(render_pr(item["pr"], comments, budget=MAX_CONTEXT_PER_PR, labels=labels["labels"]))
    remaining = [i for i, p in enumerate(run["pr_list"])
                 if _pr_key(p) not in run["prs"] and _pr_key(p) not in run["errors"]]
    done_count, total = len(run["prs"]), len(run["pr_list"])
    examined = len(set(run["prs"]) | ({_pr_key(p) for p in run["pr_list"]} & run["errors"].keys()))
    head = [
        f"# run: {args.run}",
        f"# window: {start.date()} to {(end - timedelta(days=1)).date()} (UTC, inclusive)",
        f"# windows: {json.dumps(windows)}",
        f"# authors: {', '.join(args.author) or 'everyone'}",
        f"# PRs {1 if done_count else 0}-{done_count} of {total} selected; "
        f"{needs_label_prs} with comments to label; {targets} target comments; {reused} labels reused",
        f"# candidates examined: {examined}; complete PR threads: {done_count}; "
        f"selected candidates not yet attempted: {len(remaining)}",
        f"# budget: {args.budget if args.budget is not None else 'all explicitly requested'} unique PR candidates "
        "(including cache hits and PRs without eligible comments)",
        f"# coverage: {'PARTIAL' if run['partial'] else 'complete within stated discovery scope'}; "
        "newest first among discovered candidates; no estimate of total matching activity",
        f"# API requests: {run['stats']['api_requests']}; thread cache hits: {run['stats']['thread_cache_hits']}; "
        f"discovery cache hits: {run['stats']['discovery_cache_hits']}",
        f"# discovery fetched at: {run.get('discovered_at', 'legacy run')}; cache freshness: {CACHE_HOURS} hours; "
        "saved evidence may omit subsequent comments, edits or deletions",
        f"# skipped before labelling: {dict(skipped) or 'none'}",
    ]
    stamps = [it["fetched_at"] for it in run["prs"].values() if it.get("fetched_at")]
    if args.team:
        snapshot = run["team_snapshot"]
        head.insert(4, f"# PR author team: {args.team}; {len(snapshot['members'])} current members; "
                    f"roster fetched at: {snapshot['fetched_at']}; "
                    "historical membership is not inferred")
        head.append(f"# team membership cache hits: {run['stats']['team_cache_hits']}")
        if not snapshot["members"]:
            head.append("# NOTE: the current team roster is empty; no PR candidates were selected")
    if stamps:
        head.append(f"# threads fetched at: {min(stamps)} to {max(stamps)}")
    if reused:
        head.append('# NOTE: labelled="yes" comments and saved_label blocks are reused evidence for summaries; '
                    'only remaining target comments need labelling')
    if run.get("search_used"):
        head.append("# WARNING: search-index discovery is non-exhaustive; missing results do not establish no activity")
    if run.get("search_capped"):
        head.append("# WARNING: discovery stopped at a budget or search limit; older activity may be underrepresented")
    for key, error in run["errors"].items():
        head.append(f"# WARNING: {key}: {error}; report coverage is incomplete")
    if remaining:
        head.append(f"# MORE: fetch --run {args.run} --offset {remaining[0]} --limit {args.limit}; "
                    "continue within the saved budget without asking to expand scope")
    if any("<omitted " in b for b in blocks):
        head.append("# NOTE: some long threads are shortened (<omitted comments=\"n\"/>); "
                    "use `show --run <run> --id <comment-id>` to read one in full")
    return "\n".join(head) + "\n\n" + "\n\n".join(blocks) + "\n"


def cmd_fetch(args: argparse.Namespace, get: Runner = gh_get) -> str:
    run, start, end, windows = _fetch_setup(args)
    _private_mkdir(reports_home())
    if run is None:
        while True:
            run_id = new_run_id(args)
            try:
                run_dir(run_id).mkdir(mode=0o700)
            except FileExistsError:
                continue
            args.run = run_id
            break
    try:
        with run_lock(run_dir(args.run)), closing(Store(reports_home())) as store:
            _import_saved_threads(store)
            if run is not None:
                run = load_run(args.run)
            return _fetch_locked(args, run, start, end, windows, get, store)
    except RunBusy as exc:
        sys.exit(str(exc))


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
    f.add_argument("--team", help="organization/team-slug; select PRs authored by current team members, "
                   "not comments authored by the team (default scope: that organization)")
    f.add_argument("--pr", action="append", type=int, help="specific PR numbers (one --repo)")
    f.add_argument("--since", type=_day, help="first UTC day, YYYY-MM-DD (default: 7 days ago)")
    f.add_argument("--until", type=_day, help="UTC day to stop before, YYYY-MM-DD (default: tomorrow)")
    f.add_argument("--window", type=_named_window, action="append", default=[],
                   help="NAME:START:END (UTC, end exclusive); repeat for overlapping windows sharing one budget")
    f.add_argument("--offset", type=int, default=0)
    f.add_argument("--limit", type=int, default=20, help="PRs per batch, within the invocation-wide budget")
    f.add_argument("--budget", type=int, help="maximum unique PR candidates for the entire run (default: 100)")
    f.add_argument("--all", action="store_true", default=None, help="explicitly remove the candidate budget")
    f.add_argument("--exhaustive", action="store_true", default=None,
                   help="use broad discovery instead of person-focused search; retains the candidate budget")
    f.add_argument("--refresh", action="store_true", default=None,
                   help="bypass the 24-hour discovery/thread/team-membership cache")
    f.add_argument("--run", help="resume a saved run, keeping its scope, dates and total budget")
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
