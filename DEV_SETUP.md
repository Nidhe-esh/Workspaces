# Development Setup — Workspaces

This guide walks through setting up Workspaces for local development and building the Windows exe.

---

## Prerequisites

- **Windows 7 or later** (development on Windows required due to Win32 API dependencies)
- **Git** (optional, for cloning repo)
- **Python 3.8 or later** (tested on Python 3.9, 3.10, 3.11)

---

## Step 1: Install Python

### Option A: From python.org (Recommended)
1. Go to https://www.python.org/downloads/
2. Download the latest Python 3.11 (or 3.9+)
3. **Important:** Check **"Add Python to PATH"** during installation
4. Click **"Install Now"**

### Option B: Using Windows Store
1. Open Windows Store
2. Search for "Python 3.11"
3. Click **"Get"**
4. Python will be added to PATH automatically

### Verify Installation
```powershell
python --version
pip --version
```

Both commands should show version numbers. If not, add Python to PATH:
- Right-click **"This PC"** → **"Properties"** → **"Advanced system settings"** → **"Environment Variables"**
- Click **"Path"** → **"Edit"** → add `C:\Users\YourUsername\AppData\Local\Programs\Python\Python311` (adjust version as needed)

---

## Step 2: Clone or Download Repository

### Option A: Using Git
```powershell
git clone https://github.com/YOUR_USERNAME/workspaces.git
cd workspaces
```

### Option B: Manual Download
1. Download the repo as ZIP from GitHub
2. Extract to `C:\Projects\Workspaces\workspaces`
3. Open PowerShell and navigate to that folder

---

## Step 3: Create Virtual Environment (Recommended)

Virtual environments isolate Python packages from your system Python, preventing conflicts.

```powershell
# Navigate to repo directory
cd path\to\workspaces

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\Activate.ps1
```

After activation, your shell prompt should show `(venv)` prefix:
```
(venv) PS C:\Projects\Workspaces\workspaces>
```

**If activation fails** due to execution policy:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Step 4: Install Dependencies

```powershell
pip install -r requirements.txt
```

This installs:
- `flask` — Web framework
- `pywebview` — Native window
- `pyinstaller` — Build tool
- `psutil` — Process scanning
- `pygetwindow` — Window detection
- `pywin32` — Windows APIs

**Troubleshooting:**
- If `pip` is slow, upgrade it: `python -m pip install --upgrade pip`
- If any package fails, try installing individually to see detailed error

---

## Step 5: Run Development Server

### Option A: Native Window (Recommended)
```powershell
python app.py
```

This launches a native desktop window with the Workspaces UI. Perfect for testing the real user experience.

### Option B: Browser with Hot Reload
```powershell
python app.py --dev
```

This runs in browser (`http://127.0.0.1:5050`) with live reload on file changes. Better for frontend development.

**To stop:** Press `Ctrl+C` in the terminal.

---

## Step 6: Test the App

### Full Workflow Test
1. **Scan:** Click "Scan Workspace" — should list your open apps
2. **Save:** Enter workspace name → click "Save"
3. **Close apps:** Close some of your running apps
4. **Restore:** Select the saved workspace → click "Restore"
5. **Verify:** All apps should relaunch

### CLI Scanner Test
```powershell
python scraper.py
```
This prints:
- User apps (count and listing)
- System apps (hidden, but shown for debugging)

### Flask API Test
```powershell
# In a new terminal, with venv activated:
curl http://127.0.0.1:5050/api/ping  # Should return {"ok": true}
curl -X POST http://127.0.0.1:5050/api/scan  # Scan workspace
```

---

## Step 7: Build Standalone Exe

### Using build.bat (Windows Only)
```powershell
# Navigate to repo
cd path\to\workspaces

# Activate venv if not already activated
venv\Scripts\Activate.ps1

# Run build script
.\build.bat
```

This will:
1. Install dependencies (if missing)
2. Clean previous builds
3. Run PyInstaller
4. Create `dist\Workspaces.exe`
5. Optionally launch the built exe

### Manual PyInstaller Build
```powershell
pyinstaller workspaces.spec
```

Output: `dist\Workspaces.exe` (~80-120 MB, one-file executable)

### Build Size Optimization
The default build bundles Python runtime (~50 MB). To reduce size:
1. Remove unused packages from `requirements.txt`
2. Use `--onefile` with UPX compression in `workspaces.spec` (requires UPX tool installed)

---

## Step 8: Code Structure Reference

### Frontend (Web UI)
- **`templates/index.html`** — HTML structure
- **`static/app.js`** — Vue.js app logic, API calls

### Backend (Flask)
- **`app.py`** — Main Flask server, API routes, pywebview launcher
- **`scraper.py`** — Windows process scanner
- **`restore.py`** — App restoration with fallback chain

### Data
- **`workspaces.json`** — Saved workspaces (auto-created on first save)

---

## Common Development Tasks

### Add a New Dependency
```powershell
pip install new_package
pip freeze > requirements.txt  # Update requirements
```

### Debug Scanner Issues
```powershell
python -c "from scraper import scan_workspace; import json; print(json.dumps(scan_workspace(), indent=2))"
```

### Modify restore.py Fallback Chain
Edit the `KNOWN_APPS` dict or fallback logic in `restore.py`. Test with:
```powershell
python app.py --dev  # Test via UI
```

### Update PyInstaller Config
1. Edit `workspaces.spec`
2. Rebuild: `pyinstaller workspaces.spec`
3. Changes to Python code don't require spec changes

---

## Troubleshooting

### Import Errors
```
ModuleNotFoundError: No module named 'flask'
```
Solution: Activate venv and reinstall: `pip install -r requirements.txt`

### PyWebView Fails
```
ImportError: No module named 'webview'
```
Solution: `pip install pywebview`

### PyInstaller Build Fails
```
ERROR: Building failed
```
Solutions:
- Delete `build/` and `dist/` folders, retry
- Update PyInstaller: `pip install --upgrade pyinstaller`
- Run with higher verbosity: `pyinstaller workspaces.spec -v`

### "No module named 'pywin32'"
Solution: `pip install pywin32` then run: `python Scripts/pywin32_postinstall.py -install` (from venv)

### App Doesn't Restore Apps
1. Run in dev mode: `python app.py --dev`
2. Check browser console (F12) for JavaScript errors
3. Check Flask server output in terminal for Python errors
4. Verify `workspaces.json` is not corrupted JSON

---

## Performance Tips

- **Scanning is slow:** Check if antivirus is interfering, or if you have 50+ apps running
- **Exe is large:** This is normal for PyInstaller bundles with Python runtime
- **Hot reload lags:** This is Flask's default behavior; use a production WSGI server for speed (future)

---

## Release Checklist

Before creating a release:

- [ ] Test full workflow (scan → save → restore)
- [ ] Test with 0 apps running, with 10+ apps running
- [ ] Test with various file paths (spaces, special chars, network drives)
- [ ] Test on a fresh Windows install (no development tools)
- [ ] Build exe runs standalone (double-click works)
- [ ] Update version in code if needed
- [ ] Test on both Windows 10 and Windows 11
- [ ] Update CHANGELOG if applicable
- [ ] Tag release: `git tag v1.0.0`
- [ ] Upload `dist\Workspaces.exe` to GitHub Releases

---

## Next Steps

- **Run app:** `python app.py` or `python app.py --dev`
- **Build exe:** `.\build.bat`
- **Read code:** Start with `app.py` to understand flow
- **Modify UI:** Edit `templates/index.html` and `static/app.js`
- **Extend scanner:** Edit `scraper.py` to detect more app types

---

## Resources

- Flask docs: https://flask.palletsprojects.com/
- PyWebView docs: https://pywebview.kivy.org/
- PyInstaller docs: https://pyinstaller.org/
- Windows API (Win32): https://docs.microsoft.com/en-us/windows/win32/

---

**Questions?** Check the main [README.md](README.md) or create an issue on GitHub.
