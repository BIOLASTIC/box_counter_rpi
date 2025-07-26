"""
This file contains the main application logic. It is only ever imported
and run *after* eventlet has monkey-patched the system.
"""
import threading
import signal
import os
from app import create_app
from app.extensions import socketio
from app.hardware import system_startup, cleanup_resources, start_polling_thread

def shutdown_handler(sig, frame):
    print('--- Signal received, initiating graceful shutdown... ---')
    raise SystemExit("Shutdown initiated by signal.")

def run():
    print("[Main] Creating Flask application...")
    # The factory will now start the necessary background tasks
    app = create_app()

    # Register signal handlers for a clean exit
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    print("--- Starting application with Eventlet Web Server ---")
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except SystemExit as e:
        print(f"Caught SystemExit: {e}")
    finally:
        print("--- Cleaning up hardware resources before final exit. ---")
        cleanup_resources()