"""
This is the final, corrected version of ble.py.
It fixes the "different loop" asyncio error by implementing a thread-safe
coroutine runner (run_on_ble_loop) that schedules tasks on the correct event loop
where the BleakClient was created.
"""
import asyncio
import time
import threading
from bleak import BleakClient, BleakError, BleakScanner
from . import database
from . import hardware

def connection_manager_loop():
    """
    The entry point for the background thread. It creates and manages the
    dedicated asyncio event loop for all BLE operations.
    """
    print("[BLE Manager] Starting background connection manager thread...")
    
    # Create the one and only event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Store the loop in the shared hardware state so other threads can find it
    with hardware.state['lock']:
        hardware.state['ble_loop'] = loop
        
    try:
        # Create the main connection logic as a task and run the loop forever
        loop.create_task(connection_logic(loop))
        loop.run_forever()
    finally:
        print("[BLE Manager] Loop is closing.")
        loop.close()

async def connection_logic(loop):
    """
    The main async logic for the connection manager. This will run forever
    on the dedicated BLE event loop.
    """
    while True:
        try:
            device_address = database.get_setting('printer_address')
            with hardware.state['lock']:
                client = hardware.state.get('ble_printer_client')
            is_connected = client and client.is_connected

            if not device_address:
                if is_connected:
                    print("[BLE Manager] Default device removed. Disconnecting...")
                    await client.disconnect()
                await asyncio.sleep(15)
                continue

            if not is_connected:
                print(f"[BLE Manager] Found device {device_address}, attempting connection...")
                with hardware.state['lock']:
                    hardware.state['ble_connection_status'] = "Connecting..."
                hardware.broadcast_status()
                
                await connect_and_manage_device(device_address, loop)
                
                print("[BLE Manager] Disconnected. Waiting 15 seconds before retry.")
                await asyncio.sleep(15)
            else:
                await asyncio.sleep(15)

        except Exception as e:
            print(f"[ERROR in connection_logic]: {e}")
            await asyncio.sleep(30)

async def connect_and_manage_device(address, loop):
    """Handles a single connection session for a device."""
    disconnected_event = asyncio.Event()

    def handle_disconnect(client: BleakClient):
        print(f"[BLE Disconnect] Device {client.address} disconnected.")
        with hardware.state['lock']:
            hardware.state['ble_printer_client'] = None
            hardware.state['ble_connection_status'] = "Disconnected"
        hardware.broadcast_status()
        if not disconnected_event.is_set():
            disconnected_event.set()

    client = BleakClient(address, loop=loop, disconnected_callback=handle_disconnect)

    try:
        await client.connect(timeout=10.0)
        if client.is_connected:
            print(f"[BLE Connect] Success: {address}.")
            with hardware.state['lock']:
                hardware.state['ble_printer_client'] = client
                hardware.state['ble_connection_status'] = "Connected"
            hardware.broadcast_status()
            await disconnected_event.wait()
            
    except Exception as e:
        print(f"[BLE Connect] Failed: {address}. Error: {e}")
    finally:
        print(f"[BLE Connect] Session ended for {address}.")
        with hardware.state['lock']:
            hardware.state['ble_printer_client'] = None
            hardware.state['ble_connection_status'] = "Disconnected"
        hardware.broadcast_status()

def run_on_ble_loop(coro):
    """
    Schedules a coroutine to be executed on the dedicated BLE event loop
    from a synchronous thread and waits for its result. This is the key fix.
    """
    with hardware.state['lock']:
        loop = hardware.state.get('ble_loop')
    
    if not loop or not loop.is_running():
        print("[run_on_ble_loop] Error: BLE event loop is not available.")
        raise RuntimeError("BLE event loop is not running.")

    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=10)

# --- On-Demand Functions (for API routes) ---
def run_async(coro):
    """Helper for one-off async tasks that DON'T need the persistent client."""
    return asyncio.run(coro)

async def scan_ble_devices(timeout=10.0):
    """Scans for BLE devices and returns a list of them."""
    print(f"[BLE Scan] Starting BLE device scan for {timeout} seconds...")
    try:
        devices = await BleakScanner.discover(timeout=timeout)
        return [{"name": dev.name or "Unnamed", "address": dev.address} for dev in devices if dev.name]
    except BleakError as e:
        return {"error": str(e)}

async def get_characteristics(device_address):
    """Connects to a device temporarily to discover its services."""
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