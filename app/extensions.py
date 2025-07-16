"""
This file is used to instantiate shared Flask extensions to avoid circular imports.
"""
from flask_socketio import SocketIO

# CRITICAL FIX: Explicitly set the async_mode to 'threading'.
# This forces Flask-SocketIO to use the standard threading library and
# prevents it from auto-detecting and using the incompatible gevent.
socketio = SocketIO(async_mode='threading')