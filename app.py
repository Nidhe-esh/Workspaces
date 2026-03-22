"""
app.py — Workspaces
Flask backend + pywebview native window launcher.

Run:  python app.py
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request

# ── pywebview is optional during development ──────────────────────────────────
try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

# ── Stub imports (will be real modules after Steps 1 & 2) ────────────────────
try:
    from scraper import scan_workspace
except ImportError:
    def scan_workspace():
        """Placeholder until scraper.py is built in Step 1."""
        return {
            "apps": [
                {
                    "app_name": "google_chrome",
                    "window_title": "GitHub — Google Chrome",
                    "exe_path": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    "is_system": False,
                    "keep": True,
                    "tabs": [
                        "github.com/nidheesh/workspaces",
                        "stackoverflow.com — psutil docs",
                        "figma.com — UI mockups",
                        "notion.so — Sprint board",
                        "youtube.com — lo-fi playlist",
                        "mail.google.com",
                        "claude.ai",
                    ],
                },
                {
                    "app_name": "vs_code",
                    "window_title": "workspaces — Visual Studio Code",
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
                # system apps (shown grayed, excluded from saves)
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

try:
    from restore import restore_workspace
except ImportError:
    def restore_workspace(apps):
        """Placeholder until restore.py is built in Step 2."""
        results = []
        for app in apps:
            results.append({
                "app_name": app.get("app_name", "unknown"),
                "status": "stub — restore.py not yet built",
                "launched": False,
            })
        return results


# ── Storage ───────────────────────────────────────────────────────────────────
DATA_FILE = Path(__file__).parent / "workspaces.json"


def load_workspaces() -> dict:
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"workspaces": []}


def save_workspaces(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


@app.route("/")
def index():
    return render_template("index.html")


# ── API: Scan ─────────────────────────────────────────────────────────────────
@app.route("/api/scan", methods=["POST"])
def api_scan():
    """
    Calls scraper.scan_workspace() and returns open apps.
    Stub data is returned until Step 1 replaces scan_workspace().
    """
    try:
        result = scan_workspace()
        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── API: List workspaces ──────────────────────────────────────────────────────
@app.route("/api/workspaces", methods=["GET"])
def api_list_workspaces():
    data = load_workspaces()
    return jsonify({"ok": True, "data": data["workspaces"]})


# ── API: Save workspace ───────────────────────────────────────────────────────
@app.route("/api/save", methods=["POST"])
def api_save():
    """
    Body: { name: str, apps: [...] }
    Creates or overwrites a workspace entry in workspaces.json.
    """
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get("name") or "").strip()
    apps = body.get("apps", [])

    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    if not isinstance(apps, list):
        return jsonify({"ok": False, "error": "apps must be a list"}), 400

    data = load_workspaces()

    # Build entry
    import datetime
    entry = {
        "name": name,
        "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "apps": apps,
    }

    # Overwrite if name already exists, else append
    existing = [i for i, w in enumerate(data["workspaces"]) if w["name"] == name]
    if existing:
        data["workspaces"][existing[0]] = entry
    else:
        data["workspaces"].append(entry)

    save_workspaces(data)
    return jsonify({"ok": True, "entry": entry})


# ── API: Delete workspace ─────────────────────────────────────────────────────
@app.route("/api/workspace/<name>", methods=["DELETE"])
def api_delete(name: str):
    data = load_workspaces()
    before = len(data["workspaces"])
    data["workspaces"] = [w for w in data["workspaces"] if w["name"] != name]
    if len(data["workspaces"]) == before:
        return jsonify({"ok": False, "error": "workspace not found"}), 404
    save_workspaces(data)
    return jsonify({"ok": True})


# ── API: Restore workspace ────────────────────────────────────────────────────
@app.route("/api/restore/<name>", methods=["POST"])
def api_restore(name: str):
    """
    Calls restore.restore_workspace() for each app in the named workspace.
    Stub results are returned until Step 2 replaces restore_workspace().
    """
    data = load_workspaces()
    ws = next((w for w in data["workspaces"] if w["name"] == name), None)
    if ws is None:
        return jsonify({"ok": False, "error": "workspace not found"}), 404

    apps_to_restore = [a for a in ws.get("apps", []) if a.get("keep", True)]

    try:
        results = restore_workspace(apps_to_restore)
        return jsonify({"ok": True, "results": results})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── API: Health check ─────────────────────────────────────────────────────────
@app.route("/api/ping")
def api_ping():
    return jsonify({"ok": True, "message": "Workspaces backend running"})


# ── Launcher ──────────────────────────────────────────────────────────────────
def start_flask(port: int = 5050) -> None:
    """Run Flask in a background thread (used when pywebview is present)."""
    app.run(port=port, debug=False, use_reloader=False, threaded=True)


def main() -> None:
    port = 5050
    dev_mode = "--dev" in sys.argv  # python app.py --dev → browser only

    if HAS_WEBVIEW and not dev_mode:
        # Production: Flask in background thread, pywebview as the window
        t = threading.Thread(target=start_flask, args=(port,), daemon=True)
        t.start()
        time.sleep(0.8)  # let Flask boot before opening window

        window = webview.create_window(
            title="Workspaces",
            url=f"http://127.0.0.1:{port}",
            width=820,
            height=626,        # titlebar + layout height
            resizable=False,
            frameless=False,   # OS chrome; set True for custom titlebar later
            min_size=(820, 626),
        )
        webview.start(debug=False)

    else:
        # Dev mode or no pywebview: just run Flask, open browser manually
        print(f"\n  Workspaces dev server → http://127.0.0.1:{port}")
        print("  (install pywebview for native window, or pass --dev to skip it)\n")
        app.run(port=port, debug=True, use_reloader=True)


if __name__ == "__main__":
    main()
