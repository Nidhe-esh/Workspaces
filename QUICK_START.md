# Quick Start — Workspaces

**Get started in 2 minutes!**

---

## For Users: Run the App Now

### Step 1: Open the Executable
```
📁 File: e:\Projects\Workspaces\workspaces\dist\Workspaces.exe

Simply double-click it!
(If Windows shows a warning, click "More info" → "Run anyway")
```

### Step 2: Scan Your Desktop
1. Click the **"Scan Workspace"** button
2. You'll see all your open apps listed
3. System apps are grayed out (optional to include)

### Step 3: Save the Workspace
1. Enter a name (e.g., "Development Setup")
2. Click **"Save"**
3. Done! Your workspace is saved.

### Step 4: Try Restoring
1. Close a few apps
2. Go to **"Workspaces"** tab
3. Select your saved workspace
4. Click **"Restore"**
5. ✅ All apps relaunch!

---

## For Developers: Setup & Run

### Quick Setup (< 5 minutes)

```powershell
# 1. Navigate to the project
cd e:\Projects\Workspaces\workspaces

# 2. Install packages
pip install -r requirements.txt

# 3. Run the app (native window)
python app.py

# OR run in browser with hot reload
python app.py --dev
```

Then open `http://127.0.0.1:5050` if using `--dev` mode.

---

## Common Tasks

### Test Just the Scanner
```powershell
python scraper.py
```

### Rebuild the Exe
```powershell
.\build.bat
```
Creates a new `dist/Workspaces.exe`

### Edit the Workspace Data
```json
✏ File: e:\Projects\Workspaces\workspaces\workspaces.json

Open with any text editor to manually add/edit apps
```

---

## What's Working

| Feature | Status |
|---------|--------|
| Scan apps | ✅ Works |
| Save workspace | ✅ Works |
| Restore apps | ✅ Works |
| Browser tabs | ✅ Works |
| Websites | ✅ Works |
| Data persistence | ✅ Works |
| Error handling | ✅ Works |

---

## Troubleshooting

**App didn't launch?**
- Right-click › Run as Administrator
- Make sure Python is installed (if running from source)
- Check firewall isn't blocking port 5050

**Can't find an app after restore?**
- App path may have changed
- Try re-scanning and re-saving
- Or manually edit `workspaces.json`

**Browser tabs not showing?**
- Only works if browsers have title bar access
- Chrome requires special DevTools Protocol setup
- This is normal — the app still works fine

---

## Documentation

- **README.md** — Full feature guide
- **DEV_SETUP.md** — Complete development setup
- **CHANGELOG.md** — What's new
- **IMPLEMENTATION_COMPLETE.md** — Project status

---

## File Locations

```
📁 Everything is in: e:\Projects\Workspaces\workspaces\

To run:           dist/Workspaces.exe
To develop:       app.py, scraper.py, restore.py
To edit data:     workspaces.json
To rebuild:       .\build.bat
To learn more:    README.md
```

---

## Next Steps

- ✅ **Run the app** — Open `dist/Workspaces.exe`
- 📖 **Read README** — For full feature list
- 🔧 **Modify it** — Follow DEV_SETUP.md
- 🚀 **Share it** — Upload exe to GitHub Releases

---

**That's it! You're ready to go.** 🎉

Questions? Check README.md or DEV_SETUP.md.
