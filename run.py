"""
Main entry point for the Conveyor Control application.

This script imports the application factory 'create_app' from the 'app' package
and starts the Flask development server.

To run the application:
    python3 run.py
"""
from app import create_app

if __name__ == '__main__':
    # This block is executed only when the script is run directly.
    print("--- Starting Conveyor Control Application ---")
    
    # Create the Flask app instance using the factory function.
    app = create_app()
    
    try:
        # Run the Flask application.
        # host='0.0.0.0' makes the server accessible from other devices on the network.
        # debug=False is CRITICAL for hardware projects to prevent the reloader
        # from starting a second instance of the app and GPIO threads.
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        print("\n--- Application shutting down (Ctrl+C received) ---")
    except Exception as e:
        print(f"\n--- An unexpected error occurred: {e} ---")