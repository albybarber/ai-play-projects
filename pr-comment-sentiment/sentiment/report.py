"""Turn a day's results into a short markdown digest."""

from __future__ import annotations

from collections import Counter

from .models import Result

TONES = ["kind", "neutral", "mean", "toxic"]
HELPFULNESS = ["helpful", "somewhat_helpful", "not_helpful"]


def _line(r: Result) -> str:
    c, t, pr = r.classification, r.input.target, r.input.pr
    quote = c.evidence.replace("\n", " ")
    if len(quote) > 160:
        quote = quote[:157] + "..."
    review = " · **needs human review**" if r.needs_human_review else ""
    return (
        f"- [{pr.repo}#{pr.number}]({t.url}) **{c.tone}** / {c.helpfulness} "
        f"(confidence {c.confidence}){review}\n  > {quote}\n  {c.rationale}"
    )


def _pct(n: int, total: int) -> str:
    return f"{(100 * n / total):.0f}%" if total else "–"


def render_markdown(results: list[Result], day: str) -> str:
    labelled = [r for r in results if r.classification]
    skipped = Counter(r.skipped_reason for r in results if r.skipped_reason)
    tone = Counter(r.classification.tone for r in labelled)
    helpful = Counter(r.classification.helpfulness for r in labelled)
    n = len(labelled)

    out = [f"# PR comment health — {day}", ""]
    out.append(f"{len(results)} comments seen, {n} labelled, {sum(skipped.values())} skipped.")
    if skipped:
        out.append("Skipped: " + ", ".join(f"{k} {v}" for k, v in sorted(skipped.items())) + ".")
    out += ["", "| Tone | Count | Share |", "|---|---|---|"]
    out += [f"| {t} | {tone[t]} | {_pct(tone[t], n)} |" for t in TONES]
    out += ["", "| Helpfulness | Count | Share |", "|---|---|---|"]
    out += [f"| {h} | {helpful[h]} | {_pct(helpful[h], n)} |" for h in HELPFULNESS]

    harsh = [r for r in labelled if r.classification.tone in ("toxic", "mean")]
    harsh.sort(key=lambda r: TONES.index(r.classification.tone), reverse=True)
    out += ["", f"## Toxic or mean ({len(harsh)})", ""]
    out += [_line(r) for r in harsh] or ["None today."]

    conflicts = [r for r in labelled if r.classification.conflict == "contradicts_earlier"]
    out += ["", f"## Contradicts an earlier comment ({len(conflicts)})", ""]
    out += [
        _line(r) + f"\n  Conflicts with `{r.classification.conflicts_with_comment_id}`" for r in conflicts
    ] or ["None today."]

    review = [r for r in results if r.needs_human_review and r not in harsh and r not in conflicts]
    if review:
        out += ["", f"## Other items for human review ({len(review)})", ""]
        for r in review:
            out.append(
                _line(r) if r.classification else f"- [{r.input.pr.repo}#{r.input.pr.number}]({r.input.target.url}) — {r.skipped_reason}"
            )

    kind = [r for r in labelled if r.classification.tone == "kind" and r.classification.helpfulness == "helpful"]
    out += ["", f"## Kind and helpful ({len(kind)})", ""]
    out += [_line(r) for r in kind[:10]] or ["None today."]
    return "\n".join(out) + "\n"
