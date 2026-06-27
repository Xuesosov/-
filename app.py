import os
import time
import threading
import base64
import io

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rdsk2024relay'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# Track connected agent (friend's EXE) and viewers (your browser)
agent_sid = None
viewer_sids = set()
agent_screen_size = {'w': 1920, 'h': 1080}

# ── Routes ─────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/watch')
def watch():
    return render_template('viewer.html')

@app.route('/api/status')
def api_status():
    return jsonify({
        'agent_connected': agent_sid is not None,
        'viewers': len(viewer_sids)
    })

# ── SocketIO: connection management ───────────────────────────────────────
@socketio.on('connect')
def on_connect():
    pass

@socketio.on('disconnect')
def on_disconnect():
    global agent_sid
    sid = request.sid
    if sid == agent_sid:
        agent_sid = None
        socketio.emit('agent_disconnected', {}, to='viewers')
        print('[relay] Agent disconnected')
    elif sid in viewer_sids:
        viewer_sids.discard(sid)

# ── SocketIO: agent events (from friend's EXE) ────────────────────────────
@socketio.on('agent_join')
def on_agent_join(data):
    global agent_sid, agent_screen_size
    agent_sid = request.sid
    join_room('agent_room')
    agent_screen_size = {
        'w': data.get('w', 1920),
        'h': data.get('h', 1080)
    }
    socketio.emit('agent_connected', agent_screen_size, to='viewers')
    print(f'[relay] Agent connected: {agent_screen_size}')

@socketio.on('frame')
def on_frame(data):
    if request.sid == agent_sid:
        socketio.emit('frame', data, to='viewers')

# ── SocketIO: viewer events (from your browser) ───────────────────────────
@socketio.on('viewer_join')
def on_viewer_join():
    viewer_sids.add(request.sid)
    join_room('viewers')
    if agent_sid:
        emit('agent_connected', agent_screen_size)
    else:
        emit('agent_disconnected', {})

@socketio.on('mouse_move')
def on_mouse_move(data):
    if agent_sid and request.sid in viewer_sids:
        socketio.emit('mouse_move', data, to=agent_sid)

@socketio.on('mouse_click')
def on_mouse_click(data):
    if agent_sid and request.sid in viewer_sids:
        socketio.emit('mouse_click', data, to=agent_sid)

@socketio.on('mouse_dblclick')
def on_mouse_dblclick(data):
    if agent_sid and request.sid in viewer_sids:
        socketio.emit('mouse_dblclick', data, to=agent_sid)

@socketio.on('mouse_scroll')
def on_mouse_scroll(data):
    if agent_sid and request.sid in viewer_sids:
        socketio.emit('mouse_scroll', data, to=agent_sid)

@socketio.on('key_press')
def on_key_press(data):
    if agent_sid and request.sid in viewer_sids:
        socketio.emit('key_press', data, to=agent_sid)

@socketio.on('type_text')
def on_type_text(data):
    if agent_sid and request.sid in viewer_sids:
        socketio.emit('type_text', data, to=agent_sid)

if __name__ == '__main__':
    print('=' * 50)
    print('  Remote Desktop Relay Server')
    print('=' * 50)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False,
                 allow_unsafe_werkzeug=True)
