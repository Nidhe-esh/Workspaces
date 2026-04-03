# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Workspaces Windows app.

Build single-file exe:
    pyinstaller workspaces.spec

Output: dist/Workspaces.exe
"""

import os
from pathlib import Path

# Get the directory (current working directory when spec runs)
spec_dir = Path.cwd()

block_cipher = None

a = Analysis(
    [str(spec_dir / "app.py")],
    pathex=[str(spec_dir)],
    binaries=[],
    datas=[
        (str(spec_dir / "templates"), "templates"),
        (str(spec_dir / "static"), "static"),
        (str(spec_dir / "workspaces.json"), "."),
    ],
    hiddenimports=[
        "flask",
        "psutil",
        "pygetwindow",
        "webview",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Workspaces",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Optional: add icon path later
)

