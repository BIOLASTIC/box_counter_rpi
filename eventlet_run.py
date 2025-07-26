"""
This is the ONLY file you should run to start the application.
Its sole purpose is to apply the eventlet monkey-patch in a clean
environment BEFORE any other part of the application is imported.
"""
import eventlet

# Apply the patch first. This is the most critical step.
eventlet.monkey_patch()

# NOW that the system is patched, we can safely import and run the main app logic.
import main

if __name__ == '__main__':
    main.run()