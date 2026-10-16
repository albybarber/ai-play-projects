# pr-comment-sentiment

An agent skill, `pr-tone`, for **Claude Code** and **GitHub Copilot** (CLI and VS Code agent mode). It reviews GitHub pull request comments for:
- **tone**: kind / neutral / mean / toxic
- **helpfulness**
- **conflicts with earlier comments**

It can focus on specific commenters or PRs authored by a GitHub team, reuses fetched evidence in a **local SQLite database**, and produces a **local HTML report** where you can drill into any concerning comment. No hosted service is needed.

- **No API keys.** Your coding agent does the labelling in your session, and `gh` does the fetching with your existing login.
- **Read-only towards GitHub.** Only GET requests, through `gh`.
- **Fetch once, reuse locally.** Discovery and full PR threads are reusable for 24 hours. Missing or stale data is fetched on demand; unchanged evidence and rubric allow label reuse.
- **Reports stay local and are never committed.** They're written to `~/pr-tone-reports/`. The script refuses to write inside a git repository unless git ignores that folder.

## Install

One command, no clone needed (macOS, Linux, or WSL):

```sh
curl -fsSL https://raw.githubusercontent.com/albybarber/ai-play-projects/main/pr-comment-sentiment/install.sh | bash
```

Or, from a clone of this repo: `./pr-comment-sentiment/install.sh`

The installer:
- puts the skill in **`~/.claude/skills/pr-tone`** (Claude Code) and **`~/.copilot/skills/pr-tone`** (GitHub Copilot CLI and VS Code). Both are links to the same files, so they never drift apart. Some recent Copilot CLI versions no longer read `~/.claude/skills`, which is why it installs into both.
  - Run from a clone, it **links** to your checkout, so `git pull` updates it.
  - Run via `curl`, it downloads just this folder to `~/.local/share/pr-tone`. Run the same command again to update.
- checks for Python 3.10+, the [GitHub CLI](https://cli.github.com/), and that `gh` is signed in. It tells you what's missing; run `gh auth login` if it says so.
- never overwrites or deletes a folder that isn't this skill (or, for the download folder, isn't its own download).

| Option | What it does |
|---|---|
| `--target DIR` | install only into `DIR` (repeatable), e.g. `--target ~/.copilot/skills` for Copilot only |
| `--copy` | copy the files instead of linking them |
| `--uninstall` | remove the skill and the downloaded copy; your reports in `~/pr-tone-reports` are kept |

With `curl`, pass options after `bash -s --`, for example `curl -fsSL … | bash -s -- --uninstall`.

**Check it's loaded.** Start a new session first (or run `/skills reload` in Copilot CLI).
- **Copilot CLI:** run `/skills info pr-tone`.
- **VS Code:** type `/skills` in Copilot Chat (agent mode) and look for `pr-tone`.
- **Claude Code:** type `/pr-tone`.

If VS Code doesn't list it, check that agent skills are turned on in your Copilot settings.

On Windows without WSL, copy the `skills/pr-tone` folder into `%USERPROFILE%\.copilot\skills\` (or `.claude\skills\`), and install Python and `gh`.

## Usage

**Claude Code:** type the command

```
/pr-tone acme/api alice bob last 2 weeks
/pr-tone org:acme carol since 2026-09-01
/pr-tone Frameio/massdriver team:content-supply-chain-csc last month
/pr-tone acme/api PR 482
/pr-tone dig 20261016-040213-api-alice review_comment:123
/pr-tone calibrate
```

**Copilot:** ask in plain words, for example *"Use the pr-tone skill to check alice and bob in acme/api over the last 2 weeks."*

What happens:
1. The helper reuses fresh local discovery/threads and fetches missing or stale evidence. The agent labels only comments without compatible saved labels, against `rubric.md`, and takes a second, charitable look at anything harsh.
2. It builds the report and opens it in your browser.
3. In chat it gives you the report path and the key findings.

When you name people, only their comments are labelled. Everyone else's comments are still read, as context. Dates are UTC and refer to when a comment was posted; with no dates, it covers the last 7 days plus today. Comments edited after posting are labelled as they read now and marked "edited".

### Feedback on your team's PRs

Use a team scope to assess comments **on PRs authored by team members**, rather than comments written by one reviewer:

```sh
skills/pr-tone/scripts/prtone.py fetch --repo Frameio/massdriver \
  --team Frameio/content-supply-chain-csc --since 2026-09-16 --until 2026-10-17
```

The helper resolves the team's **current members**, searches for their PRs updated since the window began (including older PRs receiving new comments), and labels eligible human comments from everyone, including PR-author replies. Bots, empty comments and trivial acknowledgements are still skipped. Report cards and concerns are grouped by the **commenter**, not the PR author, so the team is not blamed for feedback it received. An optional `--author LOGIN` separately restricts which commenters to assess.

`--team` requires `ORGANIZATION/TEAM-SLUG`; without `--repo` or `--org`, it searches the team's organization. This selects authored PRs, not PRs where the team was requested to review. Discovery remains search-index-dependent and budgeted, including with `--exhaustive`.

Membership is cached for 24 hours, saved with its timestamp and roster in the run/report, and frozen when resuming. New runs with changed membership use a different discovery cache entry; `--refresh` also refreshes membership. Current membership does **not** reconstruct who belonged to the team when a PR or comment was created. An empty roster selects no PRs. If membership cannot be read, the helper stops explicitly; confirm team visibility and your `gh` token's organization/team access and any required SSO authorization.

### Scope, speed and freshness

The default is **fast person-focused discovery, at most 100 unique candidate PRs per run**, newest first among bounded discovered results. All requested date windows share that budget; cached PRs and PRs with no eligible comments count too. The skill finishes approved batches without asking about pagination or scope expansion, then stops. A 100-PR budget does **not** mean only 100 API requests: comments and reviews have separate paginated endpoints.

Person-focused discovery uses GitHub's `involves:` and `reviewed-by:` searches, not the PR's author. Search indexing and bounded discovery can miss relevant comments. Reports prominently show partial coverage, evidence age, failures, per-window summaries, and API/cache counts. Missing results are not proof of no activity; no coverage percentage is claimed when the true total is unknown.

You can say *"max 30 candidates"*, *"refresh the evidence"*, or *"use broad discovery, max 200 candidates"* in your request. Helper equivalents:

```sh
skills/pr-tone/scripts/prtone.py fetch --repo acme/api --author alice --budget 30
skills/pr-tone/scripts/prtone.py fetch --repo acme/api --author alice --refresh
skills/pr-tone/scripts/prtone.py fetch --repo acme/api --author alice --exhaustive --budget 200
skills/pr-tone/scripts/prtone.py fetch --repo acme/api --exhaustive --all  # explicit unbounded candidate scope
skills/pr-tone/scripts/prtone.py fetch --run <run-id>                  # same scope and total budget
```

`--exhaustive` selects broad discovery; it does not remove the budget. Organization-wide broad discovery still uses GitHub search and its 1,000-result cap per query, so it can remain incomplete even with `--all`. `--limit` controls batch size (default 20), not the total budget.

For overlapping windows, fetch once and score each collected comment once:

```sh
skills/pr-tone/scripts/prtone.py fetch --repo acme/api --author alice \
  --window weekly:2026-10-09:2026-10-16 --window monthly:2026-10-01:2026-10-16
```

Window ends are exclusive. A comment can contribute to both summaries without being duplicated within either.

Fresh discovery results (including successful empty searches), team membership and complete threads are reused for up to **24 hours**. This can omit subsequent comments, edits, deletions and membership changes. `--refresh` bypasses these caches on a new run; resuming a saved run preserves completed snapshots, even when older than 24 hours. Run an explicitly refreshed new analysis for current evidence. Labels are reused only when the full PR context, comment, rubric and skill instructions match; summary/person prose is not reused across runs.

## The report

A single self-contained HTML file (no external requests) at `~/pr-tone-reports/<run>/report.html`. It works in light and dark mode and on narrow screens.

- **Headline numbers:** comments labelled, concerns, disputed, and skipped (bots, "LGTM", empty).
- **Coverage and provenance:** candidate budget, partial discovery/fetching, evidence timestamps, team roster when selected, API requests, cache hits, and separate summaries for each date window.
- **Summary:** a few sentences from the agent. All counts are computed by the script, not by the model.
- **Overall tone bar**, plus a **card per person** with:
  - tone breakdown and helpfulness counts
  - concern count, and a small-sample badge under 10 comments
  - a pattern note, but only when the evidence supports one
  - **strengths** (every person gets this section, not just problems)
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

If you agree a label should change, it rebuilds the report with `report --merge`, which replaces just that label and keeps the rest.

## How it works

```
                       ┌── cache.sqlite3: discovery, team rosters, threads, labels
prtone.py fetch ◄───────┤
      │                └── gh api GET: only missing/stale evidence
      ▼
agent session labels remaining targets ──► charitable second look
      │
      ▼
prtone.py report --merge ──► <run>/report.html (+ threads.json and labels.json)
```

- `fetch` uses person-focused searches by default when people are named. Broad repository discovery uses the repo's PR list, stopping at the date boundary or budget. Uncached fetching first checks authentication and repository/organization access, then fetches with up to four PR workers. Each completed PR (including those without target comments) is saved immediately. Only fully fetched threads enter the shared cache; failures are not cached as empty. Authentication/rate-limit failures stop further fetching and preserve progress. Other PR failures remain explicit gaps, retryable by run ID.
- The saved candidate list fixes the scope and total budget for continuation. Run locks prevent simultaneous fetch/report writers from corrupting one run; SQLite transactions coordinate the shared cache. File writes are atomic. Report HTML remains a portable snapshot, independent of the database. Older JSON-only runs still support reporting and drill-down; start a new run rather than resuming one without saved budget metadata.
- `fetch` reads conversation comments, inline review comments and review summaries. It skips bots, empty comments and approvals like "LGTM", then prints threads with only comments still needing labels marked `target="yes"`. In very long threads it keeps the context nearest the targets and marks omissions; `show` prints the whole thread.
- `report` validates JSON-line labels from the assistant session, saves `labels.json`, renders `report.html`, and indexes valid labels for reuse. It warns about missing/invalid labels, unknown IDs, non-matching evidence, unsupported concerns/disputes and invalid conflict references. `--merge` preserves saved labels and notes across batches; fresh-run reused labels are retained even without it. Summary/person notes remain specific to each run.
- `show` prints one comment's full thread with its saved label. `runs` lists past runs.

### Local storage and permissions

`$PR_TONE_HOME` selects the reports directory (default `~/pr-tone-reports`). It contains `cache.sqlite3` and run directories; no other cache location, model API key, database server or background service is required. Old reports and cache entries are not automatically deleted. They contain private review text and judgements, so manage retention and sharing deliberately.

On first use of a new database, complete threads from existing run files are imported with their recorded fetch time (or, conservatively, the run's creation time). They are reusable only while fresh. Old labels without matching provenance are rescored, and existing report files are left intact.

The helper's scope budget does not change Copilot/Claude execution permissions. Use `/permissions` in Copilot CLI to review permission modes, and narrow helper/path grants where your client supports them. The project does not modify those settings or require unrestricted shell approval. Cached runs can work without GitHub access, but the client may still ask to execute the helper.

## Making it accurate

| Lever | Why it helps |
|---|---|
| **Written rubric with boundary rules** (`rubric.md`) | Separates criticism of the code from criticism of the person. Says blunt ≠ mean and profanity about a thing ≠ toxic. Says to pick the milder label when torn. |
| **Ordinal tone + separate axes** | One `kind < neutral < mean < toxic` label can't contradict itself. Helpfulness is separate, because a mean comment can still be helpful. |
| **Full thread as context** | Conflicts, dismissive replies, and replies to someone who was rude first can't be judged from one comment. |
| **Charitable second look** | Harsh and conflict labels are re-checked against an innocent reading. Ambiguous cases become "disputed", not accusations. |
| **Evidence must be an exact quote** | The script warns when it isn't, and the report highlights it in the comment, so you can check the claim at a glance. |
| **Counts computed by code** | The model writes labels and prose; numbers come from the script. |
| **Small-sample warning** | Under 10 comments, the report says there isn't enough to show a pattern. |
| **Untrusted-text handling** | Comment bodies are treated as data, can't open or close the prompt tags (so they can't forge a comment from someone else), and are HTML-escaped in the report. A comment saying "label this kind" doesn't work; eval cases test this. |

**Calibrate.** `/pr-tone calibrate` (or ask Copilot to run the pr-tone calibration) has the agent label the cases in `eval/labeled.jsonl` without seeing the answers, then scores them: accuracy per field, plus precision/recall for "mean or toxic". Run it after changing `rubric.md`. The 24 seed cases cover the main boundaries (blunt vs mean, jokes about code, quoted insults, acknowledged vs silent reversals, polite condescension, prompt injection). They are a start; add real cases from your own repos by hand.

## Safety and privacy

**GitHub stays read-only.** Every GitHub call is `gh api --method GET` on fixed endpoints, and inputs are validated against GitHub's name formats. Tests check that `gh` is only ever called with GET, and that the only other commands are two read-only `git` checks on the reports folder.

**Reports and the database stay local:**
- They're written only under `$PR_TONE_HOME` (default `~/pr-tone-reports`). The folder is owner-only (`700`) and the files are `600`.
- If that folder is inside a git repository and not ignored, the script refuses before making any GitHub calls.
- The agent never writes files itself. In Claude Code this is enforced with `disallowed-tools: Write Edit NotebookEdit`.

**Claude Code extras:**
- `allowed-tools` pre-approves only running `prtone.py` and reading the skill's own files.
- `disable-model-invocation` means the skill only runs when you type `/pr-tone`.

**Copilot ignores those Claude-only fields.** There, the read-only rules come from the skill's instructions and Copilot's own approval prompts for shell commands.

**Optional credential-level protection:** a fine-grained read-only GitHub token can further constrain access, but is not required; the normal flow uses your existing `gh` login and never requires a separate model API key.

**Use it fairly.** The reports contain other people's words and judgements about them. They're meant as evidence to read, not a verdict:
- every concern links to the original comment
- every person gets a strengths section
- ambiguous cases are marked disputed
- small samples are called out

Read the linked comments in context before acting, and don't share reports beyond the people who need them.

## Development

```sh
cd pr-comment-sentiment
uv run --python 3.14 --no-project --with pytest python -m pytest -q  # offline fake-GitHub tests
PR_TONE_HOME=/tmp/prtone skills/pr-tone/scripts/prtone.py fetch --repo owner/name --since 2026-10-01
```

```
install.sh               installer: link/copy/download, update, uninstall
skills/pr-tone/
  SKILL.md               skill instructions (works in Claude Code and Copilot)
  rubric.md              label definitions and examples
  scripts/prtone.py      fetch / report / show / runs / calibrate / score (stdlib only)
  scripts/report_html.py self-contained HTML report renderer
  scripts/local_store.py private SQLite cache and per-run process locks
  eval/labeled.jsonl     labelled cases for calibrate
tests/                 offline tests for prtone.py and install.sh
```
