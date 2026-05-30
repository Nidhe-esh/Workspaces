"""
app.py -- Workspaces
Flask backend + pywebview native window launcher.

Run:  python app.py           (native window, no OS chrome)
      python app.py --dev     (browser only, full reload)
"""

import datetime
import json
import logging
import os
import re
import sys
import threading
import time
from html import escape
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file

# -- pywebview ----------------------------------------------------------------
try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False


# -- Runtime flags -------------------------------------------------------------

ALLOW_MOCK_FALLBACK = os.getenv("WORKSPACES_ALLOW_MOCK_FALLBACK", "0") == "1"
MAX_WORKSPACES = 500
MAX_APPS_PER_WORKSPACE = 500
MAX_STR_LEN = 2048
MAX_NAME_LEN = 120
NAME_RX = re.compile(r"^[\w .\-]{1,120}$")
DATA_LOCK = threading.Lock()
APP_DIR = Path(__file__).resolve().parent
BRAND_ASSET_NAMES = ("Workspaces.logo", "favicon.ico")
VERSION = "1.0.0"
RELEASES_URL = "https://github.com/Nidhe-esh/Workspaces/releases/latest"


# -- Logging -------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("workspaces")


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
            logger.exception("scan_workspace failed")
            if ALLOW_MOCK_FALLBACK:
                return _mock_scan()
            raise
except ImportError:
    def scan_workspace():
        if not ALLOW_MOCK_FALLBACK:
            raise RuntimeError("scanner module unavailable")
        return _mock_scan()

try:
    from restore import restore_workspace as _restore
    def restore_workspace(apps):
        try:
            return _restore(apps)
        except Exception:
            logger.exception("restore_workspace failed")
            if ALLOW_MOCK_FALLBACK:
                return _mock_restore(apps)
            raise
except ImportError:
    def restore_workspace(apps):
        if not ALLOW_MOCK_FALLBACK:
            raise RuntimeError("restore module unavailable")
        return _mock_restore(apps)


# -- Storage ------------------------------------------------------------------

APP_DATA_DIR = Path(os.getenv("APPDATA") or (Path.home() / "AppData" / "Roaming")) / "Workspaces"
DATA_FILE = APP_DATA_DIR / "workspaces.json"
DEFAULT_SETTINGS = {
    "auto_detect_browser_tabs": True,
    "show_system_apps": True,
    "auto_save_on_toggle": True,
    "dark_mode": False,
}


def _legacy_data_file() -> Path:
    return Path(__file__).resolve().parent / "workspaces.json"


def _safe_text(value, *, max_len=MAX_STR_LEN) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text


def _safe_name(value: str) -> str:
    name = _safe_text(value, max_len=MAX_NAME_LEN)
    if not name:
        raise ValueError("name is required")
    if not NAME_RX.match(name):
        raise ValueError("name contains invalid characters")
    return name


def _safe_bool(value, default=True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _validate_app_item(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("invalid app item")

    item_type = _safe_text(raw.get("item_type"), max_len=20).lower() or "app"
    if item_type not in {"app", "website"}:
        item_type = "app"

    app_name = _safe_text(raw.get("app_name"), max_len=200)
    window_title = _safe_text(raw.get("window_title"), max_len=300)
    exe_path = _safe_text(raw.get("exe_path"), max_len=MAX_STR_LEN)
    url = _safe_text(raw.get("url"), max_len=MAX_STR_LEN)

    if item_type == "website":
        if not url:
            # Preserve compatibility with existing website entries that keep URL in exe_path.
            url = exe_path
        if not url:
            raise ValueError("website url is required")
        if not app_name:
            app_name = url
        if not window_title:
            window_title = app_name
        exe_path = url
    else:
        if not app_name:
            raise ValueError("app_name is required")

    tabs_raw = raw.get("tabs", [])
    tabs = []
    if isinstance(tabs_raw, list):
        tabs = [_safe_text(t, max_len=MAX_STR_LEN) for t in tabs_raw if _safe_text(t, max_len=MAX_STR_LEN)]

    return {
        "app_name": app_name,
        "window_title": window_title,
        "exe_path": exe_path,
        "is_system": _safe_bool(raw.get("is_system"), default=False),
        "keep": _safe_bool(raw.get("keep"), default=True),
        "tabs": tabs,
        "item_type": item_type,
        "url": url if item_type == "website" else "",
    }


def _validate_workspace_entry(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("invalid workspace entry")

    name = _safe_name(raw.get("name", ""))
    saved_at = _safe_text(raw.get("saved_at"), max_len=40) or datetime.datetime.now().isoformat(timespec="seconds")

    apps_raw = raw.get("apps", [])
    if not isinstance(apps_raw, list):
        raise ValueError("apps must be a list")

    apps = []
    for item in apps_raw[:MAX_APPS_PER_WORKSPACE]:
        apps.append(_validate_app_item(item))

    return {
        "name": name,
        "saved_at": saved_at,
        "apps": apps,
    }


def _validate_settings(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return dict(DEFAULT_SETTINGS)
    settings = dict(DEFAULT_SETTINGS)
    for k in DEFAULT_SETTINGS:
        settings[k] = _safe_bool(raw.get(k), default=DEFAULT_SETTINGS[k])
    return settings


def load_data() -> dict:
    base = {"workspaces": [], "settings": dict(DEFAULT_SETTINGS)}
    if not DATA_FILE.exists():
        legacy_file = _legacy_data_file()
        if legacy_file != DATA_FILE and legacy_file.exists():
            try:
                with open(legacy_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    workspaces = raw.get("workspaces", [])
                    if isinstance(workspaces, list):
                        cleaned = []
                        for ws in workspaces[:MAX_WORKSPACES]:
                            try:
                                cleaned.append(_validate_workspace_entry(ws))
                            except Exception:
                                logger.warning("Dropping invalid legacy workspace entry")
                        settings = _validate_settings(raw.get("settings", {}))
                        data = {"workspaces": cleaned, "settings": settings}
                        write_data(data)
                        return data
            except Exception:
                logger.exception("Failed to migrate legacy data file: %s", legacy_file)
        return base

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        logger.exception("Failed to read data file: %s", DATA_FILE)
        return base

    if not isinstance(raw, dict):
        logger.warning("Invalid data file structure (root not object)")
        return base

    workspaces = raw.get("workspaces", [])
    if not isinstance(workspaces, list):
        logger.warning("Invalid data file structure (workspaces not list)")
        return base

    cleaned = []
    for ws in workspaces[:MAX_WORKSPACES]:
        try:
            cleaned.append(_validate_workspace_entry(ws))
        except Exception:
            logger.warning("Dropping invalid workspace entry")

    settings = _validate_settings(raw.get("settings", {}))
    return {"workspaces": cleaned, "settings": settings}


def write_data(data: dict) -> None:
    parent = DATA_FILE.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp_file = parent / f"{DATA_FILE.name}.tmp"

    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp_file, DATA_FILE)


# -- Flask --------------------------------------------------------------------

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


def _api_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def _find_brand_asset(*, prefer_ico: bool = False) -> Path | None:
    names = BRAND_ASSET_NAMES if not prefer_ico else ("favicon.ico", "Workspaces.logo")
    for name in names:
        candidate = APP_DIR / name
        if candidate.is_file():
            return candidate
    return None


def _brand_svg() -> str:
    title = escape("Workspaces")
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 256 256' role='img' aria-label='Workspaces'>"
        "<rect width='256' height='256' rx='48' fill='#111111'/>"
        "<rect x='24' y='24' width='208' height='208' rx='40' fill='none' stroke='#2e2e2e' stroke-width='4'/>"
        "<path d='M56 74 86 182 128 96 170 182 200 74' fill='none' stroke='#2a2a2a' stroke-width='28' stroke-linecap='round' stroke-linejoin='round' opacity='.9'/>"
        "<path d='M56 70 86 178 128 92 170 178 200 70' fill='none' stroke='#f5f5f5' stroke-width='20' stroke-linecap='round' stroke-linejoin='round'/>"
        f"<text x='128' y='220' text-anchor='middle' font-family='Arial, sans-serif' font-size='24' font-weight='700' fill='#f5f5f5'>{title}</text>"
        "</svg>"
    )


def _brand_svg_response():
    return Response(_brand_svg(), mimetype="image/svg+xml")


@app.route("/brand-mark")
@app.route("/brand-mark.svg")
def brand_mark():
    asset = _find_brand_asset()
    if asset is not None:
        mimetype = "image/svg+xml" if asset.name == "Workspaces.logo" else None
        return send_file(asset, mimetype=mimetype)
    return _brand_svg_response()


@app.route("/favicon")
@app.route("/favicon.svg")
def favicon_svg():
    asset = _find_brand_asset()
    if asset is not None:
        mimetype = "image/svg+xml" if asset.name == "Workspaces.logo" else "image/x-icon"
        return send_file(asset, mimetype=mimetype)
    return _brand_svg_response()


@app.route("/favicon.ico")
def favicon_ico():
    asset = _find_brand_asset(prefer_ico=True)
    if asset is not None:
        mimetype = "image/x-icon"
        if asset.name == "Workspaces.logo":
            mimetype = "image/svg+xml"
        return send_file(asset, mimetype=mimetype)
    return _brand_svg_response()


@app.errorhandler(Exception)
def handle_unexpected_error(err):
    logger.exception("Unhandled server error")
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "internal server error"}), 500
    raise err


@app.route("/")
def index():
    return render_template("index.html")


# Scan
@app.route("/api/scan", methods=["POST"])
def api_scan():
    return jsonify({"ok": True, "data": scan_workspace()})


@app.route("/api/version", methods=["GET"])
def api_version():
    return jsonify({"ok": True, "version": VERSION, "release_url": RELEASES_URL})


# List workspaces
@app.route("/api/workspaces", methods=["GET"])
def api_list():
    with DATA_LOCK:
        data = load_data()
    return jsonify({"ok": True, "data": data["workspaces"]})


@app.route("/api/workspaces", methods=["DELETE"])
def api_delete_all():
    with DATA_LOCK:
        current = load_data()
        data = {"workspaces": [], "settings": current.get("settings", dict(DEFAULT_SETTINGS))}
        write_data(data)
    return jsonify({"ok": True})


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    with DATA_LOCK:
        data = load_data()
    return jsonify({"ok": True, "data": data.get("settings", dict(DEFAULT_SETTINGS))})


@app.route("/api/settings", methods=["POST"])
def api_set_settings():
    body = request.get_json(silent=True) or {}
    incoming = body.get("settings", body)
    with DATA_LOCK:
        data = load_data()
        merged = dict(data.get("settings", dict(DEFAULT_SETTINGS)))
        if isinstance(incoming, dict):
            for k in DEFAULT_SETTINGS:
                if k in incoming:
                    merged[k] = _safe_bool(incoming.get(k), default=DEFAULT_SETTINGS[k])
        data["settings"] = _validate_settings(merged)
        write_data(data)
    return jsonify({"ok": True, "data": data["settings"]})


# Save workspace (full snapshot -- creates or overwrites by name)
@app.route("/api/save", methods=["POST"])
def api_save():
    body = request.get_json(silent=True) or {}
    try:
        name = _safe_name(body.get("name", ""))
        apps_raw = body.get("apps", [])
        if not isinstance(apps_raw, list):
            return _api_error("apps must be a list")
        apps = [_validate_app_item(a) for a in apps_raw[:MAX_APPS_PER_WORKSPACE]]
    except ValueError as exc:
        return _api_error(str(exc))

    with DATA_LOCK:
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
            if len(data["workspaces"]) >= MAX_WORKSPACES:
                return _api_error("workspace limit reached", 409)
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
    body = request.get_json(silent=True) or {}
    item_type = _safe_text(body.get("type", "app"), max_len=20).lower() or "app"

    if item_type == "website":
        candidate = {
            "item_type": "website",
            "app_name": _safe_text(body.get("label") or body.get("url"), max_len=200),
            "window_title": _safe_text(body.get("label") or body.get("url"), max_len=300),
            "exe_path": _safe_text(body.get("url"), max_len=MAX_STR_LEN),
            "url": _safe_text(body.get("url"), max_len=MAX_STR_LEN),
            "is_system": False,
            "keep": True,
            "tabs": [],
        }
    else:
        app_name = _safe_text(body.get("app_name"), max_len=200).replace(" ", "_").lower()
        candidate = {
            "item_type": "app",
            "app_name": app_name,
            "window_title": app_name,
            "exe_path": _safe_text(body.get("exe_path"), max_len=MAX_STR_LEN),
            "is_system": False,
            "keep": True,
            "tabs": [],
        }

    try:
        item = _validate_app_item(candidate)
    except ValueError as exc:
        return _api_error(str(exc))

    with DATA_LOCK:
        data = load_data()
        ws = next((w for w in data["workspaces"] if w["name"] == n), None)
        if ws is None:
            return jsonify({"ok": False, "error": "workspace not found"}), 404
        apps = ws.setdefault("apps", [])
        if len(apps) >= MAX_APPS_PER_WORKSPACE:
            return _api_error("app limit reached", 409)
        apps.append(item)
        write_data(data)

    return jsonify({"ok": True, "item": item})


# Delete workspace
@app.route("/api/workspace/<n>", methods=["DELETE"])
def api_delete(n):
    with DATA_LOCK:
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
    with DATA_LOCK:
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


@app.route("/api/storage-location", methods=["GET"])
def api_storage_location():
    return jsonify({"ok": True, "path": str(DATA_FILE.resolve())})


@app.route("/api/storage-location/open", methods=["POST"])
def api_open_storage_location():
    try:
        folder = APP_DATA_DIR.resolve()
        if hasattr(os, "startfile"):
            os.startfile(str(folder))
        else:
            return _api_error("open folder is only supported on Windows", 400)
        return jsonify({"ok": True, "path": str(folder)})
    except Exception as e:
        logger.exception("Failed to open storage location")
        return jsonify({"ok": False, "error": str(e)}), 500


# -- Launcher -----------------------------------------------------------------

def _run_flask(port: int) -> None:
    app.run(port=port, debug=False, use_reloader=False, threaded=True)


def main() -> None:
    port     = 5050
    dev_mode = "--dev" in sys.argv

    if dev_mode and not ALLOW_MOCK_FALLBACK:
        logger.info("Dev mode enabled; mock fallback can be enabled with WORKSPACES_ALLOW_MOCK_FALLBACK=1")

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
            frameless = False,
            min_size  = (820, 600),
        )
        webview.start(debug=False)
    else:
        print(f"\n  Workspaces dev server -> http://127.0.0.1:{port}\n")
        app.run(port=port, debug=True, use_reloader=True)


if __name__ == "__main__":
    main()