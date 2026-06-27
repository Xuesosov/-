"""
Remote Desktop — Client (friend's EXE)
Connects to the relay server, streams screen, accepts control.
Build: pyinstaller --onefile --name RemoteDesktop client_standalone.py
"""
import sys
import os
import subprocess
import threading
import time
import base64
import io
import ctypes
import ctypes.wintypes

SERVER_URL = ""  # filled at build time or entered by user

# ── Auto-install when running as .py (not frozen EXE) ─────────────────────
if not getattr(sys, 'frozen', False):
    REQUIRED = [('socketio', 'python-socketio[client]'), ('mss','mss'), ('PIL','pillow')]
    for mod, pkg in REQUIRED:
        try:
            __import__(mod)
        except ImportError:
            print(f'Installing {pkg}...')
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', pkg, '--quiet'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

import socketio as sio_module
import mss
from PIL import Image

# ── Windows mouse/keyboard via ctypes (no pyautogui needed!) ───────────────
user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE       = 0x0001
MOUSEEVENTF_LEFTDOWN   = 0x0002
MOUSEEVENTF_LEFTUP     = 0x0004
MOUSEEVENTF_RIGHTDOWN  = 0x0008
MOUSEEVENTF_RIGHTUP    = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP   = 0x0040
MOUSEEVENTF_WHEEL      = 0x0800
MOUSEEVENTF_ABSOLUTE   = 0x8000
KEYEVENTF_KEYUP        = 0x0002

VK_MAP = {
    'enter':0x0D,'backspace':0x08,'delete':0x2E,'escape':0x1B,'tab':0x09,
    'left':0x25,'right':0x27,'up':0x26,'down':0x28,
    'home':0x24,'end':0x23,'pageup':0x21,'pagedown':0x22,'space':0x20,
    'f1':0x70,'f2':0x71,'f3':0x72,'f4':0x73,'f5':0x74,'f6':0x75,
    'f7':0x76,'f8':0x77,'f9':0x78,'f10':0x79,'f11':0x7A,'f12':0x7B,
    'ctrl':0x11,'alt':0x12,'shift':0x10,'win':0x5B,
    'capslock':0x14,'insert':0x2D,'printscreen':0x2C,
}
MOD_VK = {'ctrl':0x11,'alt':0x12,'shift':0x10}

def get_screen_size():
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

def mouse_move(x, y):
    try:
        sw, sh = get_screen_size()
        ax = int(x * 65535 / sw)
        ay = int(y * 65535 / sh)
        user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, ax, ay, 0, 0)
    except Exception:
        pass

def mouse_click(x, y, button='left'):
    try:
        mouse_move(x, y)
        time.sleep(0.02)
        if button == 'left':
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_LEFTUP,   0, 0, 0, 0)
        elif button == 'right':
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP,   0, 0, 0, 0)
        elif button == 'middle':
            user32.mouse_event(MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_MIDDLEUP,   0, 0, 0, 0)
    except Exception:
        pass

def mouse_dblclick(x, y):
    mouse_click(x, y, 'left')
    time.sleep(0.05)
    mouse_click(x, y, 'left')

def mouse_scroll(delta):
    try:
        amount = -int(delta / 3)
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, ctypes.c_ulong(amount).value, 0)
    except Exception:
        pass

def key_press(key, modifiers):
    try:
        vk = VK_MAP.get(key.lower())
        if vk is None:
            if len(key) == 1:
                vk = user32.VkKeyScanW(ord(key)) & 0xFF
                if vk == 0xFF:
                    return
            else:
                return
        for mod in modifiers:
            mvk = MOD_VK.get(mod)
            if mvk:
                user32.keybd_event(mvk, 0, 0, 0)
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        for mod in reversed(modifiers):
            mvk = MOD_VK.get(mod)
            if mvk:
                user32.keybd_event(mvk, 0, KEYEVENTF_KEYUP, 0)
    except Exception:
        pass

def type_text(text):
    try:
        for ch in text:
            vk = user32.VkKeyScanW(ord(ch))
            if vk == -1:
                continue
            vk_code = vk & 0xFF
            needs_shift = (vk >> 8) & 1
            if needs_shift:
                user32.keybd_event(0x10, 0, 0, 0)
            user32.keybd_event(vk_code, 0, 0, 0)
            user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
            if needs_shift:
                user32.keybd_event(0x10, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.03)
    except Exception:
        pass

# ── Screen capture ─────────────────────────────────────────────────────────
def capture_frame(quality=55, max_width=1280):
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        img = Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=quality)
        return base64.b64encode(buf.getvalue()).decode()

# ── SocketIO client ────────────────────────────────────────────────────────
sio = sio_module.Client(
    reconnection=True,
    reconnection_attempts=20,
    reconnection_delay=2,
    logger=False,
    engineio_logger=False
)

streaming = False

@sio.event
def connect():
    global streaming
    sw, sh = get_screen_size()
    sio.emit('agent_join', {'w': sw, 'h': sh})
    streaming = True
    print('\n  [OK] Connected to server!')
    print('  Your friend can now open the browser and see your screen.\n')

@sio.event
def disconnect():
    global streaming
    streaming = False
    print('\n  [!] Disconnected from server. Reconnecting...')

@sio.on('mouse_move')
def on_mouse_move(data):
    mouse_move(data['x'], data['y'])

@sio.on('mouse_click')
def on_mouse_click(data):
    mouse_click(data['x'], data['y'], data.get('button', 'left'))

@sio.on('mouse_dblclick')
def on_mouse_dblclick(data):
    mouse_dblclick(data['x'], data['y'])

@sio.on('mouse_scroll')
def on_mouse_scroll(data):
    mouse_scroll(data.get('delta', 0))

@sio.on('key_press')
def on_key_press(data):
    key_press(data.get('key', ''), data.get('modifiers', []))

@sio.on('type_text')
def on_type_text(data):
    type_text(data.get('text', ''))

def stream_loop():
    while True:
        if streaming and sio.connected:
            try:
                frame = capture_frame()
                sio.emit('frame', {'image': frame})
            except Exception as e:
                pass
        time.sleep(0.05)

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    global SERVER_URL

    print('=' * 55)
    print('  Remote Desktop — Client')
    print('=' * 55)
    print()

    url = SERVER_URL.strip()
    if not url:
        print('  Enter server address (you got it from your friend):')
        print('  Example: https://abc123.replit.app')
        print()
        url = input('  Server URL: ').strip()
        if not url:
            print('  No URL entered. Exiting.')
            input('  Press Enter to exit...')
            return

    if not url.startswith('http'):
        url = 'https://' + url

    print(f'\n  Connecting to: {url}')
    print('  Please wait...\n')

    threading.Thread(target=stream_loop, daemon=True).start()

    while True:
        try:
            sio.connect(url, transports=['websocket', 'polling'])
            sio.wait()
        except KeyboardInterrupt:
            print('\n  Stopped.')
            break
        except Exception as e:
            print(f'  Connection error: {e}')
            print('  Retrying in 5 seconds...')
            time.sleep(5)

if __name__ == '__main__':
    main()
