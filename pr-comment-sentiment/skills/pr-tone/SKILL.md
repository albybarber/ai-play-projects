---
name: pr-tone
description: Read-only review of GitHub pull request comments for tone (kind, neutral, mean, toxic), helpfulness, and conflicts with earlier comments, optionally focused on specific people. Uses the gh CLI; never writes to GitHub or to disk.
argument-hint: "<owner/repo | org:name> [people] [date range | PR numbers]  — or: calibrate"
disable-model-invocation: true
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/prtone.py *) Read(${CLAUDE_SKILL_DIR}/**)
disallowed-tools: Write Edit NotebookEdit
---

# PR comment tone review

The user asked: `$ARGUMENTS`

## Read-only rules (do not break these)

- The **only** shell command you may run is `${CLAUDE_SKILL_DIR}/scripts/prtone.py` with its `fetch`, `calibrate` or `score` subcommands. It only makes GET requests through `gh`.
- Never run other `gh` commands, never post, comment, react, review, label or edit anything on GitHub, and never create or modify files. The report goes in your reply and nowhere else.
- If the user asks for something that needs writing, say this skill is read-only and stop.

## 1. Fetch

Read `${CLAUDE_SKILL_DIR}/rubric.md` first. Then turn the request into one fetch call:

```
${CLAUDE_SKILL_DIR}/scripts/prtone.py fetch [--repo owner/name ...] [--org name ...] [--author login ...] \
    [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--pr N ...] [--offset N] [--limit N]
```

- People to check → one `--author` per GitHub login. Only their comments are marked as targets. Everyone else's comments still appear, as context.
- No dates given → the last 7 days. "last month", "since Monday" and similar → compute UTC dates from today. `--until` is exclusive.
- `--pr` needs exactly one `--repo` and, without `--since`, covers the PR's whole history.
- If the header says `MORE`, keep calling with the `--offset` it gives until every PR has been read. For very large ranges, tell the user how many PRs there are and ask before reading them all.
- If `gh` fails with an auth error, tell the user to run `gh auth login` and stop.

## 2. Label

For every comment with `target="yes"`, apply the rubric: tone, helpfulness, conflict (plus the earlier comment id), flags, evidence quote, confidence. Read the whole `<pr>` block first, so replies, earlier instructions and who-said-what-to-whom are clear.

## 3. Second look before reporting

For every comment you labelled **mean**, **toxic** or **contradicts_earlier**, go back and:
1. Re-read the full thread around it.
2. Write down the most charitable plausible reading (a joke between friends? a reply to someone who was rude first? a reasonable change of mind after new information?).
3. Keep the label only if the charitable reading is clearly weaker. Otherwise lower it by one level, or mark it **disputed** with both readings.

Mislabelling someone as mean is worse than missing a borderline case, because these results may be used to judge a person.

## 4. Report (in the reply only)

Start with one line: scope, people, date window, and how many comments were labelled vs skipped (bots, empty, "LGTM").

**When specific people were requested**, give one section per person:
- Counts by tone and by helpfulness, plus the number of comments. With fewer than ~10 comments, say the sample is too small to show a pattern.
- **Concerns**: each mean, toxic, disputed or conflicting comment, with a link (the `url` attribute), the evidence quote, one line of context (what it was replying to), and confidence.
- **Strengths**: two or three of their most helpful or kind comments, with links. Every person gets this section, not just a list of problems.
- **Pattern**: one or two sentences, only if the evidence supports one.
- How other people spoke to them, if that context matters (for example, they were replying to someone who was rude first).

**Otherwise** give overall counts, then lists of: toxic or mean, contradicts an earlier comment, disputed, and a few kind-and-helpful highlights. Every item gets a link and a quote.

Finish with a short caveat: these are model judgements of written text without tone of voice or team history, so read the linked comments before acting on any of them.

## Calibrate (`/pr-tone calibrate`)

This measures how well the rubric is working.
1. Run `${CLAUDE_SKILL_DIR}/scripts/prtone.py calibrate` and label every case by following steps 2–3. Do **not** open `eval/labeled.jsonl`, which contains the answers.
2. Pipe your labels to the scorer, one JSON object per line:
   ```
   ${CLAUDE_SKILL_DIR}/scripts/prtone.py score <<'EOF'
   {"case": 1, "tone": "neutral", "helpfulness": "helpful", "conflict": "none"}
   ...
   EOF
   ```
3. Show the score output, then for each miss say whether the rubric, the expected label, or your reading looks wrong. Suggest rubric wording that would fix it, but don't edit anything.
