"""
This is the CORRECTED and complete version of ble.py.
The start_ble_connection_manager_thread function has been removed
as the task will now be started directly by SocketIO in __init__.py.
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
    print("[BLE Manager] Starting background connection manager loop...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            device_address = database.get_setting('printer_address')
            with hardware.state['lock']:
                client = hardware.state.get('ble_printer_client')
            is_connected = client and client.is_connected
            if not device_address:
                if is_connected:
                    print("[BLE Manager] Default device removed. Disconnecting...")
                    loop.run_until_complete(client.disconnect())
                    with hardware.state['lock']:
                        hardware.state['ble_printer_client'] = None
                        hardware.state['ble_connection_status'] = "Disconnected"
                time.sleep(15)
                continue
            if not is_connected:
                print(f"[BLE Manager] Found device {device_address}, attempting connection...")
                loop.run_until_complete(connect_and_manage_device(device_address, loop))
                print("[BLE Manager] Waiting 60 seconds before next connection attempt...")
                time.sleep(60)
            else:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR in connection_manager_loop]: {e}")
            time.sleep(30) # Wait longer if there's a loop error

async def connect_and_manage_device(address, loop):
    """The async part of the connection logic with corrected locking."""
    print(f"[BLE Connect] Attempting: {address}")
    with hardware.state['lock']:
        hardware.state['ble_connection_status'] = "Connecting..."
    try:
        new_client = BleakClient(address, loop=loop)
        await new_client.connect(timeout=10.0)
        with hardware.state['lock']:
            if new_client.is_connected:
                print(f"[BLE Connect] Success: {address}.")
                hardware.state['ble_printer_client'] = new_client
                hardware.state['ble_connection_status'] = "Connected"
            else:
                hardware.state['ble_printer_client'] = None
                hardware.state['ble_connection_status'] = "Disconnected"
    except Exception as e:
        print(f"[BLE Connect] Failed: {address}. Error: {e}")
        with hardware.state['lock']:
            hardware.state['ble_printer_client'] = None
            hardware.state['ble_connection_status'] = "Disconnected"

# --- On-Demand Functions (Unchanged) ---
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
        async with BleakClient(device_address, timeout=10.0) as client:
            return [{
                "uuid": char.uuid,
                "description": char.description,
                "properties": ", ".join(char.properties)
            } for service in client.services for char in service.characteristics]
    except Exception as e:
        return {"error": str(e)}

def run_async(coro):
    """Helper to run async functions from sync Flask code."""
    return asyncio.run(coro)