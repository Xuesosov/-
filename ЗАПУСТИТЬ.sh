#!/bin/bash

echo ""
echo "============================================================"
echo "              УДАЛЁННЫЙ РАБОЧИЙ СТОЛ"
echo "============================================================"
echo ""

# Проверяем Python
if ! command -v python3 &>/dev/null; then
    echo "[!] Python не найден. Устанавливаю..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -q && sudo apt-get install -y python3 python3-pip
    elif command -v brew &>/dev/null; then
        brew install python3
    else
        echo "[ОШИБКА] Установи Python 3 вручную: https://python.org"
        exit 1
    fi
fi

echo "[OK] Python найден!"
echo ""
echo "Запускаю программу..."
echo ""

python3 launcher.py
