@echo off
setlocal

REM Build a self-contained Windows command-line executable with PyInstaller.
REM Run this file from Explorer or from cmd.exe; it always uses its own folder.
cd /d "%~dp0"

py -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo PyInstaller is not installed for the Python launcher.
    echo Install it with: py -m pip install pyinstaller
    exit /b 1
)

py -m PyInstaller --noconfirm --clean --onefile --console --name ArhivachArchive --paths "%CD%" run_archive.py
if errorlevel 1 (
    echo.
    echo Build failed.
    exit /b 1
)

echo.
echo Build completed: "%CD%\dist\ArhivachArchive.exe"
endlocal
