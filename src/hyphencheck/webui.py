"""A small local window for running an audit without touching a terminal.

Everything stays on this machine: the server binds to localhost, the proof
never leaves the computer, and the only outbound requests are the
Merriam-Webster word lookups the audit itself makes.
"""

from __future__ import annotations

import http.server
import json
import shutil
import tempfile
import threading
import uuid
import webbrowser
from email.parser import BytesParser
from email.policy import default as default_policy
from pathlib import Path
from urllib.parse import unquote

from . import audit, config, report
from .dictionary import Dictionary

RESULTS: dict[str, Path] = {}
WORKDIR = Path(tempfile.gettempdir()) / "hyphencheck-ui"

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hyphenation Checker</title>
<style>
  :root {
    --bg: #faf9f7; --panel: #ffffff; --ink: #1c1b19; --muted: #6b6862;
    --line: #e3e0da; --accent: #7a2e2e; --ok: #2f6b4f; --warn: #8a6d1f;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#1a1917; --panel:#232120; --ink:#f0ede8; --muted:#a29d95;
            --line:#3a3734; --accent:#d98a8a; --ok:#7fc4a2; --warn:#d9bd6b; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font: 16px/1.55 Georgia, "Iowan Old Style", serif; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 48px 24px 80px; }
  h1 { font-size: 30px; margin: 0 0 6px; letter-spacing: -0.01em; }
  .sub { color: var(--muted); margin: 0 0 32px; }
  .panel { background: var(--panel); border: 1px solid var(--line);
           border-radius: 10px; padding: 28px; }
  #drop { border: 2px dashed var(--line); border-radius: 10px; padding: 44px 20px;
          text-align: center; cursor: pointer; transition: .15s; }
  #drop.over, #drop:hover { border-color: var(--accent); background: rgba(122,46,46,.04); }
  #drop strong { display:block; font-size: 18px; margin-bottom: 6px; }
  #drop span { color: var(--muted); font-size: 14px; }
  .key { margin-top: 20px; font-size: 14px; color: var(--muted); }
  .key b { color: var(--ink); font-weight: normal; }
  .status { margin-top: 24px; display:none; }
  .status.on { display:block; }
  .bar { height: 3px; background: var(--line); border-radius: 2px; overflow: hidden; }
  .bar i { display:block; height:100%; width:35%; background: var(--accent);
           animation: slide 1.1s ease-in-out infinite; }
  @keyframes slide { 0%{margin-left:-35%} 100%{margin-left:100%} }
  table { width:100%; border-collapse: collapse; margin-top: 18px; font-size: 14px;
          font-family: system-ui, sans-serif; }
  th { text-align:left; color: var(--muted); font-weight:600; font-size:12px;
       text-transform: uppercase; letter-spacing:.04em; padding: 8px 10px;
       border-bottom: 1px solid var(--line); }
  td { padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
  td.brk { font-family: ui-monospace, Menlo, monospace; white-space: nowrap; }
  .tally { display:flex; gap: 28px; margin: 4px 0 8px; font-family: system-ui, sans-serif; }
  .tally div { font-size: 13px; color: var(--muted); }
  .tally b { display:block; font-size: 26px; color: var(--ink); font-weight: 600; }
  .tally .bad b { color: var(--accent); }
  .tally .mid b { color: var(--warn); }
  a.dl { display:inline-block; margin-top: 20px; background: var(--accent); color:#fff;
         text-decoration:none; padding: 11px 20px; border-radius: 7px;
         font-family: system-ui, sans-serif; font-size: 15px; }
  .err { color: var(--accent); }
  .ok { color: var(--ok); }
  .keyform { margin-top: 12px; display: none; gap: 8px; }
  .keyform.on { display: flex; }
  .keyform input { flex: 1; padding: 9px 11px; border: 1px solid var(--line);
                   border-radius: 6px; background: var(--bg); color: var(--ink);
                   font-family: ui-monospace, Menlo, monospace; font-size: 13px; }
  .keyform button { padding: 9px 16px; border: 0; border-radius: 6px; cursor: pointer;
                    background: var(--accent); color: #fff; font-size: 14px;
                    font-family: system-ui, sans-serif; }
  .keyform button:disabled { opacity: .5; cursor: default; }
  .linkish { color: var(--accent); cursor: pointer; text-decoration: underline; }
  code { background: rgba(128,128,128,.14); padding: 1px 5px; border-radius: 4px;
         font-size: 13px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Hyphenation Checker</h1>
  <p class="sub">Drop in a proof. Every end-of-line hyphen is checked against all nine
     rules, and you get a spreadsheet with page numbers.</p>

  <div class="panel">
    <div id="drop">
      <strong>Drop a PDF here</strong>
      <span>or click to choose one</span>
      <input type="file" id="file" accept="application/pdf,.pdf" hidden>
    </div>
    <div class="key" id="key"></div>
    <div class="keyform" id="keyform">
      <input type="password" id="keyinput" placeholder="Paste your Merriam-Webster key here"
             autocomplete="off" spellcheck="false">
      <button id="keysave">Save</button>
    </div>

    <div class="status" id="status">
      <div class="bar"><i></i></div>
      <p id="msg" style="color:var(--muted);font-size:14px">Reading the proof…</p>
    </div>

    <div id="out"></div>
  </div>
</div>

<script>
const drop = document.getElementById('drop');
const file = document.getElementById('file');
const status = document.getElementById('status');
const out = document.getElementById('out');
const msg = document.getElementById('msg');

const keyLine = document.getElementById('key');
const keyForm = document.getElementById('keyform');
const keyInput = document.getElementById('keyinput');
const keySave = document.getElementById('keysave');

function showKey(state) {
  if (state.has_key) {
    keyLine.innerHTML = 'Merriam-Webster key: <b>saved</b>. Rule 1 is checked against the '
      + 'dictionary itself. <span class="linkish" id="changekey">Change it</span>';
    keyForm.classList.remove('on');
    document.getElementById('changekey').onclick = () => keyForm.classList.add('on');
  } else {
    keyLine.innerHTML = '<b>No Merriam-Webster key saved.</b> Rule 1 will fall back to spelling '
      + 'patterns and be marked unverified. Every other rule works as normal. '
      + 'Paste your free key below — see the README for how to get one.';
    keyForm.classList.add('on');
  }
}
fetch('/status').then(r => r.json()).then(showKey);

keySave.onclick = () => {
  const value = keyInput.value.trim();
  if (!value) return;
  keySave.disabled = true;
  keyLine.innerHTML = 'Checking that key with Merriam-Webster…';
  fetch('/key', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key: value }),
  })
    .then(r => r.json())
    .then(res => {
      keySave.disabled = false;
      if (res.ok) {
        keyInput.value = '';
        keyLine.innerHTML = '<span class="ok">' + esc(res.message) + '</span>';
        keyForm.classList.remove('on');
        setTimeout(() => fetch('/status').then(r => r.json()).then(showKey), 2500);
      } else {
        keyLine.innerHTML = '<span class="err">' + esc(res.message) + '</span>';
        keyForm.classList.add('on');
      }
    })
    .catch(e => {
      keySave.disabled = false;
      keyLine.innerHTML = '<span class="err">Could not save the key: ' + esc(e.message) + '</span>';
    });
};
keyInput.addEventListener('keydown', e => { if (e.key === 'Enter') keySave.click(); });

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

function send(f) {
  if (!/\.pdf$/i.test(f.name)) { out.innerHTML = '<p class="err">That is not a PDF.</p>'; return; }
  out.innerHTML = '';
  status.classList.add('on');
  msg.textContent = 'Reading ' + f.name + '… a full book takes a minute or two the first time.';
  const body = new FormData();
  body.append('pdf', f, f.name);
  fetch('/audit', { method: 'POST', body })
    .then(r => r.json())
    .then(render)
    .catch(e => {
      status.classList.remove('on');
      out.innerHTML = '<p class="err">Something went wrong: ' + esc(e.message) + '</p>';
    });
}

function render(data) {
  status.classList.remove('on');
  if (data.error) { out.innerHTML = '<p class="err">' + esc(data.error) + '</p>'; return; }
  const rows = data.flagged.map(r =>
    '<tr><td>' + esc(r.page) + '</td><td class="brk">' + esc(r.display) + '</td>' +
    '<td>' + esc(r.rules) + '</td><td>' + esc(r.reason) + '</td></tr>').join('');
  out.innerHTML =
    '<div class="tally">' +
      '<div class="bad"><b>' + data.counts.violations + '</b>violations</div>' +
      '<div class="mid"><b>' + data.counts.needs_check + '</b>need a look</div>' +
      '<div><b>' + data.counts.advisories + '</b>advisories</div>' +
      '<div><b>' + data.counts.checked + '</b>breaks checked</div>' +
      '<div><b>' + data.counts.pages + '</b>pages</div>' +
    '</div>' +
    '<a class="dl" href="/download/' + encodeURIComponent(data.id) + '">Download the spreadsheet</a>' +
    (rows ? '<table><thead><tr><th>Page</th><th>Break</th><th>Rules</th>' +
            '<th>Why</th></tr></thead><tbody>' + rows + '</tbody></table>'
          : '<p style="margin-top:18px;color:var(--ok)">Nothing flagged.</p>') +
    (data.counts.advisories
      ? '<p style="margin-top:14px;color:var(--muted);font-size:13px;' +
        'font-family:system-ui,sans-serif">Advisories are not listed here. They are on ' +
        'their own tab in the spreadsheet, and none of them breaks a rule.</p>'
      : '');
}
</script>
</body>
</html>
"""


def _parse_upload(headers, body: bytes) -> tuple[str, bytes] | None:
    """Pull the single uploaded file out of a multipart/form-data body."""
    content_type = headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type:
        return None
    raw = b"Content-Type: " + content_type.encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    message = BytesParser(policy=default_policy).parsebytes(raw)
    for part in message.iter_parts():
        filename = part.get_filename()
        if filename:
            return unquote(filename), part.get_payload(decode=True)
    return None


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "hyphencheck"

    def log_message(self, fmt, *args):  # quieter than the default
        pass

    def _send(self, code: int, body: bytes, content_type: str, extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict):
        self._send(code, json.dumps(payload).encode(), "application/json")

    def _handle_key(self):
        """Take a Merriam-Webster key typed into the page, check it, save it."""
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            key = str(payload.get("key", ""))
        except ValueError:
            self._json(200, {"ok": False, "message": "That did not look like a key."})
            return
        try:
            ok, message = config.verify_and_save(key)
        except Exception as exc:
            ok, message = False, f"Could not reach Merriam-Webster: {exc}"
        self._json(200, {"ok": ok, "message": message})

    def do_GET(self):
        if self.path == "/":
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif self.path == "/status":
            self._json(200, {"has_key": bool(config.api_key())})
        elif self.path.startswith("/download/"):
            key = unquote(self.path.rsplit("/", 1)[-1])
            path = RESULTS.get(key)
            if not path or not path.exists():
                self._json(404, {"error": "That result has expired; run the audit again."})
                return
            self._send(
                200, path.read_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                {"Content-Disposition": f'attachment; filename="{path.name}"'},
            )
        else:
            self._json(404, {"error": "Not found"})

    def _from_this_machine(self) -> bool:
        """Reject posts from a page on some other site.

        The server listens on localhost, but any web page the user happens to
        have open can still post to localhost. Nothing here is dangerous, but
        a stray request should not be able to overwrite a saved key.
        """
        origin = self.headers.get("Origin")
        if origin is None:
            return True  # not a cross-site request
        return origin in (f"http://{self.headers.get('Host', '')}",
                          "http://localhost", "http://127.0.0.1")

    def do_POST(self):
        if not self._from_this_machine():
            self._json(403, {"error": "Refused a request from another site."})
            return
        if self.path == "/key":
            self._handle_key()
            return
        if self.path != "/audit":
            self._json(404, {"error": "Not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        upload = _parse_upload(self.headers, self.rfile.read(length))
        if not upload:
            self._json(400, {"error": "No file was received."})
            return

        filename, data = upload
        WORKDIR.mkdir(parents=True, exist_ok=True)
        job = uuid.uuid4().hex
        folder = WORKDIR / job
        folder.mkdir()
        safe = Path(filename).name or "proof.pdf"
        pdf_path = folder / safe
        pdf_path.write_bytes(data)

        try:
            key = config.api_key()
            dictionary = Dictionary(
                api_key=key, cache_path=config.CACHE_PATH,
                overrides=config.load_overrides(), offline=not key,
            )
            result = audit.run(str(pdf_path), dictionary)
            xlsx = report.write(
                result, folder / (Path(safe).stem + "_hyphenation_audit.xlsx")
            )
        except Exception as exc:  # surfaced in the page rather than the console
            shutil.rmtree(folder, ignore_errors=True)
            self._json(200, {"error": f"{type(exc).__name__}: {exc}"})
            return

        RESULTS[job] = xlsx
        counts = result.counts()
        self._json(200, {
            "id": job,
            "counts": {
                "violations": counts["Violations"],
                "needs_check": counts["Needs check"],
                "advisories": counts["Advisories"],
                "checked": counts["Real word divisions checked"],
                "pages": counts["Pages"],
            },
            "flagged": [
                {
                    "page": brk.book_page or f"pdf {brk.pdf_page}",
                    "display": brk.display,
                    "rules": brk.flagged_rules,
                    "reason": brk.reason,
                }
                for brk in sorted(
                    result.flagged,
                    key=lambda b: (int(b.book_page) if b.book_page.isdigit() else 10**6,
                                   b.line_index),
                )
            ],
        })


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> int:
    server = http.server.ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"Hyphenation Checker is running at {url}")
    print("Leave this window open while you use it. Press Ctrl-C to stop.")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
        shutil.rmtree(WORKDIR, ignore_errors=True)
    return 0
