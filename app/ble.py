"""
This is the CORRECTED and complete version of ble.py with proper lock
management to prevent deadlocks during startup and reconnection.
"""
import asyncio
import time
import threading
from bleak import BleakClient, BleakError, BleakScanner
from . import database
from . import hardware

def connection_manager_loop():
    """
    A loop that runs in a background thread to manage the BLE connection.
    """
    print("[BLE Manager] Starting background connection manager thread.")
    
    # An asyncio event loop that will run in this background thread.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        device_address = database.get_setting('printer_address')
        
        # Safely get the client object from the global state
        with hardware.state['lock']:
            client = hardware.state.get('ble_printer_client')
        
        is_connected = client and client.is_connected

        if not device_address:
            # No device saved. If we were connected, disconnect.
            if is_connected:
                print("[BLE Manager] Default device removed. Disconnecting...")
                loop.run_until_complete(client.disconnect())
                with hardware.state['lock']:
                    hardware.state['ble_printer_client'] = None
                    hardware.state['ble_connection_status'] = "Disconnected"
            # Wait a while before checking the database again for a new device
            time.sleep(15)
            continue

        # If we have a device saved but are not connected, try to connect.
        if not is_connected:
            loop.run_until_complete(connect_and_manage_device(device_address, loop))
            
            # After a connection attempt (whether it succeeded or failed),
            # wait for the configured interval before retrying.
            print("[BLE Manager] Waiting 60 seconds before next connection attempt...")
            time.sleep(60)
        else:
            # We are connected, so we'll check again in a little while
            # to make sure the connection is still active.
            time.sleep(15)

async def connect_and_manage_device(address, loop):
    """The async part of the connection logic with corrected locking."""
    print(f"[BLE Manager] Attempting to connect to default printer: {address}")
    
    # Acquire lock ONLY to update the status, then release it immediately.
    with hardware.state['lock']:
        hardware.state['ble_connection_status'] = "Connecting..."

    new_client = None  # Define client outside the try block
    try:
        # Perform the long-running connection attempt OUTSIDE of any lock.
        new_client = BleakClient(address, loop=loop)
        await new_client.connect()

        # Re-acquire the lock only to update the state with the connection result.
        with hardware.state['lock']:
            if new_client.is_connected:
                print(f"[BLE Manager] Successfully connected to {address}.")
                hardware.state['ble_printer_client'] = new_client
                hardware.state['ble_connection_status'] = "Connected"
            else:
                hardware.state['ble_printer_client'] = None
                hardware.state['ble_connection_status'] = "Disconnected"

    except Exception as e:
        print(f"[BLE Manager] Connection to {address} failed. Error: {e}")
        # If the connection fails, re-acquire the lock to update the status.
        with hardware.state['lock']:
            hardware.state['ble_printer_client'] = None
            hardware.state['ble_connection_status'] = "Disconnected"

def start_ble_connection_manager_thread():
    """Helper function called from __init__.py to start the manager thread."""
    thread = threading.Thread(target=connection_manager_loop, daemon=True)
    thread.start()


# --- ON-DEMAND FUNCTIONS (for scanning, etc.) ---

async def scan_ble_devices(timeout=10.0):
    """Scans for BLE devices and returns a list of them."""
    print(f"[BLE Scan] Starting BLE device scan for {timeout} seconds...")
    try:
        devices = await BleakScanner.discover(timeout=timeout)
        return [{"name": dev.name or "Unnamed", "address": dev.address} for dev in devices]
    except BleakError as e:
        return {"error": str(e)}

async def get_characteristics(device_address):
    """Connects to a device temporarily just to discover its services."""
    print(f"[BLE Get-Chars] Connecting temporarily to {device_address}...")
    try:
        async with BleakClient(device_address) as client:
            return [{
                "uuid": char.uuid,
                "description": char.description,
                "properties": ", ".join(char.properties)
            } for service in client.services for char in service.characteristics]
    except Exception as e:
        return {"error": str(e)}

def run_async(coro):
    """Helper to run async functions from sync Flask code."""
    # This creates a new event loop for each on-demand task, ensuring thread safety.
    return asyncio.run(coro)