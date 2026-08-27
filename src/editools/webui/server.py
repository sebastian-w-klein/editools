"""One server, one port, two tools.

Each tool owns a prefix — ``/index/`` and ``/hyphen/`` — so the two never have
to agree about a route name, and the address bar says which tool you are in.
"""

from __future__ import annotations

import shutil
import threading
import urllib.error
import urllib.request
import webbrowser

import http.server

from . import home, hyphen_page, index_page
from .. import config
from .common import WORKDIR, BaseHandler, parse_upload

#: What the launchers open, and what ``editools ui --tool`` accepts.
START_PATHS = {"home": "/", "index": "/index/", "hyphen": "/hyphen/"}

#: Set once at startup by :func:`serve`, from what the auto-update did.
UPDATE_STATE: dict = {"available": False, "installed": False}


class Handler(BaseHandler):
    def do_GET(self):
        path = self.path

        if path in ("/", ""):
            self.send_html(home.PAGE)

        elif path in ("/index", "/index/"):
            self.send_html(index_page.PAGE)
        elif path.startswith("/index/download/"):
            self.send_result(path.rsplit("/", 1)[-1], index_page.DOCX,
                             index_page.EXPIRED)

        elif path in ("/hyphen", "/hyphen/"):
            self.send_html(hyphen_page.PAGE)
        elif path == "/hyphen/status":
            self.send_json(200, {
                "has_key": bool(config.api_key()),
                "overrides_problem": config.read_overrides().problem,
            })
        elif path.startswith("/hyphen/download/"):
            self.send_result(path.rsplit("/", 1)[-1], hyphen_page.XLSX,
                             hyphen_page.EXPIRED)

        elif path == "/update-status":
            self.send_json(200, UPDATE_STATE)

        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if not self.from_this_machine():
            self.send_json(403, {"error": "Refused a request from another site."})
            return

        if self.path == "/hyphen/key":
            import json
            try:
                payload = json.loads(self.read_body() or b"{}")
                key = str(payload.get("key", ""))
            except ValueError:
                self.send_json(200, {"ok": False,
                                     "message": "That did not look like a key."})
                return
            self.send_json(200, hyphen_page.save_key(key))
            return

        if self.path not in ("/index/check", "/hyphen/audit"):
            self.send_json(404, {"error": "Not found"})
            return

        upload = parse_upload(self.headers, self.read_body())
        if not upload:
            self.send_json(400, {"error": "No file was received."})
            return
        filename, data, fields = upload

        if self.path == "/index/check":
            self.send_json(200, index_page.check(filename, data, fields))
        else:
            self.send_json(200, hyphen_page.run_audit(filename, data))


def already_running(host: str, port: int) -> bool:
    """Is one of our own servers already listening here?

    Somebody who has the tools open and double-clicks the icon again — or
    opens the other checker while the first is running — should get the page
    they asked for, not a second copy fighting for the same port. Anything
    else answering on the port is not ours and must not be mistaken for it.
    """
    try:
        request = urllib.request.Request(f"http://{host}:{port}/update-status")
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.headers.get("Server", "").startswith("editools")
    except (urllib.error.URLError, OSError):
        return False


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True,
          tool: str = "home", update_state: dict | None = None) -> int:
    """Run the tools until the window is closed.

    *tool* decides which page opens in the browser. The launchers pass one, so
    that double-clicking the Index Checker opens the Index Checker rather than
    a menu, while the tools remain reachable from one another.
    """
    if update_state:
        UPDATE_STATE.update(update_state)

    url = f"http://{host}:{port}" + START_PATHS.get(tool, "/")
    name = {"index": "Index Checker", "hyphen": "Hyphenation Checker"}.get(
        tool, "Editorial Tools")

    if already_running(host, port):
        print(f"The tools are already open. Showing the {name} in your browser.")
        print("The window that started them is the one to close when you finish.")
        if open_browser:
            webbrowser.open(url)
        return 0

    try:
        server = http.server.ThreadingHTTPServer((host, port), Handler)
    except OSError:
        print(f"Something else on this computer is already using port {port},"
              f"\nso the tools cannot start. Try again with a different one:"
              f"\n\n    editools ui --port {port + 1}\n")
        return 1

    print(f"{name} is running at {url}")
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
