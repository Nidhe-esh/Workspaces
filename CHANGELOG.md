# Changelog — Workspaces

All notable changes to the Workspaces project are documented in this file.

---

## [2.0.0] — 2026-06-18

**Browser restore reliability update**

### Fixes
- Fixed Brave browser restore so saved tabs reopen in the browser instead of being converted into search results.
- Improved browser restore fallback behavior when only tab titles are available.

### Packaging
- Updated the app version to `2.0.0`.
- Published the matching release build and checksum artifact.

---

## [1.0.0] — 2026-03-31

**Initial Release** 🎉

### Features
- ✨ **Scan Running Applications** — Automatically detect all running user apps with window titles
- ✨ **Browser Tab Detection** — Capture open tabs in Chrome, Firefox, and Edge
- 💾 **Save Workspaces** — Store unlimited snapshots of your desktop workspace with descriptive names
- 🚀 **One-Click Restore** — Relaunch all saved apps instantly
- 🛡️ **Smart App Resolution** — Intelligent fallback chain finds apps even if installation paths change:
  - Exact exe path matching
  - 30+ known app location database (Chrome, Firefox, VSCode, Visual Studio, Office, etc.)
  - File path extraction from window titles
  - Parent folder navigation fallback
- 🌐 **Website Support** — Save and restore bookmarked websites
- 🖥️ **Windows-Native UI** — Clean, lightweight desktop app (no browser chrome)
- 📦 **Portable Exe** — Standalone executable, no installation required
- 🔒 **Local Data** — All workspace data stored locally in `workspaces.json` (no cloud, no tracking)

### Technical
- Flask web backend
- PyWebView native window integration
- Windows Win32 API for process scanning
- Comprehensive app filtering (system vs user apps)
- Cross-instance deduplication

### Limitations
- Windows only (7 and later, tested on Windows 10/11)
- Does not persist window sizes or positions
- Requires app installation paths to remain accessible
- Browser tabs captured via DevTools Protocol (Chrome) or title bar parsing

### Known Issues
- None reported

### Installation
- **Users:** Download `Workspaces.exe` from Releases
- **Developers:** Clone repo, run `pip install -r requirements.txt`, then `python app.py`

### Build Info
- **Built with:** Python 3.12, Flask 3.1, PyWebView 6.1, PyInstaller 6.19
- **Exe Size:** ~13 MB (includes Python runtime)
- **Tested On:** Windows 11 (build 26200)

---

## [Unreleased]

### Planned for Future Releases
- [ ] Inno Setup installer (.msi) for easy uninstall
- [ ] App icon for exe
- [ ] macOS version (requires separate development)
- [ ] Linux version (requires separate development)
- [ ] Window state persistence (size, position, monitor)
- [ ] Keyboard shortcuts (Ctrl+S to save, Ctrl+R to restore)
- [ ] Drag-and-drop workspace reordering
- [ ] Website group organization
- [ ] Cloud sync (optional)
- [ ] GitHub Actions CI/CD for automated builds
- [ ] Startup mode (auto-run with Windows)
- [ ] Process tree capture (child processes)
- [ ] Command-line interface (CLI mode)

---

## Contributing

Bug reports, feature requests, and pull requests welcome on GitHub!

**To report a bug:**
1. Try the latest version from Releases
2. Provide steps to reproduce
3. Include Windows version (Settings → System → About)
4. Describe expected vs actual behavior

**To suggest a feature:**
1. Check Unreleased section above
2. Describe use case
3. Provide mockup or example if helpful

---

## License

MIT License — Free for personal and commercial use.

---

**Questions?** See [README.md](README.md) or [DEV_SETUP.md](DEV_SETUP.md)
