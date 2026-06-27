import sys
import os
import time
import base64
import threading
import io

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

_pyautogui = None
_mss = None
_Image = None

def _get_pyautogui():
    global _pyautogui
    if _pyautogui is None:
        import pyautogui
        pyautogui.FAILSAFE = False
        _pyautogui = pyautogui
    return _pyautogui

def _get_mss():
    global _mss
    if _mss is None:
        import mss
        _mss = mss
    return _mss

def _get_image():
    global _Image
    if _Image is None:
        from PIL import Image
        _Image = Image
    return _Image

app = Flask(__name__)
app.config['SECRET_KEY'] = 'remotedeskkey2024'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

streaming = False
stream_thread = None
connected_viewers = 0

def capture_screen():
    mss_mod = _get_mss()
    Image = _get_image()
    with mss_mod.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
        max_width = 1280
        if img.width > max_width:
            ratio = max_width / img.width
            new_h = int(img.height * ratio)
            img = img.resize((max_width, new_h), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=60)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')

def stream_loop():
    global streaming
    while streaming:
        if connected_viewers > 0:
            try:
                frame = capture_screen()
                socketio.emit('frame', {'image': frame}, namespace='/')
            except Exception:
                pass
        time.sleep(0.05)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/view')
def view():
    return render_template('viewer.html')

@app.route('/host')
def host():
    return render_template('host.html')

@app.route('/api/viewers')
def api_viewers():
    return jsonify({'count': connected_viewers})

@socketio.on('connect')
def handle_connect():
    global connected_viewers
    connected_viewers += 1

@socketio.on('disconnect')
def handle_disconnect():
    global connected_viewers
    connected_viewers = max(0, connected_viewers - 1)

@socketio.on('start_stream')
def handle_start_stream():
    global streaming, stream_thread
    streaming = True
    if stream_thread is None or not stream_thread.is_alive():
        stream_thread = threading.Thread(target=stream_loop, daemon=True)
        stream_thread.start()

@socketio.on('stop_stream')
def handle_stop_stream():
    global streaming
    streaming = False

@socketio.on('mouse_move')
def handle_mouse_move(data):
    try:
        pg = _get_pyautogui()
        x = int(data['x'])
        y = int(data['y'])
        sw, sh = pg.size()
        scale_x = data.get('scale_x', 1)
        scale_y = data.get('scale_y', 1)
        real_x = max(0, min(int(x * scale_x), sw - 1))
        real_y = max(0, min(int(y * scale_y), sh - 1))
        pg.moveTo(real_x, real_y)
    except Exception:
        pass

@socketio.on('mouse_click')
def handle_mouse_click(data):
    try:
        pg = _get_pyautogui()
        x = int(data['x'])
        y = int(data['y'])
        button = data.get('button', 'left')
        scale_x = data.get('scale_x', 1)
        scale_y = data.get('scale_y', 1)
        sw, sh = pg.size()
        real_x = max(0, min(int(x * scale_x), sw - 1))
        real_y = max(0, min(int(y * scale_y), sh - 1))
        pg.click(real_x, real_y, button=button)
    except Exception:
        pass

@socketio.on('mouse_dblclick')
def handle_mouse_dblclick(data):
    try:
        pg = _get_pyautogui()
        x = int(data['x'])
        y = int(data['y'])
        scale_x = data.get('scale_x', 1)
        scale_y = data.get('scale_y', 1)
        pg.doubleClick(int(x * scale_x), int(y * scale_y))
    except Exception:
        pass

@socketio.on('mouse_scroll')
def handle_mouse_scroll(data):
    try:
        pg = _get_pyautogui()
        delta = data.get('delta', 0)
        pg.scroll(-int(delta / 100))
    except Exception:
        pass

@socketio.on('key_press')
def handle_key_press(data):
    try:
        pg = _get_pyautogui()
        key = data.get('key', '')
        modifiers = data.get('modifiers', [])
        key_map = {
            'Enter': 'enter', 'Backspace': 'backspace', 'Delete': 'delete',
            'Escape': 'escape', 'Tab': 'tab', 'ArrowLeft': 'left',
            'ArrowRight': 'right', 'ArrowUp': 'up', 'ArrowDown': 'down',
            'Home': 'home', 'End': 'end', 'PageUp': 'pageup',
            'PageDown': 'pagedown', 'F1': 'f1', 'F2': 'f2', 'F3': 'f3',
            'F4': 'f4', 'F5': 'f5', 'F6': 'f6', 'F7': 'f7', 'F8': 'f8',
            'F9': 'f9', 'F10': 'f10', 'F11': 'f11', 'F12': 'f12',
            'Control': None, 'Shift': None, 'Alt': None, 'Meta': None,
            'CapsLock': 'capslock', ' ': 'space',
        }
        mapped_key = key_map.get(key, key.lower() if len(key) == 1 else None)
        if mapped_key is None:
            return
        keys_to_press = []
        if 'ctrl' in modifiers:
            keys_to_press.append('ctrl')
        if 'alt' in modifiers:
            keys_to_press.append('alt')
        if 'shift' in modifiers:
            keys_to_press.append('shift')
        keys_to_press.append(mapped_key)
        if len(keys_to_press) > 1:
            pg.hotkey(*keys_to_press)
        else:
            pg.press(mapped_key)
    except Exception:
        pass

@socketio.on('type_text')
def handle_type_text(data):
    try:
        pg = _get_pyautogui()
        text = data.get('text', '')
        pg.typewrite(text, interval=0.02)
    except Exception:
        pass

if __name__ == '__main__':
    print('\n' + '=' * 50)
    print('  Удалённый рабочий стол запущен!')
    print('=' * 50)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
