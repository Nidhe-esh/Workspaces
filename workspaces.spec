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
brand_assets = [
    spec_dir / "Workspaces.logo",
    spec_dir / "favicon.ico",
]
icon_path = next((path for path in (spec_dir / "favicon.ico",) if path.is_file()), None)

block_cipher = None

a = Analysis(
    [str(spec_dir / "app.py")],
    pathex=[str(spec_dir)],
    binaries=[],
    datas=[
        (str(spec_dir / "templates"), "templates"),
        (str(spec_dir / "static"), "static"),
        *[(str(path), path.name) for path in brand_assets if path.is_file()],
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
    icon=str(icon_path) if icon_path is not None else None,
)

