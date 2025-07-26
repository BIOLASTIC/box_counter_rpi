"""
This is the ONLY file you should run to start the application.
Its sole purpose is to apply the eventlet monkey-patch in a clean
environment BEFORE any other part of the application is imported.
"""
import eventlet
# Apply the patch first. This is the most critical step.
eventlet.monkey_patch()

# NOW that the system is patched, we can safely import and run the main app logic.
from app import create_app
from app.extensions import socketio
import signal
from app.hardware import cleanup_resources

# This function will handle Ctrl+C
def shutdown_handler(sig, frame):
    print('--- Signal received, initiating graceful shutdown... ---')
    cleanup_resources()
    # A simple exit is fine here as eventlet will handle shutting down the server
    exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == '__main__':
    print("[Run] Creating Flask application...")
    app = create_app()
    
    print("--- Starting application with Eventlet Web Server ---")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)