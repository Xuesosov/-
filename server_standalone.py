"""
Standalone Remote Desktop Server
Builds into a single EXE via PyInstaller.
All HTML is embedded — no external files needed.
"""

import sys
import os
import subprocess
import threading
import time
import base64
import io
import socket

# ── Auto-install missing packages (when run as .py, not .exe) ──────────────
if not getattr(sys, 'frozen', False):
    REQUIRED = [
        ('flask', 'flask'),
        ('flask_socketio', 'flask-socketio'),
        ('PIL', 'pillow'),
        ('mss', 'mss'),
        ('pyngrok', 'pyngrok'),
        ('eventlet', 'eventlet'),
    ]
    for mod, pkg in REQUIRED:
        try:
            __import__(mod)
        except ImportError:
            print(f'Installing {pkg}...')
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', pkg, '--quiet'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

# ── Lazy screen / input helpers ────────────────────────────────────────────
_pg = None
_mss_mod = None
_Image = None

def get_pg():
    global _pg
    if _pg is None:
        import pyautogui
        pyautogui.FAILSAFE = False
        _pg = pyautogui
    return _pg

def get_mss():
    global _mss_mod
    if _mss_mod is None:
        import mss
        _mss_mod = mss
    return _mss_mod

def get_image():
    global _Image
    if _Image is None:
        from PIL import Image
        _Image = Image
    return _Image

# ── Embedded HTML ──────────────────────────────────────────────────────────
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Remote Desktop</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);min-height:100vh;
display:flex;align-items:center;justify-content:center;
font-family:'Segoe UI',sans-serif;color:#fff}
.c{text-align:center;padding:40px;max-width:600px;width:90%}
.logo{font-size:64px;margin-bottom:16px}
h1{font-size:32px;margin-bottom:10px;font-weight:700}
.sub{font-size:16px;color:#a0aec0;margin-bottom:50px}
a.card{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);
border-radius:20px;padding:36px;margin-bottom:20px;cursor:pointer;
transition:all .3s;text-decoration:none;display:block;color:#fff}
a.card:hover{background:rgba(255,255,255,.13);transform:translateY(-3px);
border-color:rgba(99,179,237,.5)}
.ci{font-size:48px;margin-bottom:14px}
a.card h2{font-size:22px;margin-bottom:8px}
a.card p{color:#a0aec0;font-size:14px;line-height:1.5}
.badge{display:inline-block;background:#e53e3e;color:#fff;font-size:11px;
padding:2px 10px;border-radius:20px;margin-top:10px;font-weight:600}
.badge.g{background:#38a169}
</style>
</head>
<body>
<div class="c">
  <div class="logo">&#128421;</div>
  <h1>Remote Desktop</h1>
  <p class="sub">Simple remote access to your friend's PC</p>
  <a href="/host" class="card">
    <div class="ci">&#128225;</div>
    <h2>Share my screen</h2>
    <p>Start the server and get a link to send to the person who wants to connect</p>
    <span class="badge">Run on friend's PC</span>
  </a>
  <a href="/view" class="card">
    <div class="ci">&#128065;</div>
    <h2>Connect to a friend's PC</h2>
    <p>Enter the link your friend sent you and control their computer</p>
    <span class="badge g">Run on your PC</span>
  </a>
</div>
</body>
</html>"""

HOST_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Host — Remote Desktop</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);min-height:100vh;
display:flex;align-items:center;justify-content:center;
font-family:'Segoe UI',sans-serif;color:#fff}
.c{text-align:center;padding:40px;max-width:620px;width:90%}
.logo{font-size:64px;margin-bottom:16px}
h1{font-size:28px;margin-bottom:10px}
.sub{color:#a0aec0;margin-bottom:40px;font-size:15px}
.card{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);
border-radius:20px;padding:36px;margin-bottom:20px}
.dot{width:14px;height:14px;border-radius:50%;background:#68d391;
display:inline-block;margin-right:8px;animation:p 2s infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.4}}
.sr{display:flex;align-items:center;justify-content:center;font-size:16px;
color:#68d391;margin-bottom:30px;font-weight:600}
.vc{font-size:14px;color:#a0aec0;margin-bottom:20px}
.vc span{color:#68d391;font-weight:bold}
.lb{background:rgba(0,0,0,.3);border:2px solid rgba(99,179,237,.4);border-radius:12px;
padding:16px 20px;font-size:15px;color:#90cdf4;word-break:break-all;margin-bottom:16px;
font-family:monospace}
.btn{display:inline-block;padding:12px 28px;border-radius:12px;font-size:15px;
font-weight:600;cursor:pointer;border:none;transition:all .2s;margin:6px}
.bb{background:#3182ce;color:#fff}.bb:hover{background:#2b6cb0}
.bg{background:rgba(255,255,255,.1);color:#fff}.bg:hover{background:rgba(255,255,255,.2)}
.info{color:#a0aec0;font-size:13px;margin-top:20px;line-height:1.6}
#cm{display:none;color:#68d391;font-size:13px;margin-top:8px}
.step{background:rgba(255,255,255,.04);border-radius:12px;padding:14px 18px;
margin-top:10px;text-align:left;font-size:14px;color:#e2e8f0;line-height:1.7}
.step strong{color:#90cdf4}
</style>
</head>
<body>
<div class="c">
  <div class="logo">&#128225;</div>
  <h1>Your PC is now accessible</h1>
  <p class="sub">Send the link below to connect</p>
  <div class="card">
    <div class="sr"><span class="dot"></span>Server is running</div>
    <div class="vc">Viewers connected: <span id="vc">0</span></div>
    <div class="lb" id="sl">Loading link...</div>
    <button class="btn bb" onclick="copyLink()">Copy link</button>
    <button class="btn bg" onclick="window.open('/view','_blank')">Open viewer</button>
    <div id="cm">Copied!</div>
    <div class="step">
      <strong>How to use:</strong><br>
      1. Copy the link above<br>
      2. Send it to your friend via any messenger<br>
      3. Your friend opens the link in a browser<br>
      4. They can now see and control your screen
    </div>
    <p class="info">Close this window to stop remote access</p>
  </div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
const socket=io();
let link='';
socket.on('connect',()=>socket.emit('start_stream'));
function updateLink(){
  fetch('/api/public_url').then(r=>r.json()).then(d=>{
    link=d.url||window.location.origin+'/view';
    document.getElementById('sl').textContent=link;
  }).catch(()=>{
    link=window.location.origin+'/view';
    document.getElementById('sl').textContent=link;
  });
}
function copyLink(){
  if(!link)return;
  navigator.clipboard.writeText(link).then(()=>{
    const m=document.getElementById('cm');
    m.style.display='block';
    setTimeout(()=>m.style.display='none',2500);
  });
}
setInterval(()=>{
  fetch('/api/viewers').then(r=>r.json()).then(d=>{
    document.getElementById('vc').textContent=d.count||0;
  }).catch(()=>{});
},2000);
updateLink();
setInterval(updateLink,5000);
</script>
</body>
</html>"""

VIEWER_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Viewer — Remote Desktop</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d0d0d;font-family:'Segoe UI',sans-serif;color:#fff;
height:100vh;overflow:hidden;display:flex;flex-direction:column}
.tb{background:#1a1a2e;padding:8px 16px;display:flex;align-items:center;
gap:12px;border-bottom:1px solid rgba(255,255,255,.1);flex-shrink:0;z-index:100}
.tt{font-size:14px;font-weight:600;color:#90cdf4}
.sd{width:10px;height:10px;border-radius:50%;background:#fc8181;transition:background .3s}
.sd.on{background:#68d391;animation:p 2s infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.5}}
.st{font-size:12px;color:#a0aec0}
.sp{flex:1}
.tbtn{background:rgba(255,255,255,.1);border:none;color:#fff;padding:5px 12px;
border-radius:6px;cursor:pointer;font-size:12px;transition:background .2s}
.tbtn:hover{background:rgba(255,255,255,.2)}
.tbtn.act{background:#3182ce}
.fps{font-size:11px;color:#718096}
.sa{flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative}
#screen{max-width:100%;max-height:100%;object-fit:contain;cursor:none;display:block;
user-select:none;-webkit-user-select:none}
.cur{position:absolute;width:20px;height:20px;pointer-events:none;z-index:999;
transform:translate(-2px,-2px)}
.cur::before{content:'';position:absolute;width:0;height:0;
border-left:7px solid #fff;border-top:0;border-bottom:12px solid transparent;
border-right:8px solid transparent;filter:drop-shadow(1px 1px 1px rgba(0,0,0,.8))}
.ov{position:absolute;inset:0;background:rgba(0,0,0,.85);display:flex;
flex-direction:column;align-items:center;justify-content:center;z-index:10}
.ov.h{display:none}
.oi{font-size:64px;margin-bottom:20px}
.ov h2{font-size:22px;margin-bottom:10px}
.ov p{color:#a0aec0;font-size:14px;text-align:center;max-width:400px}
.cbtn{margin-top:24px;background:#3182ce;color:#fff;border:none;
padding:14px 32px;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer}
.cbtn:hover{background:#2b6cb0}
.kp{display:none;position:fixed;bottom:60px;right:20px;background:#1a1a2e;
border:1px solid rgba(255,255,255,.15);border-radius:16px;padding:16px;z-index:200;min-width:280px}
.kp.v{display:block}
.kp h3{font-size:13px;color:#90cdf4;margin-bottom:12px}
.ki{width:100%;background:rgba(0,0,0,.4);border:1px solid rgba(255,255,255,.2);
border-radius:8px;color:#fff;padding:10px 12px;font-size:15px;outline:none;margin-bottom:10px}
.ki:focus{border-color:#3182ce}
.sb{width:100%;background:#3182ce;color:#fff;border:none;padding:10px;
border-radius:8px;font-size:14px;cursor:pointer;font-weight:600}
.sb:hover{background:#2b6cb0}
</style>
</head>
<body>
<div class="tb">
  <span class="sd" id="sd"></span>
  <span class="tt">&#128421; Remote Desktop</span>
  <span class="st" id="st">Connecting...</span>
  <span class="sp"></span>
  <span class="fps" id="fps">0 FPS</span>
  <button class="tbtn act" id="ct" onclick="toggleCtrl()">&#128433; Control: ON</button>
  <button class="tbtn" onclick="toggleKb()">&#9000; Keyboard</button>
  <button class="tbtn" onclick="toggleFS()">&#9643; Fullscreen</button>
</div>
<div class="sa" id="sa">
  <img id="screen" src="" alt="" draggable="false">
  <div class="cur" id="cur"></div>
  <div class="ov" id="ov">
    <div class="oi">&#128421;</div>
    <h2>Ready to connect</h2>
    <p>Click the button to connect and see your friend's screen</p>
    <button class="cbtn" onclick="startView()">&#9654; Connect</button>
  </div>
</div>
<div class="kp" id="kp">
  <h3>&#9000; Send text</h3>
  <input type="text" class="ki" id="ki" placeholder="Type text and press Enter..."
    onkeydown="if(event.key==='Enter'){sendTxt();event.preventDefault()}">
  <button class="sb" onclick="sendTxt()">Send</button>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
const socket=io();
const scr=document.getElementById('screen');
const cur=document.getElementById('cur');
const sa=document.getElementById('sa');
const ov=document.getElementById('ov');
let ctrl=true,fc=0,lastFps=Date.now(),rw=1920,rh=1080,ft=0;
socket.on('connect',()=>{
  document.getElementById('sd').classList.add('on');
  document.getElementById('st').textContent='Connected';
});
socket.on('disconnect',()=>{
  document.getElementById('sd').classList.remove('on');
  document.getElementById('st').textContent='Disconnected...';
});
socket.on('frame',(d)=>{
  const now=Date.now();
  scr.src='data:image/jpeg;base64,'+d.image;
  fc++;
  if(now-lastFps>=1000){
    document.getElementById('fps').textContent=Math.round(fc/(now-lastFps)*1000)+' FPS';
    fc=0;lastFps=now;
  }
});
scr.onload=function(){rw=scr.naturalWidth;rh=scr.naturalHeight};
function startView(){ov.classList.add('h');socket.emit('start_stream')}
function sf(){
  const r=scr.getBoundingClientRect();
  return{sx:rw/r.width,sy:rh/r.height,rect:r};
}
function rp(e){
  const{sx,sy,rect}=sf();
  return{x:e.clientX-rect.left,y:e.clientY-rect.top,sx,sy,rect};
}
sa.addEventListener('mousemove',(e)=>{
  const{x,y,sx,sy,rect}=rp(e);
  cur.style.left=(rect.left+x)+'px';cur.style.top=(rect.top+y)+'px';
  if(!ctrl||x<0||y<0||x>rect.width||y>rect.height)return;
  socket.emit('mouse_move',{x:Math.round(x),y:Math.round(y),scale_x:sx,scale_y:sy});
});
sa.addEventListener('click',(e)=>{
  if(!ctrl)return;
  const{x,y,sx,sy,rect}=rp(e);
  if(x<0||y<0||x>rect.width||y>rect.height)return;
  socket.emit('mouse_click',{x:Math.round(x),y:Math.round(y),button:'left',scale_x:sx,scale_y:sy});
});
sa.addEventListener('dblclick',(e)=>{
  if(!ctrl)return;
  const{x,y,sx,sy}=rp(e);
  socket.emit('mouse_dblclick',{x:Math.round(x),y:Math.round(y),scale_x:sx,scale_y:sy});
});
sa.addEventListener('contextmenu',(e)=>{
  e.preventDefault();if(!ctrl)return;
  const{x,y,sx,sy,rect}=rp(e);
  if(x<0||y<0||x>rect.width||y>rect.height)return;
  socket.emit('mouse_click',{x:Math.round(x),y:Math.round(y),button:'right',scale_x:sx,scale_y:sy});
});
sa.addEventListener('wheel',(e)=>{
  e.preventDefault();if(!ctrl)return;
  socket.emit('mouse_scroll',{delta:e.deltaY});
},{passive:false});
document.addEventListener('keydown',(e)=>{
  if(!ctrl||document.getElementById('ki')===document.activeElement)return;
  e.preventDefault();
  const mods=[];
  if(e.ctrlKey)mods.push('ctrl');if(e.altKey)mods.push('alt');if(e.shiftKey)mods.push('shift');
  socket.emit('key_press',{key:e.key,modifiers:mods});
});
function toggleCtrl(){
  ctrl=!ctrl;
  const b=document.getElementById('ct');
  b.textContent=ctrl?'\u{1F5B1} Control: ON':'\u{1F5B1} Control: OFF';
  b.classList.toggle('act',!ctrl);
  scr.style.cursor=ctrl?'none':'default';
  cur.style.display=ctrl?'block':'none';
}
function toggleKb(){
  const p=document.getElementById('kp');p.classList.toggle('v');
  if(p.classList.contains('v'))document.getElementById('ki').focus();
}
function sendTxt(){
  const i=document.getElementById('ki');
  if(i.value){socket.emit('type_text',{text:i.value});i.value=''}
}
function toggleFS(){
  if(!document.fullscreenElement)document.documentElement.requestFullscreen();
  else document.exitFullscreen();
}
</script>
</body>
</html>"""

# ── Flask app ──────────────────────────────────────────────────────────────
from flask import Flask, render_template_string, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rdsk2024secret'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

streaming = False
stream_thread = None
connected_viewers = 0
public_url = ''

def capture_screen():
    mss_mod = get_mss()
    Image = get_image()
    with mss_mod.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        img = Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')
        mw = 1280
        if img.width > mw:
            ratio = mw / img.width
            img = img.resize((mw, int(img.height * ratio)), Image.LANCZOS)
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
                socketio.emit('frame', {'image': frame})
            except Exception:
                pass
        time.sleep(0.05)

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/host')
def host():
    return render_template_string(HOST_HTML)

@app.route('/view')
def view():
    return render_template_string(VIEWER_HTML)

@app.route('/api/viewers')
def api_viewers():
    return jsonify({'count': connected_viewers})

@app.route('/api/public_url')
def api_public_url():
    return jsonify({'url': public_url})

@socketio.on('connect')
def on_connect():
    global connected_viewers
    connected_viewers += 1

@socketio.on('disconnect')
def on_disconnect():
    global connected_viewers
    connected_viewers = max(0, connected_viewers - 1)

@socketio.on('start_stream')
def on_start_stream():
    global streaming, stream_thread
    streaming = True
    if stream_thread is None or not stream_thread.is_alive():
        stream_thread = threading.Thread(target=stream_loop, daemon=True)
        stream_thread.start()

@socketio.on('stop_stream')
def on_stop_stream():
    global streaming
    streaming = False

@socketio.on('mouse_move')
def on_mouse_move(data):
    try:
        pg = get_pg()
        sw, sh = pg.size()
        rx = max(0, min(int(data['x'] * data.get('scale_x', 1)), sw - 1))
        ry = max(0, min(int(data['y'] * data.get('scale_y', 1)), sh - 1))
        pg.moveTo(rx, ry)
    except Exception:
        pass

@socketio.on('mouse_click')
def on_mouse_click(data):
    try:
        pg = get_pg()
        sw, sh = pg.size()
        rx = max(0, min(int(data['x'] * data.get('scale_x', 1)), sw - 1))
        ry = max(0, min(int(data['y'] * data.get('scale_y', 1)), sh - 1))
        pg.click(rx, ry, button=data.get('button', 'left'))
    except Exception:
        pass

@socketio.on('mouse_dblclick')
def on_mouse_dblclick(data):
    try:
        pg = get_pg()
        pg.doubleClick(
            int(data['x'] * data.get('scale_x', 1)),
            int(data['y'] * data.get('scale_y', 1))
        )
    except Exception:
        pass

@socketio.on('mouse_scroll')
def on_mouse_scroll(data):
    try:
        get_pg().scroll(-int(data.get('delta', 0) / 100))
    except Exception:
        pass

@socketio.on('key_press')
def on_key_press(data):
    try:
        pg = get_pg()
        key = data.get('key', '')
        mods = data.get('modifiers', [])
        km = {
            'Enter': 'enter', 'Backspace': 'backspace', 'Delete': 'delete',
            'Escape': 'escape', 'Tab': 'tab', 'ArrowLeft': 'left',
            'ArrowRight': 'right', 'ArrowUp': 'up', 'ArrowDown': 'down',
            'Home': 'home', 'End': 'end', 'PageUp': 'pageup', 'PageDown': 'pagedown',
            'F1':'f1','F2':'f2','F3':'f3','F4':'f4','F5':'f5','F6':'f6',
            'F7':'f7','F8':'f8','F9':'f9','F10':'f10','F11':'f11','F12':'f12',
            'Control': None, 'Shift': None, 'Alt': None, 'Meta': None,
            ' ': 'space',
        }
        mk = km.get(key, key.lower() if len(key) == 1 else None)
        if mk is None:
            return
        keys = []
        if 'ctrl' in mods: keys.append('ctrl')
        if 'alt' in mods: keys.append('alt')
        if 'shift' in mods: keys.append('shift')
        keys.append(mk)
        if len(keys) > 1:
            pg.hotkey(*keys)
        else:
            pg.press(mk)
    except Exception:
        pass

@socketio.on('type_text')
def on_type_text(data):
    try:
        get_pg().typewrite(data.get('text', ''), interval=0.02)
    except Exception:
        pass

# ── Tkinter GUI window ─────────────────────────────────────────────────────
def show_gui_window(url_getter):
    try:
        import tkinter as tk
        from tkinter import messagebox
        import webbrowser

        root = tk.Tk()
        root.title('Remote Desktop — Host')
        root.geometry('520x380')
        root.configure(bg='#1a1a2e')
        root.resizable(False, False)

        try:
            root.iconbitmap(default='')
        except Exception:
            pass

        def style_label(parent, text, size=12, color='#e2e8f0', bold=False):
            font = ('Segoe UI', size, 'bold' if bold else 'normal')
            return tk.Label(parent, text=text, font=font, bg='#1a1a2e', fg=color)

        style_label(root, 'Remote Desktop', 18, '#90cdf4', bold=True).pack(pady=(24, 4))
        style_label(root, 'Your PC is being shared', 12, '#a0aec0').pack(pady=(0, 20))

        status_lbl = style_label(root, 'Starting server...', 11, '#68d391')
        status_lbl.pack(pady=(0, 10))

        frame = tk.Frame(root, bg='#0f3460', bd=0, relief='flat')
        frame.pack(padx=30, fill='x', pady=4)

        url_var = tk.StringVar(value='Please wait...')
        url_entry = tk.Entry(frame, textvariable=url_var, font=('Consolas', 10),
                             bg='#0f3460', fg='#90cdf4', relief='flat',
                             bd=8, readonlybackground='#0f3460', state='readonly',
                             justify='center')
        url_entry.pack(fill='x')

        def copy_url():
            root.clipboard_clear()
            root.clipboard_append(url_var.get())
            copy_btn.config(text='Copied!')
            root.after(2000, lambda: copy_btn.config(text='Copy link'))

        def open_viewer():
            webbrowser.open('http://localhost:5000/view')

        btn_frame = tk.Frame(root, bg='#1a1a2e')
        btn_frame.pack(pady=12)

        copy_btn = tk.Button(btn_frame, text='Copy link',
                             command=copy_url, font=('Segoe UI', 11, 'bold'),
                             bg='#3182ce', fg='white', relief='flat',
                             padx=18, pady=8, cursor='hand2',
                             activebackground='#2b6cb0', activeforeground='white')
        copy_btn.pack(side='left', padx=6)

        open_btn = tk.Button(btn_frame, text='Open viewer',
                             command=open_viewer, font=('Segoe UI', 11),
                             bg='#2d3748', fg='white', relief='flat',
                             padx=18, pady=8, cursor='hand2',
                             activebackground='#4a5568', activeforeground='white')
        open_btn.pack(side='left', padx=6)

        info = tk.Label(root,
            text='Send the link above to the person who wants to connect.\nDo NOT close this window — it will stop the connection.',
            font=('Segoe UI', 10), bg='#1a1a2e', fg='#718096', justify='center')
        info.pack(pady=14)

        def poll_url():
            url = url_getter()
            if url and url != url_var.get():
                url_var.set(url)
                status_lbl.config(text='Server running — share the link below')
            root.after(2000, poll_url)

        root.after(2000, poll_url)
        root.mainloop()
    except Exception as e:
        print(f'GUI error: {e}')

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    global public_url

    PORT = 5000

    def start_ngrok():
        global public_url
        try:
            from pyngrok import ngrok
            time.sleep(1.5)
            tunnel = ngrok.connect(PORT, 'http')
            public_url = tunnel.public_url + '/view'
            print(f'\n  Link: {public_url}\n')
        except Exception as e:
            public_url = f'http://localhost:{PORT}/view'
            print(f'  ngrok error: {e}')
            print(f'  Local link: {public_url}')

    def flask_thread():
        socketio.run(app, host='0.0.0.0', port=PORT, debug=False,
                     allow_unsafe_werkzeug=True, log_output=False)

    print('Starting server...')
    t_flask = threading.Thread(target=flask_thread, daemon=True)
    t_flask.start()

    t_ngrok = threading.Thread(target=start_ngrok, daemon=True)
    t_ngrok.start()

    import webbrowser
    threading.Thread(
        target=lambda: (time.sleep(2), webbrowser.open(f'http://localhost:{PORT}/host')),
        daemon=True
    ).start()

    show_gui_window(lambda: public_url)

if __name__ == '__main__':
    main()
