"""
This is the final, definitive version of hardware.py.
It runs in a native OS thread and communicates with the web server
thread via a thread-safe queue instead of calling socketio.emit directly.
It uses the correct 'lgpio' pin factory for the Raspberry Pi 5.
"""
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device
Device.pin_factory = LGPIOFactory()

import time
import threading
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
from gpiozero import LED, Buzzer

from . import database
from app import status_queue

PIN_CONFIG = { 'GATE_RELAY': {'pin': 22}, 'GREEN_LED': {'pin': 27}, 'RED_LED': {'pin': 23}, 'BUZZER': {'pin': 24} }
MODBUS_CONFIG = {
    'port': '/dev/ttyUSB0', 'baudrate': 9600, 'parity': 'N', 'stopbits': 1, 'bytesize': 8,
    'slave_id': 1, 'ENTRY_SENSOR_CH': 4, 'EXIT_SENSOR_CH': 7
}
state = {
    "object_count": 0, "batch_target": 20, "gate_wait_time": 10, "objects_on_belt": 0,
    "gate_status": "Closed", "box_state": "Idle", "system_status": "Initializing",
    "lock": threading.Lock(), "batches_completed": 0,
    "entry_sensor_status": False, "exit_sensor_status": False,
}

gate_relay, green_led, red_led, buzzer = None, None, None, None
modbus_client, polling_thread = None, None
modbus_lock = threading.Lock()

def broadcast_status():
    """THE FIX: Instead of emitting, put the current state into the thread-safe queue."""
    with state['lock']:
        status_data = {k: v for k, v in state.items() if k != 'lock'}
    status_queue.put(status_data)

def initialize_hardware():
    global gate_relay, green_led, red_led, buzzer, modbus_client, polling_thread
    print("[Hardware] Initializing GPIO (using lgpio factory)...")
    try:
        gate_relay = LED(PIN_CONFIG['GATE_RELAY']['pin']); green_led = LED(PIN_CONFIG['GREEN_LED']['pin'])
        red_led = LED(PIN_CONFIG['RED_LED']['pin']); buzzer = Buzzer(PIN_CONFIG['BUZZER']['pin'])
        print("[Hardware] GPIO objects initialized successfully.")
    except Exception as e:
        print(f"[FATAL] GPIO FAILED: {e}");
        with state['lock']: state['system_status'] = f"GPIO FAILED: {e}"; broadcast_status(); return False
    print("[Hardware] Initializing Modbus client...")
    try:
        modbus_client = ModbusSerialClient(port=MODBUS_CONFIG['port'], baudrate=MODBUS_CONFIG['baudrate'], parity=MODBUS_CONFIG['parity'], stopbits=MODBUS_CONFIG['stopbits'], bytesize=MODBUS_CONFIG['bytesize'], timeout=2)
        if not modbus_client.connect(): raise ConnectionError(f"Failed to connect to Modbus device at {MODBUS_CONFIG['port']}")
        print("[Hardware] Modbus connected.")
    except Exception as e:
        print(f"[FATAL] MODBUS FAILED: {e}")
        with state['lock']: state['system_status'] = f"MODBUS FAILED: {e}"; broadcast_status(); return False
    polling_thread = threading.Thread(target=poll_sensors_loop, daemon=True); polling_thread.start()
    return True

def poll_sensors_loop():
    print("[Polling] Sensor polling thread started.")
    entry_ch_index, exit_ch_index = MODBUS_CONFIG['ENTRY_SENSOR_CH'] - 1, MODBUS_CONFIG['EXIT_SENSOR_CH'] - 1
    count_to_read = max(entry_ch_index, exit_ch_index) + 1
    while True:
        try:
            with modbus_lock:
                if not modbus_client or not modbus_client.connected:
                    print("[Polling] Modbus client disconnected. Reconnecting..."); modbus_client.connect(); time.sleep(5); continue
                rr = modbus_client.read_discrete_inputs(address=0, count=count_to_read, slave=MODBUS_CONFIG['slave_id'])
                if rr.isError() or not hasattr(rr, 'bits') or len(rr.bits) < count_to_read:
                    print(f"[POLLING WARNING] Invalid or short response from Modbus: {rr}"); time.sleep(1); continue
            inputs = rr.bits; entry_sensor_on = inputs[entry_ch_index]; exit_sensor_on = inputs[exit_ch_index]
            with state['lock']:
                state_changed = False
                if state['entry_sensor_status'] != entry_sensor_on: state['entry_sensor_status'] = entry_sensor_on; state_changed = True
                if state['exit_sensor_status'] != exit_sensor_on: state['exit_sensor_status'] = exit_sensor_on; state_changed = True
                current_box_state = state['box_state']
                if current_box_state == "Idle" and entry_sensor_on: state['box_state'] = "Entering"; state['objects_on_belt'] += 1; state_changed = True
                elif current_box_state == "Entering" and not entry_sensor_on: state['box_state'] = "Inside"
                elif current_box_state == "Inside" and exit_sensor_on: state['box_state'] = "Exiting"
                elif current_box_state == "Exiting" and not exit_sensor_on:
                    state['box_state'] = "Idle"; state['objects_on_belt'] = max(0, state['objects_on_belt'] - 1)
                    if state['gate_status'] == "Open" and state['system_status'] in ["Ready to Count", "Counting"]:
                        state['object_count'] += 1; state['system_status'] = "Counting"
                        count, target = state['object_count'], state['batch_target']
                        print(f"Object Passed. Count: {count}"); buzzer.beep(on_time=1.0, n=1, background=True)
                        if count >= target: threading.Thread(target=handle_batch_completion, daemon=True).start()
                    state_changed = True
                if state_changed: broadcast_status()
            time.sleep(0.05)
        except Exception as e:
            print(f"[ERROR in poll_sensors_loop]: {e}")
            with state['lock']: state['system_status'] = "MODBUS POLL FAILED"; broadcast_status(); time.sleep(5)

def system_startup():
    print("--- [STARTUP THREAD] Started ---")
    try:
        with state['lock']:
            print("[STARTUP THREAD] Loading configuration from database...")
            target = database.get_setting('batch_target', '20'); wait_time = database.get_setting('gate_wait_time', '10')
            state['batch_target'] = int(target); state['gate_wait_time'] = int(wait_time)
        print(f"[STARTUP THREAD] Config loaded: Batch Target={state['batch_target']}, Wait Time={state['gate_wait_time']}")
        broadcast_status()
        print("[STARTUP THREAD] Initializing hardware...")
        if not initialize_hardware(): print("[STARTUP THREAD] Hardware initialization failed. Startup aborted."); return
        print("[STARTUP THREAD] Performing initial gate sequence..."); close_gate(); time.sleep(2)
        buzzer.beep(on_time=0.1, off_time=0.2, n=3, background=True)
        open_gate()
        with state['lock']: state['system_status'] = "Ready to Count"
        broadcast_status(); print("--- [STARTUP THREAD] System is ready. ---")
    except Exception as e:
        print(f"--- [FATAL ERROR in STARTUP THREAD]: {e} ---")
        with state['lock']: state['system_status'] = "STARTUP FAILED"; broadcast_status()

# (All other functions are unchanged)
def get_diagnostics_config(): return {"ENTRY SENSOR": {"channel": f"Modbus CH {MODBUS_CONFIG.get('ENTRY_SENSOR_CH', 'N/A')}"},"EXIT SENSOR": {"channel": f"Modbus CH {MODBUS_CONFIG.get('EXIT_SENSOR_CH', 'N/A')}"},"GATE RELAY": {"channel": f"GPIO {PIN_CONFIG.get('GATE_RELAY', {}).get('pin', 'N/A')}"},"GREEN LED": {"channel": f"GPIO {PIN_CONFIG.get('GREEN_LED', {}).get('pin', 'N/A')}"},"RED LED": {"channel": f"GPIO {PIN_CONFIG.get('RED_LED', {}).get('pin', 'N/A')}"},"BUZZER": {"channel": f"GPIO {PIN_CONFIG.get('BUZZER', {}).get('pin', 'N/A')}"}}
def close_gate():
    with state['lock']:
        if state['gate_status'] != "Closed": gate_relay.on(); state['gate_status'] = "Closed"; update_lights(); print("Gate Closed.")
    broadcast_status()
def open_gate():
    with state['lock']:
        if state['gate_status'] != "Open": gate_relay.off(); state['gate_status'] = "Open"; update_lights(); print("Gate Open.")
    broadcast_status()
def update_lights():
    if state['gate_status'] == "Open": green_led.on(); red_led.off()
    else: green_led.off(); red_led.on()
def handle_batch_completion():
    print("Batch complete.")
    with state['lock']: state['system_status'] = "Batch Complete: Closing Gate"; state['batches_completed'] += 1
    broadcast_status(); buzzer.beep(on_time=2.0, n=1, background=True); time.sleep(0.5); close_gate()
    with state['lock']: wait_time = state['gate_wait_time']; state['system_status'] = f"Waiting for {wait_time}s"
    broadcast_status(); print(f"Waiting for {wait_time} seconds..."); time.sleep(wait_time)
    print("Resetting for next batch.")
    with state['lock']: state['object_count'] = 0; state['system_status'] = "Ready to Count"
    broadcast_status(); buzzer.beep(on_time=0.1, off_time=0.2, n=3, background=True); open_gate()
def get_live_io_status():
    status = {}
    with modbus_lock:
        try:
            if modbus_client and modbus_client.connected:
                count = max(MODBUS_CONFIG['ENTRY_SENSOR_CH'], MODBUS_CONFIG['EXIT_SENSOR_CH'])
                rr = modbus_client.read_discrete_inputs(address=0, count=count, slave=MODBUS_CONFIG['slave_id'])
                if not rr.isError() and hasattr(rr, 'bits') and len(rr.bits) >= count:
                    status["ENTRY_SENSOR"] = 1 if rr.bits[MODBUS_CONFIG['ENTRY_SENSOR_CH'] - 1] else 0
                    status["EXIT_SENSOR"] = 1 if rr.bits[MODBUS_CONFIG['EXIT_SENSOR_CH'] - 1] else 0
                else: status["SENSORS"] = "Modbus Error"
            else: status["SENSORS"] = "Disconnected"
        except Exception as e: status["SENSORS"] = str(e)
    try:
        if all([gate_relay, green_led, red_led, buzzer]):
            status['GATE_RELAY'] = gate_relay.value; status['GREEN_LED'] = green_led.value
            status['RED_LED'] = red_led.value; status['BUZZER'] = buzzer.value
        else: status["OUTPUTS"] = "GPIO Not Initialized"
    except Exception as e: status["OUTPUTS"] = str(e)
    return status
def cleanup_resources():
    print("Cleaning up resources...")
    if modbus_client and modbus_client.connected: modbus_client.close(); print("Modbus client closed.")
    for device in [gate_relay, green_led, red_led, buzzer]:
        if device: device.close()
    print("GPIO devices closed.")