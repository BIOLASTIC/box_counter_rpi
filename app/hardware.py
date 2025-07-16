"""
This is the CORRECTED and complete version of hardware.py.
It fixes the cleanup_gpio function to be compatible with gpiozero objects.
"""
import time
import threading
import asyncio
from gpiozero import LED, Button, Buzzer
from . import database, ble
from .extensions import socketio

# (PIN_CONFIG and state dictionary are unchanged)
PIN_CONFIG = { 'IR_SENSOR': {'pin': 17, 'type': 'Input (NPN)'}, 'GATE_RELAY': {'pin': 22, 'type': 'Output (Relay)'}, 'GREEN_LED': {'pin': 27, 'type': 'Output (Relay)'}, 'RED_LED': {'pin': 23, 'type': 'Output (Relay)'}, 'BUZZER': {'pin': 24, 'type': 'Output (Relay)'} }
state = { "object_count": 0, "batch_target": 20, "gate_wait_time": 10, "gate_status": "Closed", "ir_status": "Clear", "system_status": "Initializing", "lock": threading.Lock(), "ble_connection_status": "Disconnected", "ble_printer_client": None, "printer_enabled": False, "last_printed_payload": "N/A", "batches_completed": 0, }

# (Deferred Initialization logic is unchanged and correct)
ir_sensor = None
gate_relay = None
green_led = None
red_led = None
buzzer = None

def initialize_hardware():
    global ir_sensor, gate_relay, green_led, red_led, buzzer
    print("[Hardware] Initializing GPIO objects...")
    try:
        ir_sensor = Button(PIN_CONFIG['IR_SENSOR']['pin'], pull_up=True)
        gate_relay = LED(PIN_CONFIG['GATE_RELAY']['pin'])
        green_led = LED(PIN_CONFIG['GREEN_LED']['pin'])
        red_led = LED(PIN_CONFIG['RED_LED']['pin'])
        buzzer = Buzzer(PIN_CONFIG['BUZZER']['pin'])
        ir_sensor.when_pressed = object_detected
        ir_sensor.when_released = object_passed
        print("[Hardware] GPIO objects initialized successfully.")
        return True
    except Exception as e:
        print(f"[FATAL] Could not initialize GPIO devices: {e}")
        with state['lock']:
            state['system_status'] = "GPIO FAILED. REBOOT REQUIRED."
        broadcast_status()
        return False

# (All other hardware functions like broadcast_status, close_gate, object_passed, etc., are unchanged)
def broadcast_status():
    with state['lock']:
        status_data = {k: v for k, v in state.items() if k not in ['lock', 'ble_printer_client']}
    socketio.emit('status_update', status_data)

def close_gate():
    if not gate_relay: return
    with state['lock']:
        if state['gate_status'] != "Closed":
            gate_relay.on(); state['gate_status'] = "Closed"; update_lights(); print("Gate Closed.")
    broadcast_status()

def open_gate():
    if not gate_relay: return
    with state['lock']:
        if state['gate_status'] != "Open":
            gate_relay.off(); state['gate_status'] = "Open"; update_lights(); print("Gate Open.")
    broadcast_status()

def update_lights():
    if not green_led or not red_led: return
    if state['gate_status'] == "Open": green_led.on(); red_led.off()
    else: green_led.off(); red_led.on()

def handle_batch_completion():
    if not buzzer: return
    print("Batch complete.")
    with state['lock']:
        state['system_status'] = "Batch Complete: Closing Gate"
        state['batches_completed'] += 1
    broadcast_status()
    buzzer.beep(on_time=2.0, n=1, background=True)
    time.sleep(0.5); close_gate()
    with state['lock']: wait_time = state['gate_wait_time']; state['system_status'] = f"Waiting for {wait_time}s"
    broadcast_status()
    print(f"Waiting for {wait_time} seconds..."); time.sleep(wait_time)
    print("Resetting for next batch.")
    with state['lock']: state['object_count'] = 0; state['system_status'] = "Ready to Count"
    broadcast_status()
    buzzer.beep(on_time=0.1, off_time=0.2, n=3, background=True); open_gate()

def object_passed():
    if not buzzer: return
    with state['lock']:
        if state['gate_status'] != "Open" or state['system_status'] not in ["Ready to Count", "Counting"]: return
        state['ir_status'] = "Clear"; state['object_count'] += 1; state['system_status'] = "Counting"
        count, target = state['object_count'], state['batch_target']
    print(f"Object Passed. Count: {count}")
    buzzer.beep(on_time=1.0, n=1, background=True)
    broadcast_status()
    if count >= target:
        threading.Thread(target=handle_batch_completion, daemon=True).start()

def object_detected():
    with state['lock']:
        state['ir_status'] = "Blocked"
    broadcast_status()

def system_startup():
    print("[Hardware] Starting system startup sequence...")
    if not initialize_hardware(): return
    with state['lock']:
        state['printer_enabled'] = database.get_setting('printer_enabled', 'false') == 'true'
    close_gate()
    time.sleep(2)
    buzzer.beep(on_time=0.1, off_time=0.2, n=3, background=True)
    open_gate()
    with state['lock']: state['system_status'] = "Ready to Count"
    broadcast_status()
    print("[Hardware] System is ready.")

def get_live_pin_status():
    if not ir_sensor: return {k: 0 for k in PIN_CONFIG.keys()}
    return { 'IR_SENSOR': ir_sensor.value, 'GATE_RELAY': gate_relay.value, 'GREEN_LED': green_led.value, 'RED_LED': red_led.value, 'BUZZER': buzzer.value }

# --- FIX: Corrected cleanup function ---
def cleanup_gpio():
    """Closes all GPIO devices gracefully."""
    print("Cleaning up GPIO...")
    for device in [ir_sensor, gate_relay, green_led, red_led, buzzer]:
        if device:
            device.close()

def send_print_job():
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