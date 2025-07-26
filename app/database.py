"""
This version adds a function to initialize the database with default
settings if they do not already exist, ensuring a stable startup.
"""
import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app_instance.db')

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the settings table if it doesn't exist."""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("[Database] Database initialized successfully.")

def init_db_defaults():
    """
    NEW: Ensures default critical settings exist in the database.
    This prevents the "Stuck on Initializing" bug.
    """
    print("[Database] Checking for default settings...")
    defaults = {
        'batch_target': '20',
        'gate_wait_time': '10'
    }
    conn = get_db_connection()
    for key, value in defaults.items():
        # The 'OR IGNORE' is important: it will only insert if the key does not exist.
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
    print("[Database] Default settings verified.")

def get_setting(key, default=None):
    """Retrieves a setting value from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key, value):
    """Saves or updates a setting value in the database."""
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def remove_setting(key):
    """Removes a setting from the database."""
    conn = get_db_connection()
    conn.execute("DELETE FROM settings WHERE key = ?", (key,))
    conn.commit()
    conn.close()