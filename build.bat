@echo off
REM build.bat - Workspaces Windows Build Script
REM Usage: build.bat

setlocal enabledelayedexpansion

echo.
echo =========================================================
echo  Workspaces Build Script for Windows
echo =========================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo [1/5] Python found:
python --version

echo.
echo [2/5] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [3/5] Cleaning previous builds...
rmdir /s /q build dist 2>nul
if exist *.spec (
    echo Keeping existing spec file
)

echo.
echo [4/5] Building Workspaces.exe...
pyinstaller workspaces.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo [5/5] Build complete!
echo.
echo =========================================================
echo  Workspaces.exe created in: dist\Workspaces.exe
echo =========================================================
echo.

REM Offer to run the built exe
set /p RUN="Run Workspaces now? (y/n): "
if /i "!RUN!"=="y" (
    start "" dist\Workspaces.exe
)

pause
