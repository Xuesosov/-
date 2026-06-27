@echo off
title Building RemoteDesktop.exe
echo.
echo ============================================================
echo   Building RemoteDesktop.exe (minimal client)
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Download from https://python.org and check "Add to PATH"!
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
python -m pip install pyinstaller "python-socketio[client]" websocket-client mss pillow --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install packages.
    pause
    exit /b 1
)

echo [2/4] Downloading UPX compressor...
if not exist upx.exe (
    powershell -Command "try { Invoke-WebRequest -Uri 'https://github.com/upx/upx/releases/download/v4.2.4/upx-4.2.4-win64.zip' -OutFile upx.zip -TimeoutSec 30; Expand-Archive upx.zip -DestinationPath upx_tmp -Force; Copy-Item upx_tmp\upx-4.2.4-win64\upx.exe . -Force; Remove-Item upx.zip,upx_tmp -Recurse -Force; Write-Host 'UPX ready' } catch { Write-Host 'UPX skipped' }"
)

echo [3/4] Building EXE...

set UPX_FLAG=
if exist upx.exe set UPX_FLAG=--upx-dir .

python -m PyInstaller ^
    --onefile ^
    --console ^
    --name RemoteDesktop ^
    %UPX_FLAG% ^
    --hidden-import socketio ^
    --hidden-import socketio.transports ^
    --hidden-import engineio ^
    --hidden-import engineio.transports ^
    --hidden-import websocket ^
    --hidden-import mss ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.JpegImagePlugin ^
    --collect-all mss ^
    --exclude-module flask ^
    --exclude-module flask_socketio ^
    --exclude-module tkinter ^
    --exclude-module unittest ^
    --exclude-module xmlrpc ^
    --exclude-module ftplib ^
    --exclude-module imaplib ^
    --exclude-module smtplib ^
    --exclude-module pdb ^
    --exclude-module difflib ^
    --exclude-module calendar ^
    --exclude-module turtle ^
    --exclude-module curses ^
    --exclude-module eventlet ^
    --exclude-module gevent ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    --exclude-module matplotlib ^
    --exclude-module pyautogui ^
    --exclude-module pyngrok ^
    --exclude-module PIL.BmpImagePlugin ^
    --exclude-module PIL.GifImagePlugin ^
    --exclude-module PIL.PngImagePlugin ^
    --exclude-module PIL.TiffImagePlugin ^
    --exclude-module PIL.WebPImagePlugin ^
    client_standalone.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo [4/4] Cleaning up...
if exist upx.exe del upx.exe
if exist build rd /s /q build 2>nul
if exist RemoteDesktop.spec del RemoteDesktop.spec

echo.
echo ============================================================
for %%A in (dist\RemoteDesktop.exe) do (
    set size=%%~zA
    echo   SUCCESS!  dist\RemoteDesktop.exe
    echo   Size: %%~zA bytes
)
echo ============================================================
echo.
echo   Send dist\RemoteDesktop.exe to your friend via Discord.
echo   Friend runs it, types your server URL, done!
echo.
pause
