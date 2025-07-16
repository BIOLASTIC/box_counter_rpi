"""
Application Factory for the Conveyor Control System.
This version uses standard threading for all background tasks.
"""
import time
import atexit
from flask import Flask
from .extensions import socketio
from .database import init_db
from .hardware import (system_startup, cleanup_gpio, get_live_pin_status,
                       broadcast_status, state as hardware_state)
from .system import get_system_health_info, get_consolidated_network_info
from .ble import connection_manager_loop

tasks_started = False

def background_broadcaster_thread():
    """Periodically broadcasts system status updates using standard time.sleep."""
    print("[SocketIO] Starting background broadcaster...")
    loop_count = 0
    while True:
        try:
            socketio.emit('health_update', get_system_health_info())
            socketio.emit('pin_update', get_live_pin_status())
            if loop_count % 5 == 0:
                broadcast_top_bar_data()
            loop_count = (loop_count + 1) % 5
            # Use the standard time.sleep, which is compatible with this threading model
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR in background_broadcaster_thread]: {e}")
            time.sleep(5)

def broadcast_top_bar_data():
    """Gathers and broadcasts data for the top status bar."""
    network_info = get_consolidated_network_info()
    with hardware_state['lock']:
        ble_saved = database.get_setting('printer_address') is not None
        ble_connected = hardware_state.get('ble_connection_status') == 'Connected'
    top_bar_data = {
        "internet_active": network_info["has_internet"], "ip_address": network_info["ip_address"],
        "eth_active": network_info["is_ethernet"], "wifi_active": network_info["is_wifi"],
        "wifi_strength": network_info["wifi_strength"], "wifi_ssid": network_info["wifi_ssid"],
        "ble_saved": ble_saved, "ble_connected": ble_connected,
    }
    socketio.emit('top_bar_update', top_bar_data)


def create_app():
    """Creates the Flask app and starts the background tasks with SocketIO."""
    global tasks_started
    print("[App Factory] Creating Flask application instance...")
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-very-secret-key!'
    socketio.init_app(app)
    
    with app.app_context():
        init_db()
    print("[App Factory] Database initialization complete.")

    from .routes import main_bp
    app.register_blueprint(main_bp)
    print("[App Factory] Main blueprint registered successfully.")

    if not tasks_started:
        print("[App Factory] Starting background tasks in threading mode...")
        socketio.start_background_task(target=system_startup)
        socketio.start_background_task(target=connection_manager_loop)
        socketio.start_background_task(target=background_broadcaster_thread)
        tasks_started = True
        print("[App Factory] All background tasks started.")

    atexit.register(cleanup_gpio)
    print("[App Factory] GPIO cleanup function registered for exit.")
    print("[App Factory] Application creation complete.")
    return app

@socketio.on('connect')
def handle_connect():
    print('[SocketIO] Client connected.')
    broadcast_status()
    broadcast_top_bar_data()