"""
This version uses a thread-safe queue to communicate between the native
hardware threads and the eventlet-based web server thread, preventing deadlocks.
"""
import time
import atexit
import queue
from flask import Flask
import threading

from .extensions import socketio
from .database import init_db, init_db_defaults
from .hardware import system_startup, cleanup_resources, get_live_io_status, state as hardware_state
from .system import get_system_health_info, get_consolidated_network_info

# --- THE FIX: Create a thread-safe queue for status updates ---
status_queue = queue.Queue()

tasks_started = False

def status_broadcaster():
    """This is a GREEN thread. It safely consumes from the queue and emits to clients."""
    print("[Broadcaster] Starting status broadcaster green thread...")
    while True:
        try:
            status_data = status_queue.get()
            socketio.emit('status_update', status_data)
        except Exception as e:
            print(f"[ERROR in status_broadcaster]: {e}")
        socketio.sleep(0.01)

def diagnostics_broadcaster():
    """This is a GREEN thread for less frequent updates."""
    print("[Broadcaster] Starting diagnostics broadcaster green thread...")
    while True:
        try:
            socketio.emit('health_update', get_system_health_info())
            socketio.emit('pin_update', get_live_io_status())
            broadcast_top_bar_data()
        except Exception as e:
            print(f"[ERROR in diagnostics_broadcaster]: {e}")
        socketio.sleep(5)

def broadcast_top_bar_data():
    network_info = get_consolidated_network_info()
    top_bar_data = {
        "internet_active": network_info["has_internet"], "ip_address": network_info["ip_address"],
        "eth_active": network_info["is_ethernet"], "wifi_active": network_info["is_wifi"],
        "wifi_strength": network_info["wifi_strength"], "wifi_ssid": network_info["wifi_ssid"],
    }
    socketio.emit('top_bar_update', top_bar_data)

def create_app():
    global tasks_started
    print("[App Factory] Creating Flask application instance...")
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-very-secret-key!'
    socketio.init_app(app, async_mode='eventlet')
    
    with app.app_context():
        init_db()
        init_db_defaults()

    from .routes import main_bp
    app.register_blueprint(main_bp)
    print("[App Factory] Main blueprint registered successfully.")

    if not tasks_started:
        print("[App Factory] Starting background tasks...")
        # Start the hardware logic in a NATIVE OS thread
        threading.Thread(target=system_startup, daemon=True).start()
        # Start the queue consumers in GREEN threads managed by socketio
        socketio.start_background_task(target=status_broadcaster)
        socketio.start_background_task(target=diagnostics_broadcaster)
        tasks_started = True
        print("[App Factory] All background tasks started.")

    atexit.register(cleanup_resources)
    return app

@socketio.on('connect')
def handle_connect():
    print('[SocketIO] Client connected.')
    with hardware_state['lock']:
        status_queue.put({k: v for k, v in hardware_state.items() if k != 'lock'})