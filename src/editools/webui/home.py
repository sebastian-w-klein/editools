"""The page you land on: two tools, side by side, each clearly its own thing.

They share an installation and an updater, which is a matter for whoever
maintains them. To the person checking a book they are still two tools, so
each keeps its name, its colour, and its own page.
"""

from __future__ import annotations

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Editorial Tools</title>
<style>
  :root {
    --bg:#faf9f7; --panel:#fff; --ink:#1c1b19; --muted:#6b6862;
    --line:#e3e0da; --index:#7a2e2e; --hyphen:#2a4f7c;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#1a1917; --panel:#232120; --ink:#f0ede8; --muted:#a29d95;
            --line:#3a3734; --index:#d98a8a; --hyphen:#8fb6e0; }
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:16px/1.55 Georgia,"Iowan Old Style",serif; }
  .wrap { max-width:820px; margin:0 auto; padding:64px 24px 80px; }
  h1 { font-size:32px; margin:0 0 6px; letter-spacing:-.01em; }
  .sub { color:var(--muted); margin:0 0 40px; }
  .tools { display:grid; gap:20px; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); }
  a.tool { display:block; text-decoration:none; color:inherit; background:var(--panel);
           border:1px solid var(--line); border-top:3px solid var(--tint);
           border-radius:10px; padding:28px; transition:.15s; }
  a.tool:hover { border-color:var(--tint); border-top-color:var(--tint);
                 transform:translateY(-2px); }
  a.tool.index { --tint:var(--index); }
  a.tool.hyphen { --tint:var(--hyphen); }
  a.tool h2 { margin:0 0 8px; font-size:21px; color:var(--tint); }
  a.tool p { margin:0 0 16px; font-size:15px; color:var(--muted); }
  .takes { font-family:system-ui,sans-serif; font-size:12px; letter-spacing:.04em;
           text-transform:uppercase; color:var(--muted); font-weight:600; }
  .note { margin-top:36px; font-size:13px; color:var(--muted);
          font-family:system-ui,sans-serif; }
  #update { display:none; margin:0 0 28px; padding:12px 16px;
            border:1px solid var(--line); border-left:3px solid var(--index);
            border-radius:6px; background:var(--panel); font-size:14px;
            font-family:system-ui,sans-serif; }
  #update.on { display:block; }
</style>
</head>
<body>
<div class="wrap">
  <div id="update"></div>
  <h1>Editorial Tools</h1>
  <p class="sub">Two checkers for two jobs. Pick the one you need.</p>

  <div class="tools">
    <a class="tool index" href="/index/">
      <h2>Index Checker</h2>
      <p>Checks a book index against house style. Fixes what house style
         settles, highlights what needs your judgement, and records every
         mark as a tracked change.</p>
      <span class="takes">Takes a Word file</span>
    </a>

    <a class="tool hyphen" href="/hyphen/">
      <h2>Hyphenation Checker</h2>
      <p>Finds bad end-of-line hyphen breaks in a typeset proof and gives you
         a spreadsheet of what to fix, with page numbers.</p>
      <span class="takes">Takes a PDF proof</span>
    </a>
  </div>

  <p class="note">Nothing leaves this computer. The page is served by a program
     running on your own machine.</p>
</div>

<script>
fetch('/update-status')
  .then(r => r.json())
  .then(s => {
    if (!s.available && !s.installed) return;
    const box = document.getElementById('update');
    box.innerHTML = s.installed
      ? '<b>An update was installed.</b> Close this window and open the tools '
        + 'again to start using it.'
      : '<b>A new version is available.</b> It will install by itself next time '
        + 'you open the tools.';
    box.classList.add('on');
  })
  .catch(() => {});
</script>
</body>
</html>
"""
