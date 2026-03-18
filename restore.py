"""
restore.py — Module 6: Restore Engine
Re-launches apps from a saved session with smart fallback logic.
"""

import json
import os
import subprocess
import platform
import re

OS = platform.system()


def restore_session(session: dict):
    windows = session.get("windows", [])
    results = []

    for item in windows:
        exe   = item.get("exe_path", "unknown")
        title = item.get("window_title", "")
        app   = item.get("app_name", "unknown")

        status = _launch_with_fallback(exe, title, app)
        results.append({"app": app, "title": title, "status": status})
        print(f"  [{app}] {status}")

    return results


def _launch_with_fallback(exe_path, window_title, app_name):
    # Try 1: launch the exact exe path
    if exe_path and exe_path != "unknown" and os.path.exists(exe_path):
        _open(exe_path)
        return "ok — launched exe"

    # Try 2: guess the exe from common install locations
    guessed = _guess_exe(app_name)
    if guessed:
        _open(guessed)
        return f"ok — found at {guessed}"

    # Try 3: extract a file path from the window title
    file_path = _extract_path_from_title(window_title)

    if file_path:
        if os.path.isfile(file_path):
            _open(file_path)
            return f"ok — opened file: {file_path}"

        parent = os.path.dirname(file_path)
        if os.path.isdir(parent):
            _open(parent)
            return f"file missing — opened parent folder: {parent}"

        grandparent = os.path.dirname(parent)
        if os.path.isdir(grandparent):
            _open(grandparent)
            return f"folder missing — opened: {grandparent}"

    return "could not restore — not found"


def _open(path):
    if OS == "Windows":
        os.startfile(path)
    elif OS == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def _guess_exe(app_name):
    name = app_name.lower().replace(".exe", "")
    common = {
        "chrome":   r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "firefox":  r"C:\Program Files\Mozilla Firefox\firefox.exe",
        "code":     os.path.expanduser(r"~\AppData\Local\Programs\Microsoft VS Code\Code.exe"),
        "notepad":  r"C:\Windows\System32\notepad.exe",
        "explorer": r"C:\Windows\explorer.exe",
        "slack":    os.path.expanduser(r"~\AppData\Local\slack\slack.exe"),
        "spotify":  os.path.expanduser(r"~\AppData\Roaming\Spotify\Spotify.exe"),
        "discord":  os.path.expanduser(r"~\AppData\Local\Discord\app-1.0.9165\Discord.exe"),
        "notion":   os.path.expanduser(r"~\AppData\Local\Programs\Notion\Notion.exe"),
    }
    path = common.get(name)
    return path if path and os.path.exists(path) else None


def _extract_path_from_title(title):
    match = re.search(r'[A-Za-z]:\\[^\*\?"<>|\n]+', title)
    if match:
        return match.group(0).strip()
    return None


def load_sessions():
    if not os.path.exists("workspaces.json"):
        return []
    with open("workspaces.json", "r") as f:
        data = json.load(f)
    return data.get("sessions", [])