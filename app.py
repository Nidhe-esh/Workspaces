"""
app.py -- Workspaces
Flask backend + pywebview native window launcher.

Run:  python app.py           (native window, no OS chrome)
      python app.py --dev     (browser only, full reload)
"""

import datetime
import json
import sys
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request

# -- pywebview ----------------------------------------------------------------
try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False


# -- Mock data ----------------------------------------------------------------

def _mock_scan() -> dict:
    return {
        "apps": [
            {
                "app_name": "google_chrome",
                "window_title": "GitHub -- Google Chrome",
                "exe_path": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                "is_system": False, "keep": True,
                "tabs": ["github.com/nidheesh/workspaces", "figma.com -- UI mockups",
                         "stackoverflow.com", "claude.ai"],
            },
            {
                "app_name": "vs_code",
                "window_title": "workspaces -- Visual Studio Code",
                "exe_path": r"C:\Users\You\AppData\Local\Programs\Microsoft VS Code\Code.exe",
                "is_system": False, "keep": True,
                "tabs": ["app.py", "scraper.py", "restore.py"],
            },
            {
                "app_name": "notion",
                "window_title": "Notion",
                "exe_path": r"C:\Users\You\AppData\Local\Programs\Notion\Notion.exe",
                "is_system": False, "keep": True, "tabs": [],
            },
            {
                "app_name": "spotify",
                "window_title": "Spotify Premium",
                "exe_path": r"C:\Users\You\AppData\Roaming\Spotify\Spotify.exe",
                "is_system": False, "keep": True, "tabs": [],
            },
            {
                "app_name": "slack",
                "window_title": "Slack",
                "exe_path": r"C:\Users\You\AppData\Local\slack\slack.exe",
                "is_system": False, "keep": True,
                "tabs": ["#general", "#dev-team"],
            },
            {
                "app_name": "nvidia_app",
                "window_title": "NVIDIA App",
                "exe_path": r"C:\Program Files\NVIDIA Corporation\NVIDIA App\NVDisplay.Container.exe",
                "is_system": True, "keep": False, "tabs": [],
            },
            {
                "app_name": "settings",
                "window_title": "Settings",
                "exe_path": "ms-settings:",
                "is_system": True, "keep": False, "tabs": [],
            },
        ]
    }


def _mock_restore(apps: list) -> list:
    return [{"app_name": a.get("app_name"), "status": "mock", "launched": False} for a in apps]


# -- Real module imports (fall back to mock silently) -------------------------

try:
    from scraper import scan_workspace as _scan
    def scan_workspace():
        try:
            return _scan()
        except Exception:
            return _mock_scan()
except ImportError:
    def scan_workspace():
        return _mock_scan()

try:
    from restore import restore_workspace as _restore
    def restore_workspace(apps):
        try:
            return _restore(apps)
        except Exception:
            return _mock_restore(apps)
except ImportError:
    def restore_workspace(apps):
        return _mock_restore(apps)


# -- Storage ------------------------------------------------------------------

DATA_FILE = Path(__file__).parent / "workspaces.json"


def load_data() -> dict:
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"workspaces": []}


def write_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# -- Flask --------------------------------------------------------------------

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


@app.route("/")
def index():
    return render_template("index.html")


# Scan
@app.route("/api/scan", methods=["POST"])
def api_scan():
    return jsonify({"ok": True, "data": scan_workspace()})


# List workspaces
@app.route("/api/workspaces", methods=["GET"])
def api_list():
    return jsonify({"ok": True, "data": load_data()["workspaces"]})


# Save workspace (full snapshot -- creates or overwrites by name)
@app.route("/api/save", methods=["POST"])
def api_save():
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get("name") or "").strip()
    apps = body.get("apps", [])
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400

    data = load_data()
    entry = {
        "name": name,
        "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "apps": apps,
    }
    idx = next((i for i, w in enumerate(data["workspaces"]) if w["name"] == name), None)
    if idx is not None:
        data["workspaces"][idx] = entry
    else:
        data["workspaces"].append(entry)

    write_data(data)
    return jsonify({"ok": True, "entry": entry})


# Add a single item (app or website) to an existing workspace
@app.route("/api/workspace/<n>/add-item", methods=["POST"])
def api_add_item(n):
    """
    Body: {
      type: "app" | "website",
      app_name: str,
      exe_path: str,      -- for apps
      url: str,           -- for websites
      label: str          -- display name for websites
    }
    Appends the item to the named workspace and saves.
    """
    data = load_data()
    ws = next((w for w in data["workspaces"] if w["name"] == n), None)
    if ws is None:
        return jsonify({"ok": False, "error": "workspace not found"}), 404

    body = request.get_json(force=True, silent=True) or {}
    item_type = body.get("type", "app")

    if item_type == "website":
        url   = (body.get("url") or "").strip()
        label = (body.get("label") or url).strip()
        if not url:
            return jsonify({"ok": False, "error": "url is required"}), 400
        item = {
            "app_name":     label or url,
            "window_title": label,
            "exe_path":     url,
            "is_system":    False,
            "keep":         True,
            "tabs":         [],
            "item_type":    "website",
            "url":          url,
        }
    else:
        app_name = (body.get("app_name") or "").strip().replace(" ", "_").lower()
        exe_path = (body.get("exe_path") or "").strip()
        if not app_name:
            return jsonify({"ok": False, "error": "app_name is required"}), 400
        item = {
            "app_name":     app_name,
            "window_title": app_name,
            "exe_path":     exe_path,
            "is_system":    False,
            "keep":         True,
            "tabs":         [],
            "item_type":    "app",
        }

    ws.setdefault("apps", []).append(item)
    write_data(data)
    return jsonify({"ok": True, "item": item})


# Delete workspace
@app.route("/api/workspace/<n>", methods=["DELETE"])
def api_delete(n):
    data = load_data()
    before = len(data["workspaces"])
    data["workspaces"] = [w for w in data["workspaces"] if w["name"] != n]
    if len(data["workspaces"]) == before:
        return jsonify({"ok": False, "error": "not found"}), 404
    write_data(data)
    return jsonify({"ok": True})


# Restore workspace
@app.route("/api/restore/<n>", methods=["POST"])
def api_restore(n):
    data = load_data()
    ws = next((w for w in data["workspaces"] if w["name"] == n), None)
    if ws is None:
        return jsonify({"ok": False, "error": "not found"}), 404
    apps_to_restore = [a for a in ws.get("apps", []) if a.get("keep", True)]
    return jsonify({"ok": True, "results": restore_workspace(apps_to_restore)})


# Health
@app.route("/api/ping")
def api_ping():
    return jsonify({"ok": True})


# -- Launcher -----------------------------------------------------------------

def _run_flask(port: int) -> None:
    app.run(port=port, debug=False, use_reloader=False, threaded=True)


def main() -> None:
    port     = 5050
    dev_mode = "--dev" in sys.argv

    if HAS_WEBVIEW and not dev_mode:
        t = threading.Thread(target=_run_flask, args=(port,), daemon=True)
        t.start()
        time.sleep(0.8)

        webview.create_window(
            title     = "Workspaces",
            url       = f"http://127.0.0.1:{port}",
            width     = 820,
            height    = 628,
            resizable = True,
            frameless = False,          # keep OS chrome (title bar, close btn)
            min_size  = (820, 600),
        )
        webview.start(debug=False)
    else:
        print(f"\n  Workspaces dev server -> http://127.0.0.1:{port}\n")
        app.run(port=port, debug=True, use_reloader=True)


if __name__ == "__main__":
    main()