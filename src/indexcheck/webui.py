"""A small local page for checking an index without touching a terminal.

Everything stays on this machine: the server binds to localhost and the index
never leaves the computer.
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

from . import audit
from .rules import COLOURS

RESULTS: dict[str, Path] = {}
WORKDIR = Path(tempfile.gettempdir()) / "indexcheck-ui"

#: Word's highlight names, as CSS colours, for the legend and the table.
SWATCH = {"yellow": "#f7e463", "brightGreen": "#8fe08f",
          "cyan": "#8fdcdc", "magenta": "#efa0d8"}

LABELS = {
    "entry-order": "Main entries out of order",
    "subentry-order": "Subentries out of order",
    "page-order": "Page numbers out of order",
    "range-order": "Page ranges reversed",
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
  .err { color:var(--accent); }
</style>
</head>
<body>
<div class="wrap">
  <h1>Index Checker</h1>
  <p class="sub">Drop in an index. You get the same file back with the problems
     highlighted, each one explained in a Word comment, and every mark recorded
     as a tracked change.</p>

  <div class="panel">
    <div id="drop">
      <strong>Drop a Word file here</strong>
      <span>or click to choose one</span>
      <input type="file" id="file" accept=".docx" hidden>
    </div>

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
  let data;
  try {
    data = await (await fetch('/check', {method:'POST', body})).json();
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
    '<div class="bad"><b>' + d.findings.length + '</b>to look at</div>';
  for (const [rule, n] of Object.entries(d.counts))
    html += '<div><b>' + n + '</b>' + esc(d.labels[rule] || rule) + '</div>';
  html += '</div>';

  if (d.findings.length) {
    html += '<table><tr><th>Entry</th><th>What is wrong</th></tr>';
    for (const f of d.findings.slice(0, 200)) {
      const sw = d.swatch[f.colour] || '#ccc';
      html += '<tr><td class="where"><span class="swatch" style="background:' +
              sw + '"></span>' + esc(f.entry) + '</td><td>' +
              esc(f.message) + '</td></tr>';
    }
    html += '</table>';
    if (d.findings.length > 200)
      html += '<p class="note">Showing the first 200. All of them are marked ' +
              'in the file.</p>';
  } else {
    html += '<p>Nothing to flag.</p>';
  }
  html += '<a class="dl" href="/download/' + d.id + '">Download the marked-up file</a>';
  out.innerHTML = html;
}
</script>
</body>
</html>
"""


def _parse_upload(headers, body: bytes):
    """Pull the single uploaded file out of a multipart/form-data body."""
    content_type = headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type:
        return None
    raw = (b"Content-Type: " + content_type.encode()
           + b"\r\nMIME-Version: 1.0\r\n\r\n" + body)
    message = BytesParser(policy=default_policy).parsebytes(raw)
    for part in message.iter_parts():
        filename = part.get_filename()
        if filename:
            return unquote(filename), part.get_payload(decode=True)
    return None


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "indexcheck"

    def log_message(self, fmt, *args):        # quieter than the default
        pass

    def _send(self, code, body, content_type, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, payload):
        self._send(code, json.dumps(payload).encode(), "application/json")

    def do_GET(self):
        if self.path == "/":
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif self.path.startswith("/download/"):
            key = unquote(self.path.rsplit("/", 1)[-1])
            path = RESULTS.get(key)
            if not path or not path.exists():
                self._json(404, {"error": "That result has expired; check again."})
                return
            self._send(
                200, path.read_bytes(),
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document",
                {"Content-Disposition": f'attachment; filename="{path.name}"'},
            )
        else:
            self._json(404, {"error": "Not found"})

    def _from_this_machine(self) -> bool:
        """Reject posts from a page on some other site.

        The server listens on localhost, but any page the user happens to have
        open can still post to it.
        """
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return origin in (f"http://{self.headers.get('Host', '')}",
                          "http://localhost", "http://127.0.0.1")

    def do_POST(self):
        if not self._from_this_machine():
            self._json(403, {"error": "Refused a request from another site."})
            return
        if self.path != "/check":
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
        safe = Path(filename).name or "index.docx"
        source = folder / safe
        source.write_bytes(data)

        try:
            result = audit.run(
                source, out_path=folder / (Path(safe).stem + "_checked.docx"))
        except Exception as exc:      # surfaced in the page, not the console
            shutil.rmtree(folder, ignore_errors=True)
            self._json(200, {"error": f"{type(exc).__name__}: {exc}"})
            return

        RESULTS[job] = result.path
        self._json(200, {
            "id": job,
            "entries": result.entries,
            "counts": result.counts(),
            "labels": LABELS,
            "swatch": SWATCH,
            "findings": [
                {"entry": entry, "message": finding.message,
                 "colour": finding.colour}
                for entry, finding in result.described()
            ],
        })


def serve(host: str = "127.0.0.1", port: int = 8766,
          open_browser: bool = True) -> int:
    server = http.server.ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"Index Checker is running at {url}")
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
