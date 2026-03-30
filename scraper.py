"""
scraper.py -- Workspaces
Scans running Windows processes and returns structured app data.

Requires:
    pip install psutil pygetwindow pywin32

Called by app.py:
    from scraper import scan_workspace
    result = scan_workspace()  -> {"apps": [...]}

CLI self-test:
    python scraper.py
"""

import ctypes
import re
from pathlib import Path

import psutil
import pygetwindow as gw

# ---------------------------------------------------------------------------
# Hard-exclude paths
# Any process whose exe lives under these directories is system and skipped.
# This catches far more junk than a name-based blocklist alone.
# ---------------------------------------------------------------------------

SYSTEM_DIRS = {
    "c:\\windows",
    "c:\\windows\\system32",
    "c:\\windows\\syswow64",
    "c:\\windows\\systemapps",
    "c:\\windows\\winsxs",
    "c:\\program files\\windowsapps",
    "c:\\program files (x86)\\windowsapps",
}

# ---------------------------------------------------------------------------
# Name-based blocklist (catches anything not in system dirs but still junk)
# Keep this short -- the dir filter above does the heavy lifting.
# ---------------------------------------------------------------------------

NAME_BLOCKLIST = {
    # GPU background containers
    "nvdisplay.container", "nvcontainer", "nvspcaps64",
    "amdow", "amddvr", "cncmd",
    # Audio
    "audiodg",
    # Microsoft Office background
    "officeclicktorun",
    # OneDrive
    "onedrive",
    # Windows Security / AV
    "msmpeng", "nissrv", "antimalware",
    # Razer / Logitech / peripheral bloat
    "razercentralservice", "lghub",
    # Update agents
    "musnotification", "usocoreworker",
}

# ---------------------------------------------------------------------------
# App name aliases
# ---------------------------------------------------------------------------

ALIASES = {
    "code":         "vs_code",
    "googlechrome": "google_chrome",
    "chrome":       "google_chrome",
    "msedge":       "microsoft_edge",
    "iexplore":     "internet_explorer",
    "teams":        "ms_teams",
}

# ---------------------------------------------------------------------------
# Browser tab detection
# ---------------------------------------------------------------------------

def _chrome_tabs() -> list:
    """Chrome DevTools Protocol (needs --remote-debugging-port=9222), else window titles."""
    tabs = []
    try:
        import urllib.request, json as _j
        with urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=1) as r:
            tabs = [
                p.get("title") or p.get("url", "")
                for p in _j.loads(r.read())
                if p.get("type") == "page"
            ]
    except Exception:
        pass
    if tabs:
        return tabs
    # Fallback: parse window titles
    try:
        seen = set()
        for win in gw.getAllWindows():
            t = win.title or ""
            if t.endswith(" - Google Chrome") and len(t) > len(" - Google Chrome"):
                page = t[: -len(" - Google Chrome")].strip()
                if page and page not in seen:
                    tabs.append(page)
                    seen.add(page)
    except Exception:
        pass
    return tabs


def _firefox_tabs() -> list:
    tabs = []
    try:
        seen = set()
        for win in gw.getAllWindows():
            t = win.title or ""
            if " — Mozilla Firefox" in t or " - Mozilla Firefox" in t:
                page = re.sub(r"\s*[—\-]+\s*Mozilla Firefox$", "", t).strip()
                if page and page not in seen:
                    tabs.append(page)
                    seen.add(page)
    except Exception:
        pass
    return tabs


def _edge_tabs() -> list:
    tabs = []
    try:
        seen = set()
        for win in gw.getAllWindows():
            t = win.title or ""
            if t.endswith(" - Microsoft Edge") and len(t) > len(" - Microsoft Edge"):
                page = t[: -len(" - Microsoft Edge")].strip()
                if page and page not in seen:
                    tabs.append(page)
                    seen.add(page)
    except Exception:
        pass
    return tabs


# ---------------------------------------------------------------------------
# Visible window enumeration (Win32 EnumWindows -- most reliable method)
# ---------------------------------------------------------------------------

def _visible_windows() -> dict:
    """Return {pid: window_title} for all visible windows that have a title."""
    pid_to_title: dict = {}
    user32 = ctypes.windll.user32

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))

    def _cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        if not title:
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value and pid.value not in pid_to_title:
            pid_to_title[pid.value] = title
        return True

    user32.EnumWindows(WNDENUMPROC(_cb), 0)
    return pid_to_title


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _in_system_dir(exe: str) -> bool:
    if not exe:
        return True  # no exe = kernel thread = skip
    exe_lower = exe.lower()
    return any(exe_lower.startswith(d) for d in SYSTEM_DIRS)


def _in_name_blocklist(stem: str) -> bool:
    return stem.lower() in NAME_BLOCKLIST


def _app_name(exe: str, proc_name: str) -> str:
    stem = Path(exe).stem.lower() if exe else proc_name.replace(".exe", "").lower()
    return ALIASES.get(stem, stem.replace(" ", "_").replace("-", "_"))


def _browser_tabs(name: str) -> list:
    if "chrome" in name:
        return _chrome_tabs()
    if "firefox" in name:
        return _firefox_tabs()
    if "edge" in name or "msedge" in name:
        return _edge_tabs()
    return []


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan_workspace() -> dict:
    """
    Returns {"apps": [app_dict, ...]}
    Only processes with a visible window title pass through.
    System processes are flagged is_system=True and shown grayed.
    """
    pid_title = _visible_windows()

    # Only consider PIDs that actually have a visible window
    visible_pids = set(pid_title.keys())

    seen_exe: set = set()
    user_apps: list = []
    sys_apps: list = []

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            pid = proc.pid

            # Skip entirely if no visible window
            if pid not in visible_pids:
                continue

            proc_name = (proc.info.get("name") or "").lower()
            exe = proc.info.get("exe") or ""

            # Deduplicate by exe (or proc name as fallback)
            key = exe.lower() if exe else proc_name
            if not key or key in seen_exe:
                continue
            seen_exe.add(key)

            title = pid_title[pid]
            stem = Path(exe).stem.lower() if exe else proc_name.replace(".exe", "")

            # Classify as system if in system dirs or name blocklist
            is_sys = _in_system_dir(exe) or _in_name_blocklist(stem)

            name = _app_name(exe, proc_name)
            tabs = _browser_tabs(name) if not is_sys else []

            entry = {
                "app_name":     name,
                "window_title": title,
                "exe_path":     exe,
                "is_system":    is_sys,
                "keep":         not is_sys,
                "tabs":         tabs,
            }

            if is_sys:
                sys_apps.append(entry)
            else:
                user_apps.append(entry)

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    user_apps.sort(key=lambda x: x["app_name"])
    sys_apps.sort(key=lambda x: x["app_name"])

    return {"apps": user_apps + sys_apps}


# ---------------------------------------------------------------------------
# CLI self-test:  python scraper.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Scanning...\n")
    result = scan_workspace()
    user = [a for a in result["apps"] if not a["is_system"]]
    sys_ = [a for a in result["apps"] if     a["is_system"]]

    print(f"User apps ({len(user)}):")
    for a in user:
        tabs = f"  [{len(a['tabs'])} tabs]" if a["tabs"] else ""
        exe  = Path(a["exe_path"]).name if a["exe_path"] else "?"
        print(f"  {a['app_name']:<30} {exe}{tabs}")

    print(f"\nSystem apps shown grayed ({len(sys_)}):")
    for a in sys_:
        print(f"  {a['app_name']}")

    print()