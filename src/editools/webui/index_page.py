"""The Index Checker's page, and what happens when a file lands on it."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..index import audit
from .common import RESULTS, new_job

#: Word's highlight names, as CSS colours, for the legend and the table.
SWATCH = {"yellow": "#f7e463", "brightGreen": "#8fe08f",
          "cyan": "#8fdcdc", "magenta": "#efa0d8"}

LABELS = {
    "entry-order": "Main entries out of order",
    "subentry-order": "Subentries out of order",
    "page-order": "Page numbers out of order",
    "range-order": "Page ranges reversed",
    "duplicate-page": "Page listed twice",
    "page-too-high": "Page past the end of the book",
    "elision": "Page range elided wrongly",
    "no-term": "No entry term",
    "punctuation": "Doubled punctuation",
    "spaced-dash": "Dash with a space beside it",
    "italic-punctuation": "Punctuation should be roman",
    "roman-note-comma": "Note comma should be italic",
    "spell-out-title": "Personal title not abbreviated",
    "post-world": "Check this hyphen",
    "ff-passim": "ff. or passim",
    "note-italics": "Note marker italicised",
    "see-style": "see / see also restyled",
    "quotes": "Curly quotes",
    "number-dash": "En dash between page numbers",
    "whitespace": "Tabs and extra spaces removed",
    "dangling-crossref": "Cross-reference points nowhere",
    "syntax": "Punctuation between the parts",
}

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Index Checker</title>
<style>
  :root {
    --bg:#faf9f7; --panel:#fff; --ink:#1c1b19; --muted:#6b6862;
    --line:#e3e0da; --accent:#7a2e2e;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#1a1917; --panel:#232120; --ink:#f0ede8; --muted:#a29d95;
            --line:#3a3734; --accent:#d98a8a; }
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:16px/1.55 Georgia,"Iowan Old Style",serif; }
  .wrap { max-width:820px; margin:0 auto; padding:48px 24px 80px; }
  h1 { font-size:30px; margin:0 0 6px; letter-spacing:-.01em; }
  .sub { color:var(--muted); margin:0 0 32px; }
  .panel { background:var(--panel); border:1px solid var(--line);
           border-radius:10px; padding:28px; }
  #drop { border:2px dashed var(--line); border-radius:10px; padding:44px 20px;
          text-align:center; cursor:pointer; transition:.15s; }
  #drop.over, #drop:hover { border-color:var(--accent);
          background:rgba(122,46,46,.04); }
  #drop strong { display:block; font-size:18px; margin-bottom:6px; }
  #drop span { color:var(--muted); font-size:14px; }
  .status { margin-top:24px; display:none; } .status.on { display:block; }
  .bar { height:3px; background:var(--line); border-radius:2px; overflow:hidden; }
  .bar i { display:block; height:100%; width:35%; background:var(--accent);
           animation:slide 1.1s ease-in-out infinite; }
  @keyframes slide { 0%{margin-left:-35%} 100%{margin-left:100%} }
  table { width:100%; border-collapse:collapse; margin-top:18px; font-size:14px;
          font-family:system-ui,sans-serif; }
  th { text-align:left; color:var(--muted); font-weight:600; font-size:12px;
       text-transform:uppercase; letter-spacing:.04em; padding:8px 10px;
       border-bottom:1px solid var(--line); }
  td { padding:8px 10px; border-bottom:1px solid var(--line);
       vertical-align:top; }
  td.where { white-space:nowrap; color:var(--muted); }
  .swatch { display:inline-block; width:10px; height:10px; border-radius:2px;
            margin-right:7px; vertical-align:baseline; }
  .tally { display:grid; gap:14px 28px; margin:8px 0 4px;
           grid-template-columns:repeat(auto-fit,minmax(120px,1fr));
           font-family:system-ui,sans-serif; }
  .tally div { font-size:13px; color:var(--muted); line-height:1.3; }
  .tally b { display:block; font-size:26px; color:var(--ink); font-weight:600; }
  .tally .bad b { color:var(--accent); }
  a.dl { display:inline-block; margin-top:20px; background:var(--accent);
         color:#fff; text-decoration:none; padding:11px 20px; border-radius:7px;
         font-family:system-ui,sans-serif; font-size:15px; }
  .note { margin-top:18px; font-size:13px; color:var(--muted);
          font-family:system-ui,sans-serif; }
  .lastpage { display:flex; align-items:center; gap:10px; margin-top:16px;
              font-family:system-ui,sans-serif; font-size:14px; flex-wrap:wrap; }
  .lastpage input { width:110px; padding:8px 10px; border:1px solid var(--line);
                    border-radius:6px; background:var(--bg); color:var(--ink);
                    font-size:14px; }
  .lastpage span { color:var(--muted); font-size:13px; }
  .kind { font-size:11px; text-transform:uppercase; letter-spacing:.04em;
          color:var(--muted); font-weight:600; }
  .kind.fix { color:var(--ok,#2f6b4f); }
  tr.check td { opacity:.78; }
  .err { color:var(--accent); }
  .back { display:inline-block; margin:0 0 18px; font-size:13px;
          font-family:system-ui,sans-serif; color:var(--muted);
          text-decoration:none; }
  .back:hover { color:var(--accent); }
  #update { display:none; margin:0 0 20px; padding:12px 16px;
            border:1px solid var(--line); border-left:3px solid var(--accent);
            border-radius:6px; background:var(--panel); font-size:14px;
            font-family:system-ui,sans-serif; }
  #update.on { display:block; }
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="/">← All editorial tools</a>
  <div id="update"></div>
  <h1>Index Checker</h1>
  <p class="sub">Drop in an index. What house style settles is fixed for you;
     what needs judgement is highlighted and explained in a Word comment.
     Everything is a tracked change, so nothing is decided behind your back.</p>

  <div class="panel">
    <div id="drop">
      <strong>Drop a Word file here</strong>
      <span>or click to choose one</span>
      <input type="file" id="file" accept=".docx" hidden>
    </div>

    <label class="lastpage">Last page of the book
      <input type="number" id="lastpage" min="1" placeholder="optional">
      <span>so references past the end can be caught</span>
    </label>

    <div class="status" id="status">
      <div class="bar"><i></i></div>
      <p id="msg" style="color:var(--muted);font-size:14px">Reading the index…</p>
    </div>

    <div id="out"></div>
  </div>

  <p class="note">Nothing leaves this computer. The page is served by a program
     running on your own machine.</p>
</div>

<script>
// Checked at most once a day, and silent about any problem: not being able to
// reach GitHub is no reason to interrupt someone checking an index.
fetch('/update-status')
  .then(r => r.json())
  .then(s => {
    if (!s.available && !s.installed) return;
    const box = document.getElementById('update');
    box.innerHTML = s.installed
      ? '<b>An update was installed.</b> Close this window and open the checker '
        + 'again to start using it.'
      : '<b>A new version is available.</b> It will install by itself next time '
        + 'you open the checker.';
    box.classList.add('on');
  })
  .catch(() => {});

const drop = document.getElementById('drop');
const file = document.getElementById('file');
const status = document.getElementById('status');
const out = document.getElementById('out');
const msg = document.getElementById('msg');

drop.onclick = () => file.click();
drop.ondragover = e => { e.preventDefault(); drop.classList.add('over'); };
drop.ondragleave = () => drop.classList.remove('over');
drop.ondrop = e => {
  e.preventDefault(); drop.classList.remove('over');
  if (e.dataTransfer.files.length) send(e.dataTransfer.files[0]);
};
file.onchange = () => { if (file.files.length) send(file.files[0]); };

function esc(s) {
  return String(s).replace(/[&<>"]/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

async function send(f) {
  if (!f.name.toLowerCase().endsWith('.docx')) {
    out.innerHTML = '<p class="err">That is not a Word .docx file.</p>';
    return;
  }
  out.innerHTML = '';
  status.classList.add('on');
  msg.textContent = 'Checking ' + f.name + '…';
  const body = new FormData();
  body.append('file', f);
  const last = document.getElementById('lastpage').value;
  if (last) body.append('last_page', last);
  let data;
  try {
    data = await (await fetch('/index/check', {method:'POST', body})).json();
  } catch (err) {
    status.classList.remove('on');
    out.innerHTML = '<p class="err">' + esc(err) + '</p>';
    return;
  }
  status.classList.remove('on');
  if (data.error) {
    out.innerHTML = '<p class="err">' + esc(data.error) + '</p>';
    return;
  }
  render(data);
}

function render(d) {
  let html = '<div class="tally">' +
    '<div><b>' + d.entries + '</b>entries</div>' +
    '<div><b>' + d.fixes + '</b>fixed for you</div>' +
    '<div class="bad"><b>' + d.flags + '</b>to look at</div>';
  for (const [rule, n] of Object.entries(d.counts))
    html += '<div><b>' + n + '</b>' + esc(d.labels[rule] || rule) + '</div>';
  html += '</div>';

  if (d.findings.length) {
    html += '<table><tr><th>Entry</th><th></th><th>What happened</th></tr>';
    for (const f of d.findings.slice(0, 200)) {
      const sw = d.swatch[f.colour] || '#ccc';
      const kind = f.fixed ? '<span class="kind fix">fixed</span>'
                           : '<span class="kind">flagged</span>';
      const dot = f.fixed ? '' :
        '<span class="swatch" style="background:' + sw + '"></span>';
      html += '<tr class="' + (f.severity === 'check' ? 'check' : '') +
              '"><td class="where">' + dot + esc(f.entry) + '</td><td>' +
              kind + '</td><td>' + esc(f.message) + '</td></tr>';
    }
    html += '</table>';
    if (d.findings.length > 200)
      html += '<p class="note">Showing the first 200. All of them are marked ' +
              'in the file.</p>';
  } else {
    html += '<p>Nothing to flag.</p>';
  }
  html += '<a class="dl" href="/index/download/' + d.id + '">Download the marked-up file</a>';
  out.innerHTML = html;
}
</script>
</body>
</html>
"""




DOCX = ("application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document")

EXPIRED = "That result has expired; check the index again."


def check(filename: str, data: bytes, fields: dict) -> dict:
    """Check one uploaded index and describe the result for the page."""
    try:
        last_page = int(fields.get("last_page") or 0) or None
    except ValueError:
        last_page = None

    job, folder = new_job()
    safe = Path(filename).name or "index.docx"
    source = folder / safe
    source.write_bytes(data)

    try:
        result = audit.run(
            source, out_path=folder / (Path(safe).stem + "_checked.docx"),
            last_page=last_page)
    except Exception as exc:      # surfaced in the page, not the console
        shutil.rmtree(folder, ignore_errors=True)
        return {"error": f"{type(exc).__name__}: {exc}"}

    RESULTS[job] = result.path
    return {
        "id": job,
        "entries": result.entries,
        "fixes": result.fixes,
        "flags": result.flags,
        "counts": result.counts(),
        "labels": LABELS,
        "swatch": SWATCH,
        "findings": [
            {"entry": entry, "message": finding.message,
             "colour": finding.colour, "severity": finding.severity,
             "fixed": bool(finding.action)}
            for entry, finding in result.described()
        ],
    }
