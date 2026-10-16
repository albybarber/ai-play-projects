"""Data shapes shared by the fetcher, classifier, report and eval."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

CommentKind = Literal["issue_comment", "review_comment", "review"]


class Comment(BaseModel):
    """One piece of human-written text on a pull request."""

    id: str  # "<kind>:<github id>" so ids from different endpoints never collide
    kind: CommentKind
    author: str
    author_is_bot: bool = False
    body: str
    created_at: str
    updated_at: str
    url: str
    thread_id: str  # review comments share their root's thread; everything else is "conversation"
    path: Optional[str] = None  # file a review comment is attached to
    diff_hunk: Optional[str] = None
    review_state: Optional[str] = None  # APPROVED / CHANGES_REQUESTED / COMMENTED for reviews


class PullRequestContext(BaseModel):
    repo: str
    number: int
    title: str
    author: str
    url: str


class ClassificationInput(BaseModel):
    """Everything the model sees for one target comment.

    Rows in eval/labeled.jsonl use this exact shape under "input", so any row
    from a daily results.jsonl can be copied into the eval set and labelled.
    """

    pr: PullRequestContext
    target: Comment
    prior_comments: list[Comment] = Field(default_factory=list)


Tone = Literal["kind", "neutral", "mean", "toxic"]
Helpfulness = Literal["not_helpful", "somewhat_helpful", "helpful"]
Conflict = Literal["none", "respectful_disagreement", "contradicts_earlier"]
Confidence = Literal["low", "medium", "high"]
Flag = Literal[
    "praise",
    "gratitude",
    "sarcasm",
    "condescension",
    "dismissive",
    "personal_attack",
    "profanity",
    "harassment_or_slur",
    "passive_aggressive",
    "vague",
    "actionable_suggestion",
    "explains_reasoning",
    "question",
]


class Classification(BaseModel):
    """What Claude returns for one comment (enforced via structured outputs)."""

    tone: Tone = Field(description="Overall tone toward the people involved.")
    helpfulness: Helpfulness = Field(description="How much the comment moves the PR forward.")
    conflict: Conflict = Field(description="Relationship to earlier comments in the PR.")
    conflicts_with_comment_id: Optional[str] = Field(
        default=None,
        description="Id of the earlier comment it contradicts, when conflict is contradicts_earlier.",
    )
    flags: list[Flag] = Field(default_factory=list)
    evidence: str = Field(description="Shortest exact quote from the target comment that drove the tone label.")
    rationale: str = Field(description="One or two sentences explaining the labels.")
    confidence: Confidence


class Result(BaseModel):
    """One line of results.jsonl."""

    input: ClassificationInput
    classification: Optional[Classification] = None
    skipped_reason: Optional[str] = None  # set when prefilter skipped or the model refused
    verified: bool = False  # a second, independent pass was run
    needs_human_review: bool = False
    model: Optional[str] = None
