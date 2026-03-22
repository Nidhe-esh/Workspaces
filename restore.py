"""
restore.py — Workspaces
Launches saved apps with intelligent fallback logic.

STATUS: STUB — will be implemented in Step 2.
app.py returns stub results if this module raises NotImplementedError.

When implemented:
  pip install psutil

Fallback chain:
  1. Exact exe path exists → subprocess.Popen(exe_path)
  2. Look up known install locations dict (Chrome, Firefox, VSCode, etc.)
  3. Extract file path from window_title via regex → open file
  4. File missing → open parent folder
  5. Parent missing → open grandparent
  6. Nothing works → log "not found"
"""


def restore_workspace(apps: list) -> list:
    """
    Placeholder. Replace this entire function in Step 2 with real
    subprocess launch + fallback chain logic.

    Args:
        apps: list of app dicts (from workspaces.json), pre-filtered
              to only include apps where keep=True and is_system=False

    Returns:
        list of result dicts: [{ app_name, status, launched: bool }, ...]
    """
    raise NotImplementedError(
        "restore.py not yet implemented. "
        "app.py will return stub results until Step 2 is complete."
    )
