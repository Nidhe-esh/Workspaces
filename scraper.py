"""
scraper.py — Module 2: System Scraper
Captures all open windows and saves them to workspaces.json
"""

import psutil
import json
import os
import platform
from datetime import datetime

OS = platform.system()

def get_open_windows():
    windows = []
    if OS == "Windows":
        windows = _get_windows_windows()
    return windows


def _get_windows_windows():
    import pygetwindow as gw

    results = []
    all_windows = gw.getAllWindows()

    for win in all_windows:
        title = win.title.strip()
        if not title:
            continue

        exe_path = "unknown"
        app_name = "unknown"

        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                proc_name = proc.info['name'] or ""
                if proc_name.replace(".exe", "").lower() in title.lower():
                    exe_path = proc.info.get('exe') or "unknown"
                    app_name = proc_name.replace(".exe", "")
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        results.append({
            "app_name": app_name,
            "window_title": title,
            "pid": None,
            "exe_path": exe_path
        })

    return results


def save_snapshot(session_name: str = None):
    if not session_name:
        session_name = datetime.now().strftime("Session %Y-%m-%d %H:%M")

    print(f"Capturing workspace: '{session_name}' ...")
    windows = get_open_windows()

    session = {
        "name": session_name,
        "timestamp": datetime.now().isoformat(),
        "os": OS,
        "windows": windows
    }

    json_path = "workspaces.json"
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            data = json.load(f)
    else:
        data = {"sessions": []}

    data["sessions"].append(session)

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved {len(windows)} windows to {json_path}")
    return session