"""
Main entry point for the Conveyor Control application.
This version uses the standard threading server provided by Flask-SocketIO
and includes the necessary flag to run it as a service.
"""
from app import create_app
from app.extensions import socketio

if __name__ == '__main__':
    print("--- Starting Conveyor Control Application ---")
    
    app = create_app()
    
    try:
        # Run the app using the SocketIO server in its default threading mode.
        # allow_unsafe_werkzeug=True is required to run the development server
        # in a production-like environment such as a systemd service.
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
        
    except KeyboardInterrupt:
        print("\n--- Application shutting down (Ctrl+C received) ---")
    except Exception as e:
        print(f"\n--- An unexpected error occurred: {e} ---")