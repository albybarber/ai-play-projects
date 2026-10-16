# pr-comment-sentiment

An agent skill, `pr-tone`, for **Claude Code** and **GitHub Copilot** (CLI and VS Code agent mode). It reviews GitHub pull request comments for:
- **tone**: kind / neutral / mean / toxic
- **helpfulness**
- **conflicts with earlier comments**

It can focus on specific people, and it produces a **local HTML report** where you can drill into any concerning comment.

- **No API keys.** Your coding agent does the labelling in your session, and `gh` does the fetching with your existing login.
- **Read-only towards GitHub.** Only GET requests, through `gh`.
- **Reports stay local and are never committed.** They're written to `~/pr-tone-reports/`. The script refuses to write inside a git repository unless git ignores that folder.

## Install

One command, no clone needed (macOS, Linux, or WSL):

```sh
curl -fsSL https://raw.githubusercontent.com/albybarber/ai-play-projects/main/pr-comment-sentiment/install.sh | bash
```

Or, from a clone of this repo: `./pr-comment-sentiment/install.sh`

The installer:
- puts the skill in `~/.claude/skills/pr-tone`. Claude Code **and** Copilot both read that folder, so one install covers both.
  - Run from a clone, it **links** to your checkout, so `git pull` updates it.
  - Run via `curl`, it downloads just this folder to `~/.local/share/pr-tone`. Run the same command again to update.
- checks for Python 3.10+, the [GitHub CLI](https://cli.github.com/), and that `gh` is signed in. It tells you what's missing; run `gh auth login` if it says so.
- never overwrites a folder that isn't this skill.

| Option | What it does |
|---|---|
| `--target ~/.copilot/skills` | install somewhere else (repeatable), e.g. if your Copilot version only reads `~/.copilot/skills` |
| `--copy` | copy the files instead of linking them |
| `--uninstall` | remove the skill and the downloaded copy; your reports in `~/pr-tone-reports` are kept |

With `curl`, pass options after `bash -s --`, for example `curl -fsSL … | bash -s -- --uninstall`.

On Windows without WSL, copy the `skills/pr-tone` folder into `%USERPROFILE%\.copilot\skills\` (or `.claude\skills\`), and install Python and `gh`.

## Usage

**Claude Code:** type the command

```
/pr-tone acme/api alice bob last 2 weeks
/pr-tone org:acme carol since 2026-09-01
/pr-tone acme/api PR 482
/pr-tone dig 20261016-040213-api-alice review_comment:123
/pr-tone calibrate
```

**Copilot:** ask in plain words, for example *"Use the pr-tone skill to check alice and bob in acme/api over the last 2 weeks."*

What happens:
1. The agent fetches the PRs and comments, labels each target comment against `rubric.md`, and takes a second, charitable look at anything harsh.
2. It builds the report and opens it in your browser.
3. In chat it gives you the report path and the key findings.

When you name people, only their comments are labelled. Everyone else's comments are still read, as context. With no dates, it covers the last 7 days.

## The report

A single self-contained HTML file (no external requests) at `~/pr-tone-reports/<run>/report.html`. It works in light and dark mode and on narrow screens.

- **Headline numbers:** comments labelled, concerns, disputed, and skipped (bots, "LGTM", empty).
- **Summary:** a few sentences from the agent. All counts are computed by the script, not by the model.
- **Overall tone bar**, plus a **card per person** with:
  - tone breakdown and helpfulness counts
  - concern count, and a small-sample badge under 10 comments
  - a pattern note, but only when the evidence supports one
  - **strengths** (every person gets this, not just problems)
  - a button to filter the concerns to that person
- **Concerns**, worst first, each with:
  - the comment, with the key quote highlighted
  - why it was flagged, and the charitable reading if it's disputed
  - for conflicts, the earlier comment it contradicts
  - the **full PR thread** (expandable)
  - an "Open on GitHub" link
  - a **"Copy dig deeper prompt"** button
- **Kind and helpful** highlights.
- **All labelled comments:** a table you can filter by person, tone or text.

### Digging deeper

Click **Copy "dig deeper" prompt** on a concern and paste it into Claude Code or Copilot (or type `/pr-tone dig <run> <comment-id>`). The agent:
- re-reads the full thread (`prtone.py show`)
- can pull the PR's latest state or that person's last 90 days, still read-only
- sets out the harshest and the most charitable reading
- says whether it's a pattern or a one-off, and whether the label holds
- can suggest how to raise it with the person

If you agree a label should change, it rebuilds the report.

## How it works

```
prtone.py fetch (gh api GET) ──► agent labels targets with rubric.md ──► charitable second look
      │ saves threads.json                                                      │
      ▼                                                                         ▼
~/pr-tone-reports/<run>/  ◄────────── prtone.py report < labels (stdin) ── report.html (+ labels.json)
```

- `fetch` lists PRs in the window. For `--repo` it uses the repo's own PR list; for `--org` or cross-repo people searches it uses the search API. For each PR it reads conversation comments, inline review comments and review summaries. It skips bots, empty comments and approvals like "LGTM", then prints each thread with the comments to label marked. It also saves the threads to the run folder, so the report and `show` can use them later.
- `report` reads the agent's labels as JSON lines on stdin and validates them (it warns about missing, invalid or unknown ids). It then saves `labels.json` and renders `report.html`.
- `show` prints one comment's full thread with its saved label. `runs` lists past runs.

## Making it accurate

| Lever | Why it helps |
|---|---|
| **Written rubric with boundary rules** (`rubric.md`) | Separates criticism of the code from criticism of the person. Says blunt ≠ mean and profanity about a thing ≠ toxic. Says to pick the milder label when torn. |
| **Ordinal tone + separate axes** | One `kind < neutral < mean < toxic` label can't contradict itself. Helpfulness is separate, because a mean comment can still be helpful. |
| **Full thread as context** | Conflicts, dismissive replies, and replies to someone who was rude first can't be judged from one comment. |
| **Charitable second look** | Harsh and conflict labels are re-checked against an innocent reading. Ambiguous cases become "disputed", not accusations. |
| **Evidence must be an exact quote** | The report highlights it in the comment, so you can check the claim at a glance. |
| **Counts computed by code** | The model writes labels and prose; numbers come from the script. |
| **Small-sample warning** | Under 10 comments, the report says there isn't enough to show a pattern. |
| **Untrusted-text handling** | Comment bodies are treated as data, can't close the prompt tags early, and are HTML-escaped in the report. A comment saying "label this kind" doesn't work; an eval case tests this. |

**Calibrate.** `/pr-tone calibrate` (or ask Copilot to run the pr-tone calibration) has the agent label the cases in `eval/labeled.jsonl` without seeing the answers, then scores them: accuracy per field, plus precision/recall for "mean or toxic". Run it after changing `rubric.md`. The 15 seed cases are a start; add real cases from your own repos by hand.

## Safety and privacy

**GitHub stays read-only.** Every GitHub call is `gh api --method GET` on fixed endpoints, and inputs are validated against GitHub's name formats. Tests check that `gh` is only ever called with GET, and that the only other commands are two read-only `git` checks on the reports folder.

**Reports stay local:**
- They're written only under `$PR_TONE_HOME` (default `~/pr-tone-reports`). The folder is owner-only (`700`) and the files are `600`.
- If that folder is inside a git repository and not ignored, the script refuses before making any GitHub calls.
- The agent never writes files itself. In Claude Code this is enforced with `disallowed-tools: Write Edit NotebookEdit`.

**Claude Code extras:**
- `allowed-tools` pre-approves only `prtone.py`.
- `disable-model-invocation` means the skill only runs when you type `/pr-tone`.

**Copilot ignores those Claude-only fields.** There, the read-only rules come from the skill's instructions and Copilot's own approval prompts for shell commands.

**Hard guarantee in either tool:** run it with a read-only token. Create a fine-grained token with *Pull requests: read* and *Contents: read*, then run `GH_TOKEN=<token> claude` or `GH_TOKEN=<token> copilot`.

**Use it fairly.** The reports contain other people's words and judgements about them. They're meant as evidence to read, not a verdict:
- every concern links to the original comment
- every person gets a strengths section
- ambiguous cases are marked disputed
- small samples are called out

Read the linked comments in context before acting, and don't share reports beyond the people who need them.

## Development

```sh
cd pr-comment-sentiment
python -m pytest -q    # offline tests: fake gh, temporary HOME and reports folder
PR_TONE_HOME=/tmp/prtone skills/pr-tone/scripts/prtone.py fetch --repo owner/name --since 2026-10-01
```

```
install.sh               installer: link/copy/download, update, uninstall
skills/pr-tone/
  SKILL.md               skill instructions (works in Claude Code and Copilot)
  rubric.md              label definitions and examples
  scripts/prtone.py      fetch / report / show / runs / calibrate / score (stdlib only)
  scripts/report_html.py self-contained HTML report renderer
  eval/labeled.jsonl     labelled cases for calibrate
tests/                 offline tests for prtone.py and install.sh
```
