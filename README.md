# Workspaces — Windows Application Manager

**Save and restore your entire Windows desktop workspace with one click.**

Workspaces is a standalone Windows desktop application that captures your currently running applications, browser tabs, and files, then restores them all instantly. Perfect for:
- Switching between project setups (frontend dev, backend dev, data analysis, etc.)
- Saving specific working contexts
- Quick context switching on a shared machine
- Automating repetitive app launches

---

## Features ✨

✅ **Scan Running Apps** — Automatically detects all running user applications and ignores system background processes  
✅ **Smart Browser Tab Detection** — Captures open tabs in Chrome, Firefox, and Edge  
✅ **Save Workspaces** — Store snapshots of your desktop workspace with custom names  
✅ **Restore with One Click** — Launch all saved apps instantly (with intelligent fallback if paths change)  
✅ **Intelligent Path Resolution** — Finds apps even if installation paths change (includes 30+ known apps)  
✅ **Website Support** — Add and restore bookmarked websites  
✅ **Windows Native UI** — Desktop app (no browser chrome), lightweight and fast  

---

## Installation

### Option A: Download & Run (Recommended for Users)

1. Download **`Workspaces.exe`** from the [Releases page](../../releases)
2. Double-click to run — no installation needed (portable exe)
3. Windows may show a security warning — click **"More info"** → **"Run anyway"**

### Option B: Build From Source (For Developers)

See [DEV_SETUP.md](DEV_SETUP.md) for Python environment setup and building the exe yourself.

---

## Quick Start

### 1. Scan Your Desktop
Click **"Scan Workspace"** to capture all running apps and browser tabs. System apps are hidden by default.

### 2. Save a Workspace
- Review the scanned apps
- Give your workspace a name (e.g., "Frontend Dev", "Data Analysis")
- Click **"Save"**

### 3. Close Some Apps
Open different apps or close some. Then:

### 4. Restore Your Workspace
- From the **"Workspaces"** tab, select a saved workspace
- Click **"Restore"** to launch all apps instantly

---

## How It Works

### Scanning
**Process:**
- Enumerates all visible Windows (Win32 API `EnumWindows`)
- Matches each window to its originating process
- Extracts executable path and window title
- Detects browser tabs using DevTools Protocol or window title parsing

**System vs User Apps:**
- System apps (Windows, drivers, background services) are hidden with a "grayed" indicator
- Only user apps are saved by default (but system apps can be included if needed)
- Filtering uses both path-based (e.g., `C:\Windows\*`) and name-based rules

### Saving
Data stored in `workspaces.json`:
```json
{
  "workspaces": [
    {
      "name": "Frontend Dev",
      "saved_at": "2026-01-15T14:32:00",
      "apps": [
        {
          "app_name": "vs_code",
          "window_title": "workspaces – Visual Studio Code",
          "exe_path": "C:\\Users\\You\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
          "is_system": false,
          "keep": true,
          "tabs": ["app.py", "scraper.py", "restore.py"],
          "item_type": "app"
        }
      ]
    }
  ]
}
```

### Restoring (Fallback Chain)
When you restore, Workspaces uses an **intelligent 5-step fallback chain** to re-launch apps:

1. **Exact Exe Path** — If the saved exe path still exists, launch it directly
2. **Known App Locations** — Check 30+ standard install locations (Chrome, Firefox, VSCode, Visual Studio, Office, etc.)
3. **Path Extraction** — Parse app names to find likely install folders
4. **File Opener** — If a window title contains a filename, open that file with the default app
5. **Parent Folders** — If file is missing, open its parent folder

**Result:** Apps are restored even if you reinstalled them or moved them to a different path.

---

## File Structure

```
Workspaces/
├── app.py                    # Flask backend + pywebview launcher
├── scraper.py                # Windows process scanner
├── restore.py                # App restoration with fallback chain
├── workspaces.json           # Saved workspaces data (auto-created)
├── requirements.txt          # Python dependencies
├── workspaces.spec           # PyInstaller build config
├── build.bat                 # Windows build script
├── templates/
│   └── index.html            # Web UI
├── static/
│   └── app.js                # Frontend logic
└── README.md                 # This file
```

---

## Configuration

### Edit `workspaces.json` Manually
You can edit the JSON file directly:
- Add custom apps with specific exe paths
- Manually include/exclude apps
- Add websites with custom URLs

### Known Apps Database
The app includes install paths for 30+ popular applications (Chrome, Firefox, VSCode, Visual Studio, Spotify, Slack, Discord, Notion, etc.). The paths are checked in this order:
1. Program Files default paths
2. AppData Local paths
3. AppData Roaming paths
4. User-specific paths with `{user}` placeholder substitution

To add more known apps, edit the `KNOWN_APPS` dict in `restore.py`.

---

## Troubleshooting

### "System processes look like user apps"
Make sure Workspaces is running with appropriate permissions. Try right-clicking → "Run as Administrator".

### "App didn't launch during restore"
1. Check the restore result status next to the app name
2. If "not_found", the app installation path may have changed
3. Manually add the new exe path to `workspaces.json`
4. Or re-scan and re-save the workspace

### "Browser tabs aren't detected"
For Chrome: Tabs require DevTools Protocol or window title parsing. Make sure Chrome can be accessed via Title Bar scanning.
For other browsers: Window titles are parsed for tab names (e.g., "Tab Title — Mozilla Firefox")

### "Can't open the app"
- Ensure Python environment is set up correctly if running from source
- Check UAC (User Account Control) — some apps require elevation
- Verify app path is correct in `workspaces.json`

---

## Development

### Running in Development Mode
```bash
# Install dependencies
pip install -r requirements.txt

# Run with hot reload in browser
python app.py --dev
```

Then open http://127.0.0.1:5050 in your browser.

### Testing the Scanner
```bash
python scraper.py
```
This will print all detected apps and system apps.

### Building a New Exe
```bash
build.bat
```
This runs the PyInstaller build and creates `dist\Workspaces.exe`.

See [DEV_SETUP.md](DEV_SETUP.md) for detailed development setup instructions.

---

## Requirements

**To Run Exe:**
- Windows 7 or later (tested on Windows 10/11)
- ~50 MB disk space for the standalone exe
- No Python installation required

**To Build From Source:**
- Python 3.8 or later
- pip (usually included with Python)
- See [DEV_SETUP.md](DEV_SETUP.md) for full setup

---

## Dependencies

Built with:
- **Flask** — Web backend
- **PyWebView** — Native Windows window
- **PyInstaller** — Stand-alone exe packaging
- **psutil** — Process enumeration
- **pygetwindow** — Window title extraction
- **pywin32** — Windows API bindings

---

## License

MIT License — See LICENSE file (if included) or contact the author.

---

## Contributing

Bug reports, feature requests, and pull requests are welcome!

**Common improvements:**
- [ ] Icon for exe
- [ ] Inno Setup installer (.msi) for easy uninstall
- [ ] Keyboard shortcuts
- [ ] Website group management
- [ ] GitHub Actions CI/CD for automated builds
- [ ] Portable vs installer versions

---

## FAQ

**Q: Can I use this on a Mac or Linux?**  
A: Not currently. Workspaces uses Windows-specific APIs (Win32). A macOS version would require separate development.

**Q: Will Workspaces run at startup?**  
A: Not by default. You can add it to Windows Startup folder manually.

**Q: Can I share workspaces between users?**  
A: Yes, via the `workspaces.json` file. Just copy it to another user's Workspaces folder.

**Q: Does it track app state (window size, position)?**  
A: Currently no — it only launches apps. Future versions may capture and restore window state.

**Q: Is my data secure?**  
A: All data is stored locally in `workspaces.json`. No cloud sync or remote servers.

---

## Thanks

Built with ❤️ for Windows power users.

