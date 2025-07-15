"""
This is the CORRECTED and complete version of hardware.py.
It adds tracking for 'last_printed_payload' and 'batches_completed'
to the global state for the new dashboard UI.
"""
import asyncio
import time
import threading
from gpiozero import LED, Button, Buzzer
from . import database, ble

PIN_CONFIG = {
    'IR_SENSOR': {'pin': 17, 'type': 'Input (NPN)'},
    'GATE_RELAY': {'pin': 22, 'type': 'Output (Relay)'},
    'GREEN_LED': {'pin': 27, 'type': 'Output (Relay)'},
    'RED_LED': {'pin': 23, 'type': 'Output (Relay)'},
    'BUZZER': {'pin': 24, 'type': 'Output (Relay)'}
}

# --- Global State Dictionary (with new keys) ---
state = {
    "object_count": 0, "batch_target": 20, "gate_wait_time": 10,
    "gate_status": "Closed", "ir_status": "Clear", "system_status": "Initializing",
    "lock": threading.Lock(), "ble_connection_status": "Disconnected",
    "ble_printer_client": None, "printer_enabled": False,
    # --- NEW STATE VARIABLES ---
    "last_printed_payload": "N/A",
    "batches_completed": 0,
}

# Hardware Device Initializations
ir_sensor = Button(PIN_CONFIG['IR_SENSOR']['pin'], pull_up=True)
gate_relay = LED(PIN_CONFIG['GATE_RELAY']['pin'])
green_led = LED(PIN_CONFIG['GREEN_LED']['pin'])
red_led = LED(PIN_CONFIG['RED_LED']['pin'])
buzzer = Buzzer(PIN_CONFIG['BUZZER']['pin'])


# Core Gate and Light Control Functions
def close_gate():
    with state['lock']:
        if state['gate_status'] != "Closed":
            gate_relay.on(); state['gate_status'] = "Closed"; update_lights(); print("Gate Closed.")

def open_gate():
    with state['lock']:
        if state['gate_status'] != "Open":
            gate_relay.off(); state['gate_status'] = "Open"; update_lights(); print("Gate Open.")

def update_lights():
    if state['gate_status'] == "Open": green_led.on(); red_led.off()
    else: green_led.off(); red_led.on()


# Print Job Logic (MODIFIED)
def send_print_job():
    """Fetches print settings and sends data to the BLE printer."""
    print("[Print Job] Started.")
    try:
        delay_ms = int(database.get_setting('printer_delay_ms', '0'))
        var1, val1 = database.get_setting('printer_var1', ''), database.get_setting('printer_var1_val', '')
        var2, val2 = database.get_setting('printer_var2', ''), database.get_setting('printer_var2_val', '')
        char_uuid = database.get_setting('write_characteristic_uuid')

        if not char_uuid:
            print("[Print Job] Error: No printer characteristic UUID is saved."); return

        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

        payload = f"{var1}{val1}{var2}{val2}"
        print(f"[Print Job] Constructed payload: '{payload}'")

        # --- NEW: Update the global state with the payload ---
        with state['lock']:
            state['last_printed_payload'] = payload
            client = state.get('ble_printer_client')
        
        if client and client.is_connected:
            print("[Print Job] Sending data to printer...")
            asyncio.run(client.write_gatt_char(char_uuid, payload.encode('utf-8')))
            print("[Print Job] Data sent successfully.")
        else:
            print("[Print Job] Error: Printer is not connected. Aborting print job.")

    except Exception as e:
        print(f"[Print Job] An exception occurred: {e}")


# Batch Completion Logic (MODIFIED)
def handle_batch_completion():
    """Manages the process after a batch is fully counted."""
    print("Batch complete.")
    with state['lock']:
        state['system_status'] = "Batch Complete: Closing Gate"
        # --- NEW: Increment the completed batches counter ---
        state['batches_completed'] += 1
    
    buzzer.beep(on_time=2.0, n=1, background=True)
    time.sleep(0.5); close_gate()
    with state['lock']: wait_time = state['gate_wait_time']; state['system_status'] = f"Waiting for {wait_time}s"
    print(f"Waiting for {wait_time} seconds..."); time.sleep(wait_time)
    print("Resetting for next batch.")
    with state['lock']: state['object_count'] = 0; state['system_status'] = "Ready to Count"
    buzzer.beep(on_time=0.1, off_time=0.2, n=3, background=True); open_gate()


# Object Detection Logic
def object_passed():
    """Called when the object has finished passing the sensor."""
    with state['lock']:
        if state['gate_status'] != "Open" or state['system_status'] not in ["Ready to Count", "Counting"]:
            return
        
        state['ir_status'] = "Clear"; state['object_count'] += 1; state['system_status'] = "Counting"
        count, target = state['object_count'], state['batch_target']
        is_printing_enabled = state.get('printer_enabled', False)
        is_printer_connected = state.get('ble_connection_status') == 'Connected'

    print(f"Object Passed. Count: {count}")
    buzzer.beep(on_time=1.0, n=1, background=True)

    if is_printing_enabled and is_printer_connected:
        print_thread = threading.Thread(target=send_print_job, daemon=True)
        print_thread.start()
    elif is_printing_enabled and not is_printer_connected:
        print("[Hardware] Print job skipped: Automatic Printing is ON, but the printer is disconnected.")
    
    if count >= target:
        threading.Thread(target=handle_batch_completion, daemon=True).start()

def object_detected():
    with state['lock']:
        state['ir_status'] = "Blocked"


# System Startup and Cleanup
def system_startup():
    print("[Hardware] Starting system startup sequence...")
    with state['lock']:
        state['printer_enabled'] = database.get_setting('printer_enabled', 'false') == 'true'
    
    ir_sensor.when_pressed = object_detected
    ir_sensor.when_released = object_passed
    
    close_gate()
    time.sleep(2)

    buzzer.beep(on_time=0.1, off_time=0.2, n=3, background=True)
    open_gate()
    with state['lock']:
        state['system_status'] = "Ready to Count"
    print("[Hardware] System is ready.")

def cleanup_gpio():
    print("Cleaning up GPIO...")
    ir_sensor.close(); gate_relay.close(); green_led.close(); red_led.close(); buzzer.close()