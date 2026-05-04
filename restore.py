"""
restore.py — Workspaces
Launches saved apps with intelligent fallback logic.

Fallback chain:
  1. Exact exe path exists → subprocess.Popen(exe_path)
  2. Look up known install locations dict (Chrome, Firefox, VSCode, etc.)
  3. Extract file path from window_title via regex → open file
  4. File missing → open parent folder
  5. Parent missing → open grandparent
  6. Nothing works → log result as "not_found"
  
Special handling:
  - Websites: opened via webbrowser.open(url) or os.startfile(url)
  - Apps: launched via subprocess.Popen(exe_path) with shell=True for protocol handlers
"""

import logging
import os
import re
import subprocess
import urllib.parse
import webbrowser
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)


BROWSER_NAME_HINTS = (
    "chrome",
    "chromium",
    "edge",
    "brave",
    "opera",
    "vivaldi",
    "thorium",
    "arc",
    "firefox",
    "waterfox",
    "librewolf",
)


def _normalize_url(url: str) -> str:
    """Return a browser-safe URL with a scheme when possible."""
    if not url:
        return ""
    value = url.strip()
    if not value:
        return ""
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        return value
    if value.startswith(("mailto:", "file:", "about:")):
        return value
    return f"https://{value}"


def _open_url_default(url: str) -> bool:
    """Open a URL using the user's default browser/handler."""
    target = _normalize_url(url)
    if not target:
        return False
    try:
        # On Windows this uses the user's default browser association.
        os.startfile(target)
        return True
    except Exception:
        try:
            return webbrowser.open(target)
        except Exception:
            return False


def _is_browser_item(app: dict) -> bool:
    app_name = (app.get("app_name") or "").lower()
    exe_path = (app.get("exe_path") or "").lower()
    return any(hint in app_name or hint in exe_path for hint in BROWSER_NAME_HINTS)


def _browser_urls(tabs: list) -> list[str]:
    urls = []
    seen = set()
    for tab in tabs or []:
        if not isinstance(tab, str):
            continue
        value = tab.strip()
        if not value:
            continue
        if not re.match(r"^(https?://|file:|about:|chrome://|edge://|moz-extension://|ftp://|www\.)", value, re.IGNORECASE):
            continue
        normalized = _normalize_url(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        urls.append(normalized)
    return urls


def _tab_title_fallback_urls(tabs: list) -> list[str]:
    """Convert non-URL tab labels into searchable URLs for restore fallback."""
    urls = []
    seen = set()

    for tab in tabs or []:
        if not isinstance(tab, str):
            continue

        label = tab.strip()
        if not label:
            continue

        # Skip labels that are already handled as explicit URLs.
        if re.match(r"^(https?://|file:|about:|chrome://|edge://|moz-extension://|ftp://|www\.)", label, re.IGNORECASE):
            continue

        # Domain-like labels from title parsing (e.g. "github.com").
        compact = label.lower().replace(" ", "")
        if re.match(r"^[a-z0-9.-]+\.[a-z]{2,}(/.*)?$", compact):
            candidate = _normalize_url(compact)
        else:
            # Graceful fallback: open search results for plain tab titles.
            candidate = f"https://www.google.com/search?q={urllib.parse.quote_plus(label)}"

        if candidate and candidate not in seen:
            seen.add(candidate)
            urls.append(candidate)

    return urls


def _launch_browser_tabs(app: dict, tabs: list) -> bool:
    urls = _browser_urls(tabs)
    if not urls:
        urls = _tab_title_fallback_urls(tabs)
    if not urls:
        return False

    exe_path = (app.get("exe_path") or "").strip()
    browser_name = (app.get("app_name") or "").lower()
    launch_args = None

    if exe_path and Path(exe_path).exists():
        if any(hint in browser_name or hint in exe_path.lower() for hint in ("firefox", "waterfox", "librewolf")):
            launch_args = [exe_path, "-new-window", *urls]
        else:
            launch_args = [exe_path, "--new-window", *urls]

    try:
        if launch_args:
            subprocess.Popen(launch_args)
            return True
        for url in urls:
            _open_url_default(url)
        return True
    except Exception as e:
        logger.warning("Failed to restore browser tabs for %s: %s", app.get("app_name", "unknown"), e)
        return False

# Known application installation paths (fallback dict)
KNOWN_APPS = {
    "google_chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "microsoft_edge": [
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ],
    "firefox": [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ],
    "vs_code": [
        r"C:\Users\{user}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
    ],
    "visual_studio": [
        r"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\devenv.exe",
        r"C:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\IDE\devenv.exe",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\Common7\IDE\devenv.exe",
    ],
    "notepad": [
        r"C:\Windows\System32\notepad.exe",
    ],
    "paint": [
        r"C:\Windows\System32\mspaint.exe",
    ],
    "calculator": [
        r"C:\Windows\System32\calc.exe",
    ],
    "explorer": [
        r"C:\Windows\explorer.exe",
    ],
    "spotify": [
        r"C:\Users\{user}\AppData\Roaming\Spotify\Spotify.exe",
    ],
    "slack": [
        r"C:\Users\{user}\AppData\Local\slack\slack.exe",
    ],
    "discord": [
        r"C:\Users\{user}\AppData\Local\Discord\app-1.0.9011\Discord.exe",
    ],
    "notion": [
        r"C:\Users\{user}\AppData\Local\Programs\Notion\Notion.exe",
    ],
    "whatsnew": [
        r"ms-settings:",
    ],
}


def _expand_user_path(path_str: str) -> str:
    """Replace {user} placeholder and expand ~ in paths."""
    import getpass
    username = getpass.getuser()
    expanded = path_str.replace("{user}", username)
    return str(Path(expanded).expanduser())


def _resolve_exe_path(app_name: str, exe_path: str) -> str:
    """
    Fallback chain to resolve the actual executable path.
    Returns the path if found, or None otherwise.
    """
    # Step 1: Try exact path provided
    if exe_path:
        expanded = _expand_user_path(exe_path)
        if Path(expanded).exists():
            return expanded
        # If it's a protocol handler (e.g., ms-settings:), return as-is
        if ":" in exe_path and not expanded.endswith(".exe"):
            return exe_path

    # Step 2: Look up known install locations
    app_name_lower = app_name.lower()
    if app_name_lower in KNOWN_APPS:
        for candidate in KNOWN_APPS[app_name_lower]:
            expanded = _expand_user_path(candidate)
            if Path(expanded).exists():
                return expanded

    # Step 3: Try shortcuts or common variations
    # For instance, try "app" if "app_name" doesn't match
    app_variations = [
        app_name.replace("_", " "),
        app_name.replace("_", ""),
    ]
    for var in app_variations:
        var_lower = var.lower()
        if var_lower in KNOWN_APPS and var_lower != app_name_lower:
            for candidate in KNOWN_APPS[var_lower]:
                expanded = _expand_user_path(candidate)
                if Path(expanded).exists():
                    return expanded

    return None


def _open_file_or_parent(file_path: str) -> bool:
    """
    Try to open a file with default app, or parent folder if not found.
    Returns True if successfully opened.
    """
    try:
        p = Path(file_path)
        
        # File exists → open it
        if p.exists():
            os.startfile(str(p))
            return True
        
        # Try parent folder
        if p.parent.exists():
            os.startfile(str(p.parent))
            return True
        
        # Try grandparent
        if p.parent.parent.exists():
            os.startfile(str(p.parent.parent))
            return True
    except Exception as e:
        logger.debug(f"Error opening {file_path}: {e}")
    
    return False


def restore_workspace(apps: list) -> list:
    """
    Launch saved apps with intelligent fallback chain.

    Args:
        apps: list of app dicts (from workspaces.json), pre-filtered
              to only include apps where keep=True

    Returns:
        list of result dicts: [{ app_name, status, launched: bool }, ...]
        
    Status values:
        "success":     App launched successfully
        "not_found":   Could not locate or launch app
        "website":     Website opened in default browser
    """
    results = []

    for app in apps:
        app_name = app.get("app_name", "unknown")
        exe_path = app.get("exe_path", "")
        is_website = app.get("item_type") == "website" or exe_path.startswith("http")
        window_title = app.get("window_title", "")
        tabs = app.get("tabs", [])

        result = {
            "app_name": app_name,
            "status": "unknown",
            "launched": False,
        }

        try:
            # Handle websites
            if is_website:
                url = exe_path if exe_path.startswith(("http", "www.")) else app.get("url", "")
                if url and _open_url_default(url):
                    result["status"] = "website"
                    result["launched"] = True
                else:
                    logger.warning(f"Failed to open website {url}")
                    result["status"] = "not_found"
            # Handle applications
            else:
                exe = _resolve_exe_path(app_name, exe_path)
                if exe:
                    try:
                        # Protocol handlers (e.g., ms-settings:) should use shell=True
                        if exe.endswith(":") or not exe.endswith(".exe"):
                            subprocess.Popen(exe, shell=True)
                        else:
                            subprocess.Popen(exe)
                        result["status"] = "success"
                        result["launched"] = True

                        if _is_browser_item(app) and tabs:
                            _launch_browser_tabs(app, tabs)
                    except Exception as e:
                        logger.warning(f"Failed to launch {exe}: {e}")
                        result["status"] = "not_found"
                else:
                    # Step 3: Try to extract file path from window title and open it
                    if window_title:
                        # Try to find file patterns in window title (e.g., "filename.txt - Notepad")
                        # Extract common file extensions
                        file_patterns = [
                            r"([A-Za-z0-9_\-\.]+\.py)\s*(?:[-–]|—)",
                            r"([A-Za-z0-9_\-\.]+\.js)\s*(?:[-–]|—)",
                            r"([A-Za-z0-9_\-\.]+\.txt)\s*(?:[-–]|—)",
                            r"([A-Za-z0-9_\-\.]+\.json)\s*(?:[-–]|—)",
                        ]
                        for pattern in file_patterns:
                            match = re.search(pattern, window_title)
                            if match:
                                filename = match.group(1)
                                if _open_file_or_parent(filename):
                                    result["status"] = "success"
                                    result["launched"] = True
                                    break

                    if not result["launched"]:
                        result["status"] = "not_found"

        except Exception as e:
            logger.error(f"Unexpected error restoring {app_name}: {e}")
            result["status"] = "not_found"

        results.append(result)

    return results
