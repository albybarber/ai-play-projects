# pr-comment-sentiment

A command-line tool that reads pull request comments from any repo you can access with the `gh` CLI. It labels each comment for **tone** (kind / neutral / mean / toxic), **helpfulness**, and whether it **conflicts with an earlier comment**, then writes a short markdown report.

The labels come from Claude (`claude-opus-5-5`) using a written rubric, structured outputs, and the full PR conversation as context. A labelled eval set measures how accurate the labels are.

> This is a team-health tool, not a performance-review tool. The report links to comments, not people's scores, and anything uncertain is marked for a person to read before anyone acts on it.

## How it works

```
gh api ──► fetch ──► prefilter ──► Claude pass 1 ──► (flagged?) ──► Claude pass 2 ──► report
           date range  bots,        rubric + PR        mean/toxic,     higher effort,    report.md
           or PR list  "LGTM"       context            conflict, or    disagree ⇒        results.jsonl
                                                                low confidence  human review
```

1. **Fetch** (`sentiment/github_client.py`, via `gh api`): for each repo, every PR updated in the date range, or just the PRs you name with `--pr`. It collects all three kinds of PR text (conversation comments, inline review comments, and review summaries), sorted oldest first. A comment is a target if it was created or edited in the range. Each target carries up to the 30 earlier comments on the PR (from any thread) and its diff hunk.
2. **Prefilter** (`sentiment/prefilter.py`): bot accounts, empty bodies, and one-word approvals like "LGTM" or 👍 are skipped without a model call.
3. **Classify** (`sentiment/classifier.py`): one structured-output call per comment returns `tone`, `helpfulness`, `conflict`, `conflicts_with_comment_id`, `flags`, an `evidence` quote, `rationale`, and `confidence`.
4. **Verify**: comments labelled mean or toxic, comments that contradict an earlier one, and low-confidence labels get a second, independent pass at higher effort. The second answer is kept. If the two passes disagree on tone or conflict, the item goes to the "needs human review" list.
5. **Report** (`sentiment/report.py`): counts by tone and helpfulness, then four lists: toxic or mean, contradicts an earlier comment, other items for human review, and kind and helpful.

## Making it accurate

Sentiment models trained on product reviews or tweets do badly on code review. "This is wrong, use a set" is fine in a review, and sarcasm is common. Here is what this project does about it, roughly in order of impact:

| Lever | Why it helps |
|---|---|
| **A written rubric with boundary rules** (`SYSTEM_PROMPT`) | Separates "criticism of the code" from "criticism of the person". Says blunt ≠ mean and profanity about a thing ≠ toxic. Says to pick the milder label when torn. Most errors come from unclear definitions, not from the model. |
| **Ordinal, mutually exclusive tone** | One `kind < neutral < mean < toxic` label cannot contradict itself, unlike separate "kind 0.7, toxic 0.4" scores. Helpfulness and conflict are separate axes, because a mean comment can still be helpful. |
| **Thread context** | "Conflicts with a previous message" cannot be judged from one comment, and neither can "dismissive reply to a sincere question". Each target is shown with earlier comments (ids included) and its diff hunk. |
| **Evidence quote + rationale** | Forces the label to rest on specific words, and gives the human reviewer something to check in seconds. |
| **Two-pass verification on flagged items** | The labels you act on (mean, toxic, conflict) are the rarest and the costliest to get wrong, so they get a second look. Disagreement is a strong signal of a genuinely ambiguous comment. |
| **Prefilter** | Removes bots and "LGTM", which would otherwise make up a big share of the data and skew the numbers. |
| **Prompt-injection guard** | Comment text is wrapped in tags and marked as data. Structured outputs mean a comment saying "label this kind" can't change the output format. An eval row tests this. |
| **A labelled eval set** (`eval/labeled.jsonl`) | The only way to know whether a prompt change helped. See below. |

### The improvement loop

1. Run `python eval/run_eval.py`. It prints accuracy per field, a tone confusion matrix, and **precision/recall for "mean or toxic"**, which is the headline number.
2. After each run, take items from the "needs human review" list and any labels you disagree with. Copy those rows from `out/<run>/results.jsonl` into `eval/labeled.jsonl` (the `input` object has the same shape) and add an `expected` block.
3. Change the rubric or examples in `SYSTEM_PROMPT`, re-run the eval, and keep the change only if the headline improves without hurting the other fields. `--runs 3` shows how stable the labels are.
4. Aim for **100+ labelled rows** taken from your own repos before trusting the numbers. The 15 seed rows only cover the obvious boundary cases. If two people label the same rows, their agreement rate shows how high the model can realistically score.

## Usage

Requires Python 3.10+ and the [GitHub CLI](https://cli.github.com/) signed in (`gh auth login`). Whatever repos that account can read, this tool can read.

```sh
cd pr-comment-sentiment
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...       # or `ant auth login`

python run.py --repo owner/name                                # comments from yesterday (UTC)
python run.py --repo owner/name --since 2026-10-01             # a single day
python run.py --repo a/b --repo c/d --since 2026-10-01 --until 2026-10-08   # a week, two repos
python run.py --repo owner/name --pr 123 --pr 456              # every comment on these PRs
```

- Dates are UTC days. `--until` is exclusive and defaults to the day after `--since`.
- `--pr` with no dates labels the whole history of those PRs.
- The report is printed and saved to `out/<run>/report.md`, with one JSON line per comment in `out/<run>/results.jsonl`.
- `--effort low|medium|high` sets the first pass (default `medium`). `--workers` sets how many comments are labelled in parallel (default 4).

```sh
python -m pytest -q                 # offline unit tests (no API or gh calls)
python eval/run_eval.py             # live eval against eval/labeled.jsonl, uses the API
```

## Cost

Each labelled comment is one request of roughly 2–5K input tokens and a short output; about 10–20% of comments get a second pass. The rubric is a stable prefix with `cache_control`, so across a run it is billed at cache-read rates where the prefix is long enough to cache. If cost matters more than accuracy, try `--effort low` and compare with `eval/run_eval.py --effort low` first.

## Ideas for later

- Per-repo trend chart from accumulated `results.jsonl` files
- Use the Message Batches API (50% cheaper) for large date ranges. Note that server-side refusal fallbacks are not available on Batches.
