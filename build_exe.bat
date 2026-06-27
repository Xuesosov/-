@echo off
title Building RemoteDesktop.exe
echo.
echo ============================================================
echo   Building RemoteDesktop.exe
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Download from https://python.org
    echo Make sure to check "Add to PATH" during install!
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
python -m pip install pyinstaller flask flask-socketio pillow pyautogui mss pyngrok --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [2/4] Downloading UPX (compressor)...
if not exist upx.exe (
    powershell -Command "try { Invoke-WebRequest -Uri 'https://github.com/upx/upx/releases/download/v4.2.4/upx-4.2.4-win64.zip' -OutFile upx.zip -TimeoutSec 30; Expand-Archive upx.zip -DestinationPath upx_tmp -Force; Copy-Item upx_tmp\upx-4.2.4-win64\upx.exe . -Force; Remove-Item upx.zip,upx_tmp -Recurse -Force } catch { Write-Host 'UPX download failed, building without compression' }"
)

echo [3/4] Building EXE (may take 2-4 minutes)...

set UPX_FLAG=
if exist upx.exe set UPX_FLAG=--upx-dir .

python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name RemoteDesktop ^
    %UPX_FLAG% ^
    --hidden-import flask ^
    --hidden-import flask_socketio ^
    --hidden-import engineio ^
    --hidden-import engineio.async_drivers.threading ^
    --hidden-import socketio ^
    --hidden-import socketio.async_drivers ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.JpegImagePlugin ^
    --hidden-import mss ^
    --hidden-import pyautogui ^
    --hidden-import pyngrok ^
    --hidden-import pyngrok.ngrok ^
    --hidden-import pyngrok.conf ^
    --collect-all mss ^
    --collect-all pyngrok ^
    --exclude-module tkinter ^
    --exclude-module unittest ^
    --exclude-module xmlrpc ^
    --exclude-module ftplib ^
    --exclude-module imaplib ^
    --exclude-module poplib ^
    --exclude-module smtplib ^
    --exclude-module telnetlib ^
    --exclude-module nntplib ^
    --exclude-module turtle ^
    --exclude-module curses ^
    --exclude-module doctest ^
    --exclude-module pdb ^
    --exclude-module difflib ^
    --exclude-module calendar ^
    --exclude-module eventlet ^
    --exclude-module gevent ^
    --exclude-module pandas ^
    --exclude-module numpy ^
    --exclude-module scipy ^
    --exclude-module matplotlib ^
    --exclude-module PIL.BmpImagePlugin ^
    --exclude-module PIL.GifImagePlugin ^
    --exclude-module PIL.PngImagePlugin ^
    --exclude-module PIL.TiffImagePlugin ^
    --exclude-module PIL.WebPImagePlugin ^
    server_standalone.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See errors above.
    pause
    exit /b 1
)

echo [4/4] Done!
echo.
echo ============================================================
echo   SUCCESS!
echo   File: dist\RemoteDesktop.exe
echo ============================================================
echo.

for %%A in (dist\RemoteDesktop.exe) do echo   Size: %%~zA bytes (~%%~zA / 1048576 MB)

echo.
echo   Send dist\RemoteDesktop.exe to your friend.
echo   Friend just double-clicks it - nothing else needed!
echo.

if exist upx.exe del upx.exe
if exist build rd /s /q build
if exist RemoteDesktop.spec del RemoteDesktop.spec

pause
