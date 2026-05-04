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

try:
    from pywinauto import Desktop
except Exception:
    Desktop = None

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
    # This app should never scan itself
    "workspaces",
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

BROWSER_NAME_HINTS = {
    "arc": "Arc",
    "brave": "Brave",
    "chromium": "Chromium",
    "chrome": "Google Chrome",
    "edge": "Microsoft Edge",
    "firefox": "Mozilla Firefox",
    "librewolf": "LibreWolf",
    "maxthon": "Maxthon",
    "opera": "Opera",
    "thorium": "Thorium",
    "vivaldi": "Vivaldi",
    "waterfox": "Waterfox",
    "yandex": "Yandex Browser",
    "zen": "Zen Browser",
}

def _chrome_tabs(titles: list[str] | None = None) -> list:
    """Chrome DevTools Protocol (needs --remote-debugging-port=9222), else window titles."""
    tabs = []
    try:
        import urllib.request, json as _j
        with urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=1) as r:
            seen = set()
            for p in _j.loads(r.read()):
                if p.get("type") != "page":
                    continue
                val = (p.get("url") or p.get("title") or "").strip()
                if val.lower() in {"about:blank", "new tab", "new window"}:
                    continue
                if val and val not in seen:
                    seen.add(val)
                    tabs.append(val)
    except Exception:
        pass
    if tabs:
        return tabs
    # Fallback: parse window titles.
    return _tabs_from_titles(
        titles,
        suffix_regex=r"\s*[-—–]\s*(?:[^-—–]+[-—–]\s*)?Google Chrome(?:\s*\(.*\))?$",
        browser_label="Google Chrome",
    )


def _firefox_tabs(titles: list[str] | None = None) -> list:
    return _tabs_from_titles(
        titles,
        suffix_regex=r"\s*[-—–]\s*(?:[^-—–]+[-—–]\s*)?Mozilla Firefox(?:\s*\(Private Browsing\))?$",
        browser_label="Mozilla Firefox",
    )


def _edge_tabs(titles: list[str] | None = None) -> list:
    return _tabs_from_titles(
        titles,
        suffix_regex=r"\s*[-—–]\s*(?:[^-—–]+[-—–]\s*)?Microsoft Edge(?:\s*\(.*\))?$",
        browser_label="Microsoft Edge",
    )


def _browser_label(stem: str, proc_name: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", "", f"{stem} {proc_name}".lower())
    for hint, label in BROWSER_NAME_HINTS.items():
        if hint in compact:
            return label
    return stem.replace("_", " ").strip().title() or proc_name.replace(".exe", "").title()


def _is_browser_process(stem: str, proc_name: str) -> bool:
    compact = re.sub(r"[^a-z0-9]+", "", f"{stem} {proc_name}".lower())
    return any(hint in compact for hint in BROWSER_NAME_HINTS)


def _tabs_from_titles(titles: list[str] | None, suffix_regex: str, browser_label: str) -> list:
    tabs = []
    rx = re.compile(suffix_regex, re.IGNORECASE)
    try:
        seen = set()
        for title in titles or []:
            title = (title or "").strip()
            if not title or not rx.search(title):
                continue

            page = rx.sub("", title).strip()
            # Skip generic browser-only titles and common placeholders.
            if not page:
                continue
            if page.lower() in {
                browser_label.lower(),
                "new tab",
                "new window",
                "about:blank",
            }:
                continue
            if page not in seen:
                seen.add(page)
                tabs.append(page)
    except Exception:
        pass
    return tabs


def _uia_tabs(browser_tokens: tuple[str, ...], browser_label: str) -> list:
    """Try extracting all tab labels from browser tab strips via UI Automation."""
    if Desktop is None:
        return []

    tabs = []
    seen = set()
    try:
        windows = Desktop(backend="uia").windows(visible_only=True)
    except Exception:
        return []

    for win in windows:
        try:
            title = (win.window_text() or "").strip()
            if not title:
                continue

            pid = win.process_id()
            if not pid:
                continue

            proc_name = psutil.Process(pid).name().lower()
            if not any(tok in proc_name for tok in browser_tokens):
                continue

            for tab in win.descendants(control_type="TabItem"):
                label = (tab.window_text() or "").strip()
                if not label:
                    continue
                low = label.lower()
                if low in {
                    browser_label.lower(),
                    "new tab",
                    "new window",
                    "about:blank",
                }:
                    continue
                if label in seen:
                    continue
                seen.add(label)
                tabs.append(label)
        except Exception:
            continue

    return tabs


# ---------------------------------------------------------------------------
# Visible window enumeration (Win32 EnumWindows -- most reliable method)
# ---------------------------------------------------------------------------

def _visible_windows() -> dict:
    """Return {pid: [window_title, ...]} for all visible windows that have a title."""
    pid_to_titles: dict = {}
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
        if pid.value:
            pid_to_titles.setdefault(pid.value, []).append(title)
        return True

    user32.EnumWindows(WNDENUMPROC(_cb), 0)
    return {pid: list(dict.fromkeys(titles)) for pid, titles in pid_to_titles.items()}


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


def _browser_tabs(name: str, titles: list[str] | None = None) -> list:
    def _merge(*groups: list[str]) -> list:
        out = []
        seen = set()
        for g in groups:
            for item in g:
                val = (item or "").strip()
                if not val or val in seen:
                    continue
                seen.add(val)
                out.append(val)
        return out

    compact_name = re.sub(r"[^a-z0-9]+", "", name.lower())
    if "chrome" in compact_name or "chromium" in compact_name:
        cdp_tabs = _chrome_tabs(titles)
        title_tabs = _tabs_from_titles(titles, r"\s*[-—–]\s*Google Chrome(?:\s*\(.*\))?$", "Google Chrome")
        uia_tabs = _uia_tabs(("chrome", "brave", "opera", "vivaldi", "arc", "thorium", "chromium"), "Google Chrome")
        return _merge(cdp_tabs, uia_tabs, title_tabs)
    if "firefox" in compact_name:
        title_tabs = _firefox_tabs(titles)
        uia_tabs = _uia_tabs(("firefox", "waterfox", "librewolf"), "Mozilla Firefox")
        return _merge(uia_tabs, title_tabs)
    if "edge" in compact_name or "msedge" in compact_name:
        title_tabs = _edge_tabs(titles)
        uia_tabs = _uia_tabs(("msedge", "edge"), "Microsoft Edge")
        return _merge(uia_tabs, title_tabs)
    if _is_browser_process(name, name):
        browser_label = _browser_label(name, name)
        title_tabs = _tabs_from_titles(titles, rf"\s*[-—–]\s*{re.escape(browser_label)}(?:\s*\(.*\))?$", browser_label)
        uia_tabs = _uia_tabs((name.lower().replace("_", ""),), browser_label)
        return _merge(uia_tabs, title_tabs)
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
    pid_titles = _visible_windows()

    # Only consider PIDs that actually have a visible window
    visible_pids = set(pid_titles.keys())

    seen_exe: set = set()
    proc_rows: list[dict] = []
    titles_by_key: dict[str, list[str]] = {}
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

            # Group by exe (or proc name as fallback) to merge all window titles
            # from every visible PID of the same app (important for browsers).
            key = exe.lower() if exe else proc_name
            if not key:
                continue

            titles = pid_titles[pid]
            merged_titles = titles_by_key.setdefault(key, [])
            for t in titles:
                if t and t not in merged_titles:
                    merged_titles.append(t)

            proc_rows.append({
                "proc_name": proc_name,
                "exe": exe,
                "key": key,
            })

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    for row in proc_rows:
        try:
            key = row["key"]
            if key in seen_exe:
                continue
            seen_exe.add(key)

            proc_name = row["proc_name"]
            exe = row["exe"]
            titles = titles_by_key.get(key, [])
            title = titles[0] if titles else ""
            stem = Path(exe).stem.lower() if exe else proc_name.replace(".exe", "")

            # Exclude this app itself (packaged exe or dev python host window).
            if stem == "workspaces":
                continue
            if proc_name in {"python.exe", "pythonw.exe"} and "workspaces" in title.lower():
                continue

            # Classify as system if in system dirs or name blocklist
            is_sys = _in_system_dir(exe) or _in_name_blocklist(stem)

            name = _app_name(exe, proc_name)
            tabs = _browser_tabs(name, titles) if not is_sys else []

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