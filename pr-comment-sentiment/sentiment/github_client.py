"""Fetch PR comments with the GitHub CLI (`gh api`) and build per-comment context.

Uses whatever account `gh auth login` is signed in as, so any repo you can
read with gh works here.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from typing import Callable, Iterator

from .models import ClassificationInput, Comment, PullRequestContext

PER_PAGE = 100
MAX_PRIOR_COMMENTS = 30  # older context rarely changes a label and costs tokens
MAX_DIFF_HUNK_LINES = 40

Runner = Callable[[list[str]], str]


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def run_gh(args: list[str]) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


class GitHubClient:
    def __init__(self, runner: Runner = run_gh):
        self.run = runner

    def _pages(self, path: str, params: str = "") -> Iterator[dict]:
        """Yield items from a REST list endpoint one page at a time, so callers can stop early."""
        page = 1
        while True:
            sep = "&" if params else ""
            items = json.loads(self.run(["api", f"{path}?{params}{sep}per_page={PER_PAGE}&page={page}"]))
            yield from items
            if len(items) < PER_PAGE:
                return
            page += 1

    def pull(self, repo: str, number: int) -> dict:
        return json.loads(self.run(["api", f"repos/{repo}/pulls/{number}"]))

    def pulls_updated_since(self, repo: str, since: datetime) -> Iterator[dict]:
        """PRs (open or closed) whose updated_at is at or after `since`, newest first."""
        for pr in self._pages(f"repos/{repo}/pulls", "state=all&sort=updated&direction=desc"):
            if _parse_ts(pr["updated_at"]) < since:
                return
            yield pr

    def pr_comments(self, repo: str, number: int) -> list[Comment]:
        """All human-readable text on a PR, oldest first."""
        comments: list[Comment] = []

        for c in self._pages(f"repos/{repo}/issues/{number}/comments"):
            comments.append(_from_issue_comment(c))

        review_comments = list(self._pages(f"repos/{repo}/pulls/{number}/comments"))
        by_id = {c["id"]: c for c in review_comments}
        for c in review_comments:
            comments.append(_from_review_comment(c, _thread_root(c, by_id)))

        for r in self._pages(f"repos/{repo}/pulls/{number}/reviews"):
            if (r.get("body") or "").strip() and r.get("submitted_at"):
                comments.append(_from_review(r))

        comments.sort(key=lambda c: c.created_at)
        return comments


def _is_bot(user: dict | None) -> bool:
    return bool(user) and user.get("type") == "Bot"


def _login(user: dict | None) -> str:
    return (user or {}).get("login", "ghost")


def _from_issue_comment(c: dict) -> Comment:
    return Comment(
        id=f"issue_comment:{c['id']}",
        kind="issue_comment",
        author=_login(c.get("user")),
        author_is_bot=_is_bot(c.get("user")),
        body=c.get("body") or "",
        created_at=c["created_at"],
        updated_at=c["updated_at"],
        url=c["html_url"],
        thread_id="conversation",
    )


def _thread_root(c: dict, by_id: dict[int, dict]) -> int:
    seen = set()
    while c.get("in_reply_to_id") and c["in_reply_to_id"] in by_id and c["id"] not in seen:
        seen.add(c["id"])
        c = by_id[c["in_reply_to_id"]]
    return c["id"]


def _from_review_comment(c: dict, root_id: int) -> Comment:
    hunk = c.get("diff_hunk")
    if hunk:
        hunk = "\n".join(hunk.splitlines()[-MAX_DIFF_HUNK_LINES:])
    return Comment(
        id=f"review_comment:{c['id']}",
        kind="review_comment",
        author=_login(c.get("user")),
        author_is_bot=_is_bot(c.get("user")),
        body=c.get("body") or "",
        created_at=c["created_at"],
        updated_at=c["updated_at"],
        url=c["html_url"],
        thread_id=f"review_thread:{root_id}",
        path=c.get("path"),
        diff_hunk=hunk,
    )


def _from_review(r: dict) -> Comment:
    return Comment(
        id=f"review:{r['id']}",
        kind="review",
        author=_login(r.get("user")),
        author_is_bot=_is_bot(r.get("user")),
        body=r.get("body") or "",
        created_at=r["submitted_at"],
        updated_at=r["submitted_at"],
        url=r["html_url"],
        thread_id="conversation",
        review_state=r.get("state"),
    )


def build_inputs(
    pr: PullRequestContext, comments: list[Comment], start: datetime, end: datetime
) -> list[ClassificationInput]:
    """One ClassificationInput per comment created or edited inside [start, end).

    Prior context is every earlier comment on the PR (any thread), because
    "conflicts with a previous message" often spans threads: reviewer A asks
    for X on one line, reviewer B asks for not-X in the conversation tab.
    """
    inputs = []
    for i, c in enumerate(comments):
        touched = _parse_ts(c.updated_at)
        if not (start <= touched < end):
            continue
        prior = [p for p in comments[:i] if p.body.strip()][-MAX_PRIOR_COMMENTS:]
        inputs.append(ClassificationInput(pr=pr, target=c, prior_comments=prior))
    return inputs


def _pr_context(repo: str, pr: dict) -> PullRequestContext:
    return PullRequestContext(
        repo=repo, number=pr["number"], title=pr["title"], author=_login(pr.get("user")), url=pr["html_url"]
    )


def collect_inputs(
    gh: GitHubClient,
    repos: list[str],
    start: datetime,
    end: datetime,
    pr_numbers: list[int] | None = None,
) -> list[ClassificationInput]:
    """Comments created or edited in [start, end) across `repos`, or only on `pr_numbers` if given."""
    inputs: list[ClassificationInput] = []
    for repo in repos:
        prs = [gh.pull(repo, n) for n in pr_numbers] if pr_numbers else gh.pulls_updated_since(repo, start)
        for pr in prs:
            ctx = _pr_context(repo, pr)
            inputs.extend(build_inputs(ctx, gh.pr_comments(repo, pr["number"]), start, end))
    return inputs
