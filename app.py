"""
app.py -- Workspaces
Flask backend + pywebview native window launcher.

Run:  python app.py           (native window)
      python app.py --dev     (browser only, no pywebview needed)
"""

import datetime
import json
import sys
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request

# -- pywebview (optional) -----------------------------------------------------
try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False


# -- Mock data (used while scraper.py / restore.py are stubs) -----------------

def _mock_scan():
    return {
        "apps": [
            {
                "app_name": "google_chrome",
                "window_title": "GitHub -- Google Chrome",
                "exe_path": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                "is_system": False,
                "keep": True,
                "tabs": [
                    "github.com/nidheesh/workspaces",
                    "stackoverflow.com -- psutil docs",
                    "figma.com -- UI mockups",
                    "notion.so -- Sprint board",
                    "youtube.com -- lo-fi playlist",
                    "mail.google.com",
                    "claude.ai",
                ],
            },
            {
                "app_name": "vs_code",
                "window_title": "workspaces -- Visual Studio Code",
                "exe_path": r"C:\Users\You\AppData\Local\Programs\Microsoft VS Code\Code.exe",
                "is_system": False,
                "keep": True,
                "tabs": ["app.py", "scraper.py", "restore.py"],
            },
            {
                "app_name": "notion",
                "window_title": "Notion",
                "exe_path": r"C:\Users\You\AppData\Local\Programs\Notion\Notion.exe",
                "is_system": False,
                "keep": True,
                "tabs": [],
            },
            {
                "app_name": "spotify",
                "window_title": "Spotify Premium",
                "exe_path": r"C:\Users\You\AppData\Roaming\Spotify\Spotify.exe",
                "is_system": False,
                "keep": True,
                "tabs": [],
            },
            {
                "app_name": "slack",
                "window_title": "Slack",
                "exe_path": r"C:\Users\You\AppData\Local\slack\slack.exe",
                "is_system": False,
                "keep": True,
                "tabs": ["#general", "#dev-team"],
            },
            {
                "app_name": "nvidia_app",
                "window_title": "NVIDIA App",
                "exe_path": r"C:\Program Files\NVIDIA Corporation\NVIDIA App\NVDisplay.Container.exe",
                "is_system": True,
                "keep": False,
                "tabs": [],
            },
            {
                "app_name": "settings",
                "window_title": "Settings",
                "exe_path": "ms-settings:",
                "is_system": True,
                "keep": False,
                "tabs": [],
            },
        ]
    }


def _mock_restore(apps):
    return [
        {"app_name": a.get("app_name", "unknown"), "status": "mock", "launched": False}
        for a in apps
    ]


# -- Import real modules; fall back to mocks if stub or missing ---------------

try:
    from scraper import scan_workspace as _real_scan
    def scan_workspace():
        try:
            return _real_scan()
        except Exception:
            return _mock_scan()
except ImportError:
    def scan_workspace():
        return _mock_scan()

try:
    from restore import restore_workspace as _real_restore
    def restore_workspace(apps):
        try:
            return _real_restore(apps)
        except Exception:
            return _mock_restore(apps)
except ImportError:
    def restore_workspace(apps):
        return _mock_restore(apps)


# -- Storage ------------------------------------------------------------------

DATA_FILE = Path(__file__).parent / "workspaces.json"


def load_workspaces():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"workspaces": []}


def save_workspaces(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# -- Flask app ----------------------------------------------------------------

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/scan", methods=["POST"])
def api_scan():
    result = scan_workspace()
    return jsonify({"ok": True, "data": result})


@app.route("/api/workspaces", methods=["GET"])
def api_list_workspaces():
    data = load_workspaces()
    return jsonify({"ok": True, "data": data["workspaces"]})


@app.route("/api/save", methods=["POST"])
def api_save():
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get("name") or "").strip()
    apps = body.get("apps", [])
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    data = load_workspaces()
    entry = {
        "name": name,
        "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "apps": apps,
    }
    existing = [i for i, w in enumerate(data["workspaces"]) if w["name"] == name]
    if existing:
        data["workspaces"][existing[0]] = entry
    else:
        data["workspaces"].append(entry)
    save_workspaces(data)
    return jsonify({"ok": True, "entry": entry})


@app.route("/api/workspace/<n>", methods=["DELETE"])
def api_delete(n):
    data = load_workspaces()
    before = len(data["workspaces"])
    data["workspaces"] = [w for w in data["workspaces"] if w["name"] != n]
    if len(data["workspaces"]) == before:
        return jsonify({"ok": False, "error": "not found"}), 404
    save_workspaces(data)
    return jsonify({"ok": True})


@app.route("/api/restore/<n>", methods=["POST"])
def api_restore(n):
    data = load_workspaces()
    ws = next((w for w in data["workspaces"] if w["name"] == n), None)
    if ws is None:
        return jsonify({"ok": False, "error": "not found"}), 404
    apps_to_restore = [a for a in ws.get("apps", []) if a.get("keep", True)]
    results = restore_workspace(apps_to_restore)
    return jsonify({"ok": True, "results": results})


@app.route("/api/ping")
def api_ping():
    return jsonify({"ok": True})


# -- Launcher -----------------------------------------------------------------

def start_flask(port=5050):
    app.run(port=port, debug=False, use_reloader=False, threaded=True)


def main():
    port = 5050
    dev_mode = "--dev" in sys.argv

    if HAS_WEBVIEW and not dev_mode:
        t = threading.Thread(target=start_flask, args=(port,), daemon=True)
        t.start()
        time.sleep(0.8)
        webview.create_window(
            title="Workspaces",
            url=f"http://127.0.0.1:{port}",
            width=820,
            height=660,
            resizable=True,
            frameless=False,
            min_size=(820, 600),
        )
        webview.start(debug=False)
    else:
        print(f"\n  Workspaces dev server -> http://127.0.0.1:{port}\n")
        app.run(port=port, debug=True, use_reloader=True)


if __name__ == "__main__":
    main()
