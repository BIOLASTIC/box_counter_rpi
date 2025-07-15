"""
Application Factory for the Conveyor Control System.
"""

import threading
import atexit
from flask import Flask
from .database import init_db # <-- Import the init_db function
from .hardware import system_startup, cleanup_gpio
from .ble import start_ble_connection_manager_thread # <-- IMPORT THE NEW FUNCTION

def create_app():
    """
    Creates and configures an instance of the Flask application.
    By default, Flask looks for 'templates' and 'static' folders in the same
    directory as the module where it is instantiated. In our case, this is
    the 'app' directory, which is correct.
    """
    print("[App Factory] Creating Flask application instance...")
    
    # We instantiate the app here. Because this __init__.py file is inside
    # the 'app' directory, Flask will automatically look for:
    # - /app/templates
    # - /app/static
    app = Flask(__name__)

    # --- DIAGNOSTIC PRINT STATEMENT ---
    # Let's see what Flask has automatically determined the path to be.
    print(f"--- [DIAGNOSTIC] Flask auto-detected template folder: {app.template_folder} ---")
    print(f"--- [DIAGNOSTIC] Absolute path to template folder: {app.jinja_loader.searchpath[0]} ---")

    with app.app_context():
        init_db()
    print("[App Factory] Database initialization complete.")


    # --- Import and Register Blueprints ---
    from .routes import main_bp
    app.register_blueprint(main_bp)
    print("[App Factory] Main blueprint registered successfully.")

    # --- Start Background Hardware Thread ---
    from .hardware import system_startup, cleanup_gpio
    
    print("[App Factory] Starting hardware control thread...")
    hardware_thread = threading.Thread(target=system_startup, daemon=True)
    hardware_thread.start()
    print("[App Factory] Hardware control thread started.")

    # --- START THE NEW BLE THREAD ---
    print("[App Factory] Starting BLE connection manager thread...")
    start_ble_connection_manager_thread()

    # --- Register GPIO Cleanup ---
    atexit.register(cleanup_gpio)
    print("[App Factory] GPIO cleanup function registered for exit.")
    
    print("[App Factory] Application creation complete.")
    return app