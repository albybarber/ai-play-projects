"""Cheap, deterministic checks that decide whether a comment is worth a model call.

Skipping bots and one-word approvals saves money and removes the most common
source of noise in the daily report (CI bots are never "kind" or "toxic").
"""

from __future__ import annotations

import re

from .models import Comment

_TRIVIAL = re.compile(
    r"^\s*(lgtm|looks good( to me)?|ship it|approved?|thanks!?|thank you!?|ty|"
    r"\+1|:\+1:|👍|✅|🚀|done\.?|fixed\.?|nit\.?)\s*[.!]*\s*$",
    re.IGNORECASE,
)
_BOT_NAME = re.compile(r"(\[bot\]$|-bot$|^dependabot|^renovate|^github-actions|^codecov)", re.IGNORECASE)


def is_bot(comment: Comment) -> bool:
    return comment.author_is_bot or bool(_BOT_NAME.search(comment.author))


def skip_reason(comment: Comment) -> str | None:
    """Return why a comment should not be sent to the model, or None to classify it."""
    if is_bot(comment):
        return "bot"
    body = comment.body.strip()
    if not body:
        return "empty"
    if _TRIVIAL.match(body):
        return "trivial"
    return None
