"""
This is the final, combined version of hardware.py. It uses the new thread-safe
BLE loop runner to ensure stability for automatic printing.
"""
import time
import threading
import asyncio
from gpiozero import LED, Button, Buzzer
from . import database, ble
from .extensions import socketio

PIN_CONFIG = { 
    'IR_SENSOR': {'pin': 17, 'type': 'Input (NPN)'}, 
    'GATE_RELAY': {'pin': 22, 'type': 'Output (Relay)'}, 
    'GREEN_LED': {'pin': 27, 'type': 'Output (Relay)'}, 
    'RED_LED': {'pin': 23, 'type': 'Output (Relay)'}, 
    'BUZZER': {'pin': 24, 'type': 'Output (Relay)'} 
}

state = {
    "object_count": 0,
    "batch_target": 20,
    "gate_wait_time": 10,
    "gate_status": "Closed",
    "ir_status": "Clear",
    "system_status": "Initializing",
    "lock": threading.Lock(),
    "ble_connection_status": "Disconnected",
    "ble_printer_client": None,
    "ble_loop": None, # ## FIX: Added to hold the BLE event loop
    "printer_enabled": False,
    "last_printed_payload": "N/A",
    "batches_completed": 0,
    "beep_on_count_ms": 100,
    "beep_on_complete_ms": 2000,
    "beep_on_reset_ms": 100,
    "last_count_timestamp": 0,
    "debounce_time_ms": 500,
    "last_debounce_timestamp": 0,
}

ir_sensor = None
gate_relay = None
green_led = None
red_led = None
buzzer = None

def initialize_hardware():
    global ir_sensor, gate_relay, green_led, red_led, buzzer
    print("[Hardware] Initializing GPIO objects...")
    try:
        ir_sensor = Button(PIN_CONFIG['IR_SENSOR']['pin'], pull_up=True, bounce_time=0.05)
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

def broadcast_status():
    with state['lock']:
        status_data = {k: v for k, v in state.items() if k not in ['lock', 'ble_printer_client', 'ble_loop']}
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
        complete_beep_duration_s = state['beep_on_complete_ms'] / 1000.0
        reset_beep_duration_s = state['beep_on_reset_ms'] / 1000.0
    broadcast_status()
    buzzer.beep(on_time=complete_beep_duration_s, n=1, background=True)
    time.sleep(0.5)
    close_gate()
    with state['lock']:
        wait_time = state['gate_wait_time']
        state['system_status'] = f"Waiting for {wait_time}s"
    broadcast_status()
    print(f"Waiting for {wait_time} seconds...")
    time.sleep(wait_time)
    print("Resetting for next batch.")
    with state['lock']:
        state['object_count'] = 0
        state['system_status'] = "Resetting..."
        state['last_count_timestamp'] = 0
    broadcast_status()
    buzzer.beep(on_time=reset_beep_duration_s, off_time=0.2, n=3, background=True)
    open_gate()
    with state['lock']:
        state['system_status'] = "Ready to Count"
    broadcast_status()

def debounce_alert():
    if not buzzer: return
    print("DEBOUNCE ALERT: A rapid signal was ignored.")
    buzzer.beep(on_time=0.1, off_time=0.1, n=5, background=True)

def object_detected():
    with state['lock']:
        state['ir_status'] = "Blocked"
    broadcast_status()
    
def object_passed():
    if not buzzer: return
    
    is_valid_count = False
    is_debounce_event = False
    printer_enabled_locally = False
    
    count = 0
    target = 0
    count_beep_duration_s = 0

    with state['lock']:
        if state['ir_status'] != "Blocked":
            return

        state['ir_status'] = "Clear"
        current_time_s = time.time()

        if state['gate_status'] != "Open" or state['system_status'] not in ["Ready to Count", "Counting"]:
            print(f"Count ignored: System not ready (Gate: {state['gate_status']}, Status: {state['system_status']}).")
        
        elif (current_time_s - state['last_count_timestamp']) * 1000 < state['debounce_time_ms']:
            time_since = (current_time_s - state['last_count_timestamp']) * 1000
            print(f"Debounce ignored. Only {time_since:.0f}ms since last valid count.")
            state['last_debounce_timestamp'] = current_time_s
            is_debounce_event = True
        
        else:
            is_valid_count = True
            state['last_count_timestamp'] = current_time_s
            state['object_count'] += 1
            state['system_status'] = "Counting"
            count = state['object_count']
            target = state['batch_target']
            count_beep_duration_s = state['beep_on_count_ms'] / 1000.0
            printer_enabled_locally = state['printer_enabled']

    broadcast_status()

    if is_debounce_event:
        debounce_alert()

    if is_valid_count:
        print(f"VALID Count Registered. New Count: {count}")
        buzzer.beep(on_time=count_beep_duration_s, n=1, background=True)
        if printer_enabled_locally:
            print_thread = threading.Thread(target=send_print_job, daemon=True)
            print_thread.start()
        if count >= target:
            threading.Thread(target=handle_batch_completion, daemon=True).start()

def system_startup():
    print("[Hardware] Starting system startup sequence...")
    if not initialize_hardware(): return
    with state['lock']:
        state['printer_enabled'] = database.get_setting('printer_enabled', 'false') == 'true'
        state['beep_on_count_ms'] = int(database.get_setting('beep_on_count_ms', 100))
        state['beep_on_complete_ms'] = int(database.get_setting('beep_on_complete_ms', 2000))
        state['beep_on_reset_ms'] = int(database.get_setting('beep_on_reset_ms', 100))
    close_gate()
    time.sleep(2)
    with state['lock']:
        reset_beep_duration_s = state['beep_on_reset_ms'] / 1000.0
    buzzer.beep(on_time=reset_beep_duration_s, off_time=0.2, n=3, background=True)
    open_gate()
    with state['lock']:
        state['system_status'] = "Ready to Count"
        state['last_count_timestamp'] = 0
    broadcast_status()
    print("[Hardware] System is ready.")

def get_live_pin_status():
    if not ir_sensor: return {k: 0 for k in PIN_CONFIG.keys()}
    return { 'IR_SENSOR': ir_sensor.value, 'GATE_RELAY': gate_relay.value, 'GREEN_LED': green_led.value, 'RED_LED': red_led.value, 'BUZZER': buzzer.value }

def cleanup_gpio():
    print("Cleaning up GPIO...")
    for device in [ir_sensor, gate_relay, green_led, red_led, buzzer]:
        if device and not device.closed:
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
        with state['lock']:
            state['last_printed_payload'] = payload
            client = state.get('ble_printer_client')
            is_connected = client and client.is_connected
        
        broadcast_status()
        
        if is_connected:
            print(f"[Print Job] Using UUID: {char_uuid}")
            print(f"[Print Job] Sending payload: '{payload}'")
            # ## FIX: Use the new thread-safe runner
            coro = client.write_gatt_char(char_uuid, payload.encode('utf-8'))
            ble.run_on_ble_loop(coro)
            print("[Print Job] Data sent successfully.")
        else:
            print("[Print Job] Error: Printer is not connected. Aborting print job.")
    except Exception as e:
        print(f"[Print Job] An exception occurred: {e}")