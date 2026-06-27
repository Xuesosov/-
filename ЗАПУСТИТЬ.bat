@echo off
chcp 65001 >nul
title Удалённый рабочий стол
color 0A

echo.
echo ============================================================
echo              УДАЛЁННЫЙ РАБОЧИЙ СТОЛ
echo ============================================================
echo.

:: Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python не найден! Устанавливаю Python...
    echo.
    
    :: Скачиваем Python установщик
    echo Скачиваю Python (это займёт минуту)...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    
    if errorlevel 1 (
        echo.
        echo [ОШИБКА] Не удалось скачать Python.
        echo Пожалуйста, скачай Python вручную с сайта: https://python.org
        echo После установки запусти этот файл снова.
        pause
        exit /b 1
    )
    
    echo Устанавливаю Python...
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1
    
    :: Обновляем PATH
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
    
    python --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [ОШИБКА] Python установлен, но не найден.
        echo Перезапусти компьютер и попробуй снова.
        pause
        exit /b 1
    )
    
    echo [OK] Python установлен!
    echo.
)

echo [OK] Python найден!
echo.
echo Запускаю программу...
echo.

python launcher.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Произошла ошибка при запуске.
    echo Попробуй запустить от имени администратора.
    pause
)
