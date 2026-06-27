@echo off
title Building Remote Desktop EXE
echo.
echo ============================================================
echo   Building RemoteDesktop.exe — please wait...
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Download from https://python.org
    echo Make sure to check "Add to PATH" during installation!
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install pyinstaller flask flask-socketio pillow pyautogui mss pyngrok eventlet --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [2/3] Building EXE (this may take 1-3 minutes)...
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name RemoteDesktop ^
    --hidden-import flask ^
    --hidden-import flask_socketio ^
    --hidden-import engineio ^
    --hidden-import socketio ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import mss ^
    --hidden-import pyautogui ^
    --hidden-import pyngrok ^
    --hidden-import eventlet ^
    --hidden-import eventlet.hubs ^
    --hidden-import eventlet.hubs.epolls ^
    --hidden-import eventlet.hubs.kqueue ^
    --hidden-import eventlet.hubs.selects ^
    --hidden-import dns ^
    --hidden-import dns.resolver ^
    --collect-all mss ^
    --collect-all pyngrok ^
    server_standalone.py
if errorlevel 1 (
    echo [ERROR] Build failed. Check the output above.
    pause
    exit /b 1
)

echo [3/3] Done!
echo.
echo ============================================================
echo   SUCCESS! File is ready:
echo   dist\RemoteDesktop.exe
echo ============================================================
echo.
echo Send dist\RemoteDesktop.exe to your friend.
echo Your friend just double-clicks it — nothing else needed!
echo.
pause
