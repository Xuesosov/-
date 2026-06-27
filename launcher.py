"""
Launcher — устанавливает зависимости и запускает сервер.
Запускается из ЗАПУСТИТЬ.bat / ЗАПУСТИТЬ.sh
"""
import subprocess
import sys
import os

PACKAGES = [
    'flask',
    'flask-socketio',
    'pillow',
    'pyautogui',
    'mss',
    'pyngrok',
    'eventlet',
]

def install_packages():
    print("Устанавливаю необходимые компоненты, подождите...")
    for pkg in PACKAGES:
        print(f"  Устанавливаю {pkg}...")
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', pkg, '--quiet'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    print("Все компоненты установлены!\n")

def check_packages():
    missing = []
    for pkg in ['flask', 'flask_socketio', 'PIL', 'pyautogui', 'mss', 'pyngrok', 'eventlet']:
        try:
            __import__(pkg.lower())
        except ImportError:
            missing.append(pkg)
    return missing

def start_server():
    import threading
    import time
    import webbrowser

    from pyngrok import ngrok, conf

    print("=" * 60)
    print("      УДАЛЁННЫЙ РАБОЧИЙ СТОЛ")
    print("=" * 60)
    print()

    try:
        tunnel = ngrok.connect(5000, "http")
        public_url = tunnel.public_url
        print(f"✅ Ссылка для подключения готова!")
        print()
        print(f"  👉  {public_url}")
        print()
        print("📋 Инструкция:")
        print("   1. Скопируй ссылку выше")
        print("   2. Отправь другу в мессенджере")
        print("   3. Друг откроет ссылку в браузере")
        print("   4. Готово! Друг увидит твой экран")
        print()
        print("⚠️  Не закрывай это окно — иначе соединение прервётся!")
        print()
        print("=" * 60)
    except Exception as e:
        print(f"⚠️  Не удалось создать публичную ссылку: {e}")
        print("   Используй локальный адрес: http://localhost:5000")
        print()

    def open_browser():
        time.sleep(2)
        webbrowser.open('http://localhost:5000/host')

    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    from app import socketio, app, connected_viewers

    @app.route('/api/viewers')
    def api_viewers():
        from flask import jsonify
        from app import connected_viewers as cv
        return jsonify({'count': cv})

    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    missing = check_packages()
    if missing:
        install_packages()
    start_server()
