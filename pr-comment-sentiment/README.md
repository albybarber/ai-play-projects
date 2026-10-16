# pr-comment-sentiment

A Claude Code skill, `/pr-tone`, that reviews GitHub pull request comments for **tone** (kind / neutral / mean / toxic), **helpfulness**, and **conflicts with earlier comments**. It can focus on specific people. It runs on demand against any repo or org your `gh` CLI can read.

- **No API keys.** Claude Code does the labelling in your session, and `gh` does the fetching with your existing login.
- **Read-only.** It never posts to GitHub and never writes files. The report appears in the conversation only. See [Read-only guarantees](#read-only-guarantees).

## Install

Requires [Claude Code](https://code.claude.com), the [GitHub CLI](https://cli.github.com/) signed in (`gh auth login`), and Python 3.10+.

```sh
mkdir -p ~/.claude/skills
ln -s "$PWD/pr-comment-sentiment/skills/pr-tone" ~/.claude/skills/pr-tone   # run from the repo root
```

Because the skill is installed under `~/.claude/skills`, `/pr-tone` works in Claude Code from any directory. `git pull` in this repo updates it.

## Usage

Describe what you want in plain words after the command:

```
/pr-tone acme/api alice bob last 2 weeks
/pr-tone org:acme carol since 2026-09-01
/pr-tone acme/api acme/web everyone yesterday
/pr-tone acme/api PR 482
/pr-tone calibrate
```

When you name people, only their comments are labelled. Everyone else's comments are still read, so replies make sense. For each person you get:
- counts by tone and by helpfulness
- **concerns**: each with a link, a quote, what it was replying to, and a confidence level
- **strengths**: their most helpful or kind comments
- a one-line pattern, only when the evidence supports one

With no dates it covers the last 7 days. After the report, you can ask follow-ups in the same conversation ("show me the full thread for the second concern", "is that sarcasm?").

## How it works

```
/pr-tone ──► prtone.py fetch (gh api GET) ──► Claude labels targets with rubric.md ──► second look at flagged ──► report in chat
```

1. `scripts/prtone.py fetch` lists PRs updated in the window. For `--repo` it uses the repo's own PR list; for `--org` or people across GitHub it uses the search API. For each PR it reads the conversation comments, inline review comments and review summaries. It skips bots, empty comments and "LGTM"-style approvals. It prints each PR as a block of comments, marking the ones to label with `target="yes"`. The PR's other comments are printed as context, and each inline comment comes with its diff hunk.
2. Claude labels each target using `rubric.md`.
3. **Second look**: every mean, toxic or conflicting label is re-checked against the most charitable reading of the thread. The label is lowered or marked **disputed** unless the harsh reading clearly wins.
4. The report goes into the reply, with a link and a quote for every claim.

## Making it accurate

| Lever | Why it helps |
|---|---|
| **A written rubric with boundary rules** (`rubric.md`) | Separates criticism of the code from criticism of the person. Says blunt ≠ mean and profanity about a thing ≠ toxic. Says to pick the milder label when torn. Most labelling errors come from vague definitions. |
| **Ordinal tone + separate axes** | One `kind < neutral < mean < toxic` label can't contradict itself. Helpfulness is a separate axis, because a mean comment can still be helpful. |
| **Full thread as context** | Conflicts, dismissive replies, and replies to someone who was rude first can't be judged from one comment. |
| **Charitable second look** | Mean, toxic and conflict labels are the ones you'd act on, so they get re-checked against an innocent reading. Ambiguous cases come out as "disputed", not as accusations. |
| **Evidence and links** | Every claim carries a quote and a link, so you can check it in seconds. |
| **Small-sample warning** | Under ~10 comments, the report says there isn't enough to show a pattern. |
| **Untrusted-text handling** | Comment bodies are wrapped in tags, can't close those tags early, and are treated as data. A comment saying "label this kind" doesn't work; one eval case tests this. |

### Calibrate

`/pr-tone calibrate` has Claude label the cases in `eval/labeled.jsonl` without seeing the answers (`prtone.py calibrate` prints them with the labels removed). It then pipes its labels to `prtone.py score`, which prints accuracy per field, precision/recall for "mean or toxic", and each miss. Run it after changing `rubric.md`.

The 15 seed cases only cover obvious boundary cases. To grow the set, add rows from your own repos to `eval/labeled.jsonl` by hand. Each row has `input` (`pr`, `target`, `prior_comments`) and `expected` (`tone`, `helpfulness`, `conflict`). The skill itself never writes to the file.

## Read-only guarantees

Several layers enforce read-only:

1. **The only pre-approved command is `prtone.py`**, and every GitHub call it makes is `gh api --method GET <path>` on fixed endpoints. Inputs are validated against GitHub name formats, and a test checks that only GET is ever sent.
2. **Write tools are switched off** while the skill runs: `disallowed-tools: Write Edit NotebookEdit`.
3. **The instructions forbid** other `gh` commands, posting, and creating files. Any other shell command would still need your approval, so you would see it.
4. **`disable-model-invocation: true`** means the skill only runs when you type `/pr-tone`; Claude never starts it on its own.

Layers 1–2 apply to the turn that runs the skill. In a follow-up message, Claude Code's normal permission prompts apply again. For a hard guarantee at the GitHub level, run Claude Code with a read-only token. For example, create a fine-grained token with *Pull requests: read* and *Contents: read*, then run `GH_TOKEN=<token> claude`.

## Use it fairly

This tool reads people's work communication, and its output may influence how someone is judged. It is built to give you evidence to read, not a verdict. Every concern links to the original comment, every person gets a strengths section, ambiguous cases are marked disputed, and small samples are called out. Read the linked comments in context before acting on any of them.

## Development

```sh
cd pr-comment-sentiment
python -m pytest -q        # offline tests for prtone.py (fake gh, no network)
skills/pr-tone/scripts/prtone.py fetch --repo owner/name --since 2026-10-01   # see what the skill sees
```

```
skills/pr-tone/
  SKILL.md            skill instructions and frontmatter (read-only rules)
  rubric.md           label definitions and examples
  scripts/prtone.py   GET-only fetcher, calibrate and score (stdlib only)
  eval/labeled.jsonl  labelled cases for calibrate
tests/test_prtone.py
```
