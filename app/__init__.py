"""
Application Factory for the Conveyor Control System.
This version is configured to work as a pure API/WebSocket backend.
"""
import time
import atexit
from flask import Flask
from .extensions import socketio, cors # <-- Import cors
from .database import init_db
from .hardware import (system_startup, cleanup_gpio, get_live_pin_status, 
                       broadcast_status, state as hardware_state)
from .system import get_system_health_info, get_consolidated_network_info
from .ble import connection_manager_loop 

tasks_started = False

def background_broadcaster_thread():
    # This function is unchanged
    print("[SocketIO] Starting background broadcaster...")
    # ... (rest of function)
    
def broadcast_top_bar_data():
    # This function is unchanged
    pass

def create_app():
    """Creates the Flask app and starts the background tasks."""
    global tasks_started
    print("[App Factory] Creating Flask API instance...")
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-very-secret-key!'

    # Initialize extensions
    socketio.init_app(app, cors_allowed_origins="*") # Allow all origins for SocketIO
    cors.init_app(app) # Initialize CORS for standard HTTP requests

    with app.app_context():
        init_db()
    print("[App Factory] Database initialization complete.")

    from .routes import main_bp
    app.register_blueprint(main_bp)
    print("[App Factory] Main API blueprint registered successfully.")

    if not tasks_started:
        print("[App Factory] Starting background tasks...")
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