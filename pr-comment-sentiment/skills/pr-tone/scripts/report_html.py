"""Render a pr-tone run as one self-contained HTML file (no external requests).

All comment text is untrusted and goes through html.escape. Counts are
computed here from the labels, not taken from the model's prose.
"""

from __future__ import annotations

import html
from collections import Counter
from datetime import datetime, timezone

TONES = ["kind", "neutral", "mean", "toxic"]
HELP = ["helpful", "somewhat_helpful", "not_helpful"]
HELP_LABEL = {"helpful": "Helpful", "somewhat_helpful": "Somewhat helpful", "not_helpful": "Not helpful"}
CONFLICT_LABEL = {"respectful_disagreement": "Respectful disagreement", "contradicts_earlier": "Contradicts earlier"}
SMALL_SAMPLE = 10
DISPUTED_SM = ' <span class="badge outline warn sm">disputed</span>'
EDITED = ' · <span title="Edited after posting; labels apply to the current text">edited</span>'


def e(s: object) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def severity(lab: dict) -> int:
    return {"toxic": 40, "mean": 30}.get(lab["tone"], 0) + (10 if lab["conflict"] == "contradicts_earlier" else 0)


def concern_order(x: tuple) -> tuple:
    """Worst first; at the same level, disputed ones (a charitable reading holds up) go after the clear ones."""
    c, lab = x[0], x[3]
    return -severity(lab), bool(lab.get("disputed")), c["created_at"]


def url(u: object) -> str:
    """Escaped link target; anything but an http(s) URL becomes '#', so stored data can't inject javascript: links."""
    s = "" if u is None else str(u)
    return e(s) if s.startswith(("https://", "http://")) else "#"


def quote_of(lab: dict, body: str) -> str:
    """The label's evidence if it really is a quote from the comment, else the comment itself."""
    ev = (lab.get("evidence") or "").strip()
    return ev if ev and ev in body else body.strip()


def is_concern(lab: dict) -> bool:
    return lab["tone"] in ("mean", "toxic") or bool(lab.get("disputed")) or lab["conflict"] == "contradicts_earlier"


def _body_with_evidence(body: str, evidence: str | None) -> str:
    """Escape the body and wrap the first exact occurrence of the evidence quote in <mark>."""
    if evidence and evidence.strip() and evidence in body:
        i = body.index(evidence)
        return e(body[:i]) + "<mark>" + e(evidence) + "</mark>" + e(body[i + len(evidence):])
    return e(body)


def _edited(c: dict) -> bool:
    return bool(c.get("updated_at")) and c["updated_at"] != c["created_at"]


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _date(ts: str) -> str:
    return ts[:10]


def _tone_bar(counts: Counter, label: str) -> str:
    total = sum(counts[t] for t in TONES)
    if not total:
        return '<div class="bar empty">no labelled comments</div>'
    segs = []
    for t in TONES:
        n = counts[t]
        if n:
            pct = 100 * n / total
            segs.append(f'<span class="seg t-{t}" style="flex:{n}" data-tip="{e(label)}: {n} {t} ({pct:.0f}%)"></span>')
    legend = " ".join(f'<span class="lg"><i class="sw t-{t}"></i>{t} <b>{counts[t]}</b></span>' for t in TONES)
    spoken = ", ".join(f"{counts[t]} {t}" for t in TONES)
    return f'<div class="bar" role="img" aria-label="{e(label)} tone: {spoken}">{"".join(segs)}</div>' \
           f'<div class="legend">{legend}</div>'


def _badges(lab: dict) -> str:
    out = [f'<span class="badge t-{lab["tone"]}">{e(lab["tone"])}</span>',
           f'<span class="badge plain">{e(HELP_LABEL[lab["helpfulness"]])}</span>']
    if lab["conflict"] != "none":
        out.append(f'<span class="badge outline">{e(CONFLICT_LABEL[lab["conflict"]])}</span>')
    if lab.get("disputed"):
        out.append('<span class="badge outline warn">Disputed</span>')
    out.append(f'<span class="badge plain">confidence {e(lab["confidence"])}</span>')
    return "".join(out)


def _thread(item: dict, focus: str, also: str | None, labels: dict) -> str:
    rows = []
    for c in item["comments"]:
        if not c["body"].strip():
            continue
        cls = "tc focus" if c["id"] == focus else "tc related" if c["id"] == also else "tc"
        lab = labels.get(c["id"])
        tag = f' <span class="badge t-{lab["tone"]} sm">{e(lab["tone"])}</span>' if lab and c["id"] != focus else ""
        where = f' · <code>{e(c["file"])}</code>' if c.get("file") else ""
        state = f' · {e(c["review_state"].lower().replace("_", " "))}' if c.get("review_state") else ""
        rows.append(
            f'<div class="{cls}" id="t-{e(focus)}-{e(c["id"])}"><div class="tm"><b>{e(c["author"])}</b> · '
            f'{e(_date(c["created_at"]))}{EDITED if _edited(c) else ""}{where}{state}{tag} · '
            f'<a href="{url(c["url"])}" target="_blank" rel="noopener">open</a></div>'
            f'<div class="tb">{e(c["body"].strip())}</div></div>')
    return "".join(rows)


def _concern_card(c: dict, pr: dict, item: dict, lab: dict, labels: dict, run_id: str, by_id: dict) -> str:
    conflict = ""
    other = lab.get("conflicts_with")
    if lab["conflict"] == "contradicts_earlier" and other in by_id:
        o = by_id[other]
        conflict = (f'<div class="conflict"><div class="k">Contradicts {e(o["author"])} '
                    f'({e(_date(o["created_at"]))})</div><div class="q">{e(o["body"].strip()[:600])}</div></div>')
    charitable = (f'<div class="kv"><span class="k">Charitable reading</span>{e(lab["charitable_reading"])}</div>'
                  if lab.get("charitable_reading") else "")
    dig = f"Use the pr-tone skill to dig deeper into comment {c['id']} from run {run_id}"
    return f'''
<article class="card concern" data-person="{e(c['author'].lower())}" data-tone="{e(lab['tone'])}" id="c-{e(c['id'])}">
  <header><div class="who"><b>{e(c['author'])}</b> on <a href="{url(pr['url'])}" target="_blank" rel="noopener">{e(pr['repo'])}#{e(pr['number'])}</a>
    <span class="muted">· {e(pr['title'])} · {e(_date(c['created_at']))}{EDITED if _edited(c) else ''}</span></div>
    <div class="badges">{_badges(lab)}</div></header>
  <blockquote class="body">{_body_with_evidence(c['body'].strip(), lab.get('evidence'))}</blockquote>
  <div class="kv"><span class="k">Why</span>{e(lab.get('rationale'))}</div>
  {charitable}
  {conflict}
  <details><summary>Full PR thread ({len([x for x in item['comments'] if x['body'].strip()])} comments)</summary>
    <div class="thread">{_thread(item, c['id'], other, labels)}</div></details>
  <footer><a class="btn" href="{url(c['url'])}" target="_blank" rel="noopener">Open on GitHub</a>
    <button class="btn copy" data-copy="{e(dig)}">Copy “dig deeper” prompt</button></footer>
</article>'''


def _highlight(c: dict, pr: dict, lab: dict) -> str:
    return (f'<li><span class="badge t-{lab["tone"]} sm">{e(lab["tone"])}</span> '
            f'<b>{e(c["author"])}</b> on <a href="{url(c["url"])}" target="_blank" rel="noopener">{e(pr["repo"])}#{e(pr["number"])}</a>: '
            f'“{e(quote_of(lab, c["body"])[:220])}”</li>')


def render_report(run: dict, labels: dict, notes: list[dict]) -> str:
    items, by_id = [], {}
    for item in run["prs"].values():
        for c in item["comments"]:
            by_id[c["id"]] = c
            if c.get("target"):
                items.append((c, item["pr"], item))
    labelled = [(c, pr, it, labels[c["id"]]) for c, pr, it in items if c["id"] in labels]
    skipped = Counter(c["skip"] for it in run["prs"].values() for c in it["comments"] if c.get("skip"))
    overall = Counter(l["tone"] for *_, l in labelled)
    concerns = sorted((x for x in labelled if is_concern(x[3])), key=concern_order)
    disputed = sum(1 for *_, l in labelled if l.get("disputed"))

    scope = run["scope"]
    wanted = [a.lower() for a in scope["authors"]]
    authors = Counter(c["author"] for c, *_ in labelled)
    if wanted:
        people = [next((a for a in authors if a.lower() == w), w) for w in wanted]
    else:
        people = [a for a, _ in authors.most_common()]
    person_notes = {n.get("login", "").lower(): n for n in notes if n.get("type") == "person"}
    summary = next((n.get("text", "") for n in notes if n.get("type") == "summary"), "")

    where = ", ".join(scope["repos"] + [f"org:{o}" for o in scope["orgs"]]) or "GitHub"
    if scope["prs"]:
        where += " · PR " + ", ".join(f"#{n}" for n in scope["prs"])
    who = ", ".join(scope["authors"]) or "everyone"
    window = f'{run["window"]["start"]} → {run["window"]["end"]}'
    if run["window"]["start"].startswith("1970"):
        window = "full history"
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ---- people cards
    cards = []
    for p in people:
        mine = [x for x in labelled if x[0]["author"].lower() == p.lower()]
        tones = Counter(x[3]["tone"] for x in mine)
        helps = Counter(x[3]["helpfulness"] for x in mine)
        n_concern = sum(1 for x in mine if is_concern(x[3]))
        note = person_notes.get(p.lower(), {})
        small = f'<span class="badge outline">small sample ({len(mine)})</span>' if len(mine) < SMALL_SAMPLE else ""
        strengths = sorted((x for x in mine if x[3]["tone"] == "kind" or x[3]["helpfulness"] == "helpful"),
                           key=lambda x: (x[3]["helpfulness"] != "helpful", x[3]["tone"] != "kind"))[:3]
        help_txt = " · ".join(f"{HELP_LABEL[h]} {helps[h]}" for h in HELP)
        cards.append(f'''
<article class="card person" id="p-{e(p.lower())}">
  <header><h3><a href="https://github.com/{e(p)}" target="_blank" rel="noopener">{e(p)}</a></h3>
    <div class="badges"><span class="badge plain">{plural(len(mine), "comment")}</span>
    <span class="badge {'outline warn' if n_concern else 'plain'}">{n_concern} concern{'s' if n_concern != 1 else ''}</span>{small}</div></header>
  {_tone_bar(tones, p)}
  <p class="muted small">{e(help_txt)}</p>
  {f'<p>{e(note.get("pattern"))}</p>' if note.get("pattern") else ''}
  {f'<p class="muted">{e(note.get("context"))}</p>' if note.get("context") else ''}
  <h4>Strengths</h4>
  {('<ul class="hl">' + "".join(_highlight(c, pr, l) for c, pr, _, l in strengths) + '</ul>') if strengths
   else f'<p class="muted small">{"No labelled comments in this run." if not mine else "None of these comments were labelled kind or helpful; that is not evidence of a problem."}</p>'}
  {f'<button class="btn filter" data-person="{e(p.lower())}">Show {n_concern} concern{"s" if n_concern != 1 else ""}</button>' if n_concern else ''}
</article>''')

    concern_html = "".join(_concern_card(c, pr, it, l, labels, run["run"], by_id) for c, pr, it, l in concerns) \
        or '<p class="muted">No concerns found.</p>'
    kind_helpful = [x for x in labelled if x[3]["tone"] == "kind" and x[3]["helpfulness"] == "helpful"][:12]

    rows = "".join(
        f'<tr data-person="{e(c["author"].lower())}" data-tone="{e(l["tone"])}" '
        f'data-text="{e((c["body"] + " " + pr["repo"]).lower())}">'
        f'<td>{e(_date(c["created_at"]))}</td><td>{e(c["author"])}</td>'
        f'<td><a href="{url(c["url"])}" target="_blank" rel="noopener">{e(pr["repo"])}#{e(pr["number"])}</a></td>'
        f'<td><span class="badge t-{l["tone"]} sm">{e(l["tone"])}</span>{DISPUTED_SM if l.get("disputed") else ""}</td>'
        f'<td>{e(HELP_LABEL[l["helpfulness"]])}</td>'
        f'<td>{e(CONFLICT_LABEL.get(l["conflict"], "—"))}</td>'
        f'<td class="ex">{e(c["body"].strip()[:160])}</td></tr>'
        for c, pr, _, l in sorted(labelled, key=lambda x: x[0]["created_at"], reverse=True))
    person_opts = "".join(f'<option value="{e(p.lower())}">{e(p)}</option>' for p in sorted(authors, key=str.lower))
    unlabelled = len(items) - len(labelled)
    skipped_txt = ", ".join(f"{k} {v}" for k, v in sorted(skipped.items())) or "none"

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PR tone report</title>
<style>
:root {{
  --page:#f9f9f7; --surface:#fcfcfb; --card:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --line:#e1e0d9; --accent:#2a78d6; --mark:#fde9a8; --warn:#b4570f;
  --t-kind:#2a78d6; --t-neutral:#c9c7bf; --t-mean:#e8793f; --t-toxic:#c22f2f;
}}
@media (prefers-color-scheme: dark) {{ :root:where(:not([data-theme="light"])) {{
  color-scheme:dark; --page:#0d0d0d; --surface:#1a1a19; --card:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781;
  --line:#2c2c2a; --accent:#6da7ec; --mark:#5c4a12; --warn:#f0a35e;
  --t-kind:#3987e5; --t-neutral:#6a6964; --t-mean:#cc7d28; --t-toxic:#c4353f; }}
  :root:where(:not([data-theme="light"])) .badge.t-kind {{ color:#0b0b0b }} }}
:root[data-theme="dark"] {{ color-scheme:dark; --page:#0d0d0d; --surface:#1a1a19; --card:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7;
  --muted:#898781; --line:#2c2c2a; --accent:#6da7ec; --mark:#5c4a12; --warn:#f0a35e;
  --t-kind:#3987e5; --t-neutral:#6a6964; --t-mean:#cc7d28; --t-toxic:#c4353f; }}
:root[data-theme="dark"] .badge.t-kind {{ color:#0b0b0b }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--page); color:var(--ink); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif }}
main {{ max-width:1080px; margin:0 auto; padding:32px 16px 64px }}
a {{ color:var(--accent) }}
h1 {{ font-size:28px; margin:0 0 4px }} h2 {{ font-size:20px; margin:40px 0 12px }} h3 {{ margin:0; font-size:17px }}
h4 {{ margin:16px 0 6px; font-size:13px; text-transform:uppercase; letter-spacing:.04em; color:var(--ink2) }}
.muted {{ color:var(--ink2) }} .small {{ font-size:13px }}
.meta {{ color:var(--ink2); margin-bottom:20px }}
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:20px 0 }}
.kpi {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px }}
.kpi b {{ display:block; font-size:28px; font-variant-numeric:tabular-nums }} .kpi span {{ color:var(--ink2); font-size:13px }}
.summary {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px 18px; white-space:pre-wrap }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; margin:0 0 14px }}
.card header {{ display:flex; flex-wrap:wrap; justify-content:space-between; gap:8px; align-items:baseline; margin-bottom:10px }}
.people {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:14px }}
.people .card {{ margin:0 }}
.bar {{ display:flex; gap:2px; height:14px; margin:8px 0 6px }}
.bar.empty {{ height:auto; color:var(--muted); font-size:13px }}
.seg {{ min-width:4px; border-radius:2px }} .seg:first-child {{ border-radius:4px 2px 2px 4px }} .seg:last-child {{ border-radius:2px 4px 4px 2px }}
.seg:only-child {{ border-radius:4px }}
.legend {{ display:flex; flex-wrap:wrap; gap:12px; font-size:13px; color:var(--ink2) }}
.lg b {{ color:var(--ink); font-variant-numeric:tabular-nums }}
.sw {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px }}
.t-kind {{ background:var(--t-kind) }} .t-neutral {{ background:var(--t-neutral) }}
.t-mean {{ background:var(--t-mean) }} .t-toxic {{ background:var(--t-toxic) }}
.badges {{ display:flex; flex-wrap:wrap; gap:6px }}
.badge {{ font-size:12px; padding:2px 8px; border-radius:999px; color:#fff; white-space:nowrap }}
.badge.t-neutral {{ color:var(--ink) }} .badge.sm {{ font-size:11px; padding:1px 6px }}
.badge.t-mean {{ color:#0b0b0b }} /* white on orange is under 3:1 */
.badge.plain {{ background:transparent; color:var(--ink2); border:1px solid var(--line) }}
.badge.outline {{ background:transparent; color:var(--ink); border:1px solid var(--ink2) }}
.badge.warn {{ border-color:var(--warn); color:var(--warn) }}
blockquote.body {{ margin:0 0 12px; padding:10px 14px; border-left:3px solid var(--line); white-space:pre-wrap; overflow-wrap:anywhere }}
.concern[data-tone="mean"] blockquote {{ border-color:var(--t-mean) }}
.concern[data-tone="toxic"] blockquote {{ border-color:var(--t-toxic) }}
mark {{ background:var(--mark); color:inherit; border-radius:3px; padding:0 2px }}
.kv {{ margin:6px 0 }} .k {{ font-weight:600; margin-right:8px; color:var(--ink2) }}
.conflict {{ margin:10px 0; padding:10px 14px; border:1px dashed var(--ink2); border-radius:8px }}
.conflict .q {{ white-space:pre-wrap; color:var(--ink2) }}
details {{ margin-top:12px }} summary {{ cursor:pointer; color:var(--accent) }}
.thread {{ margin-top:10px; border-left:2px solid var(--line); padding-left:12px }}
.tc {{ padding:8px 0; border-bottom:1px solid var(--line) }}
.tc.focus {{ background:color-mix(in srgb, var(--t-mean) 12%, transparent); padding:8px; border-radius:6px }}
.tc.related {{ outline:1px dashed var(--ink2); padding:8px; border-radius:6px }}
.tm {{ font-size:13px; color:var(--ink2) }} .tb {{ white-space:pre-wrap; overflow-wrap:anywhere }}
.card footer {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:12px }}
.btn {{ font:inherit; font-size:13px; padding:6px 12px; border-radius:8px; border:1px solid var(--line); background:var(--surface);
  color:var(--ink); cursor:pointer; text-decoration:none }}
.btn:hover {{ border-color:var(--ink2) }}
ul.hl {{ margin:0; padding-left:18px }} ul.hl li {{ margin:4px 0 }}
.filters {{ display:flex; flex-wrap:wrap; gap:8px; margin:0 0 12px }}
.filters select, .filters input {{ font:inherit; padding:6px 10px; border-radius:8px; border:1px solid var(--line);
  background:var(--surface); color:var(--ink) }}
.tablewrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:10px }}
table {{ border-collapse:collapse; width:100%; font-size:14px; background:var(--card) }}
th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top }}
th {{ color:var(--ink2); font-weight:600; font-size:13px }}
td:first-child {{ white-space:nowrap }}
td.ex {{ color:var(--ink2); min-width:240px }}
.note {{ margin-top:40px; font-size:13px; color:var(--ink2) }}
#tip {{ position:fixed; pointer-events:none; background:var(--ink); color:var(--page); font-size:12px; padding:4px 8px;
  border-radius:6px; display:none; z-index:10 }}
.active-filter {{ margin:0 0 12px; font-size:13px }}
</style></head>
<body><main>
<h1>PR tone report</h1>
<div class="meta">{e(where)} · people: {e(who)} · {e(window)} · generated {e(generated)} · run <code>{e(run["run"])}</code></div>

<div class="kpis">
  <div class="kpi"><b>{len(labelled)}</b><span>comments labelled</span></div>
  <div class="kpi"><b>{len(concerns)}</b><span>concerns</span></div>
  <div class="kpi"><b>{disputed}</b><span>disputed</span></div>
  <div class="kpi"><b>{sum(skipped.values())}</b><span>skipped ({e(skipped_txt)})</span></div>
</div>
{f'<p class="muted">⚠ {plural(unlabelled, "target comment")} not labelled.</p>' if unlabelled else ''}
{f'<div class="summary">{e(summary)}</div>' if summary else ''}

<h2>Overall tone</h2>
{_tone_bar(overall, "All comments")}

<h2>People</h2>
<div class="people">{"".join(cards) or '<p class="muted">No labelled comments.</p>'}</div>

<h2 id="concerns">Concerns ({len(concerns)})</h2>
<div class="active-filter" id="af" hidden>Showing concerns for <b id="afn"></b> · <a href="#" id="clear">show all</a></div>
{concern_html}

<h2>Kind and helpful</h2>
{('<ul class="hl">' + "".join(_highlight(c, pr, l) for c, pr, _, l in kind_helpful) + '</ul>') if kind_helpful else '<p class="muted">None in this run.</p>'}

<h2>All labelled comments</h2>
<div class="filters">
  <select id="fp" aria-label="Filter by person"><option value="">Everyone</option>{person_opts}</select>
  <select id="ft" aria-label="Filter by tone"><option value="">Any tone</option>{"".join(f'<option>{t}</option>' for t in TONES)}</select>
  <input id="fq" type="search" placeholder="Search text or repo" aria-label="Search comment text or repo">
  <span class="muted small" id="fc" aria-live="polite"></span>
</div>
<div class="tablewrap"><table><thead><tr><th>Date</th><th>Person</th><th>PR</th><th>Tone</th><th>Helpfulness</th><th>Conflict</th><th>Comment</th></tr></thead>
<tbody id="rows">{rows}</tbody></table></div>

<p class="note">These labels are model judgements of written text, without tone of voice or team history.
Read the linked comments in context before acting on any of them. This file is local and private; do not commit it.</p>
</main>
<div id="tip"></div>
<script>
const tip = document.getElementById('tip');
document.querySelectorAll('[data-tip]').forEach(el => {{
  el.addEventListener('mousemove', ev => {{ tip.textContent = el.dataset.tip; tip.style.display = 'block';
    tip.style.left = (ev.clientX + 12) + 'px'; tip.style.top = (ev.clientY + 12) + 'px'; }});
  el.addEventListener('mouseleave', () => tip.style.display = 'none');
}});
document.querySelectorAll('.copy').forEach(b => b.addEventListener('click', async () => {{
  try {{ await navigator.clipboard.writeText(b.dataset.copy); b.textContent = 'Copied'; }}
  catch {{ prompt('Copy this prompt:', b.dataset.copy); }}
}}));
const af = document.getElementById('af');
function filterConcerns(p) {{
  document.querySelectorAll('.concern').forEach(c => c.hidden = !!p && c.dataset.person !== p);
  af.hidden = !p; document.getElementById('afn').textContent = p || '';
}}
document.querySelectorAll('.filter').forEach(b => b.addEventListener('click', () => {{
  filterConcerns(b.dataset.person); document.getElementById('concerns').scrollIntoView({{behavior:'smooth'}});
}}));
document.getElementById('clear').addEventListener('click', ev => {{ ev.preventDefault(); filterConcerns(''); }});
const fp = document.getElementById('fp'), ft = document.getElementById('ft'), fq = document.getElementById('fq');
function filterRows() {{
  let n = 0;
  document.querySelectorAll('#rows tr').forEach(r => {{
    const ok = (!fp.value || r.dataset.person === fp.value) && (!ft.value || r.dataset.tone === ft.value)
      && (!fq.value || r.dataset.text.includes(fq.value.toLowerCase()));
    r.hidden = !ok; if (ok) n++;
  }});
  document.getElementById('fc').textContent = n + ' shown';
}}
[fp, ft, fq].forEach(x => x.addEventListener('input', filterRows)); filterRows();
</script>
</body></html>
'''
