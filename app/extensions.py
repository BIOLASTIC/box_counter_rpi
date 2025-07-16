"""
This file is used to instantiate shared Flask extensions to avoid circular imports.
"""
from flask_socketio import SocketIO
from flask_cors import CORS

# Instantiate all extensions here
socketio = SocketIO(async_mode='threading')
cors = CORS()