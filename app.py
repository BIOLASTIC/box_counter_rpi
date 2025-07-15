import time
import threading
from flask import Flask, render_template, request, jsonify
from gpiozero import LED, Button, Buzzer
import logging

# --- Suppress Flask's default logging to keep the console clean ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- Pin Definitions (for diagnostics page) ---
PIN_CONFIG = {
    'IR_SENSOR': {'pin': 17, 'type': 'Input (NPN)'},
    'GATE_RELAY': {'pin': 22, 'type': 'Output (Relay)'},
    'GREEN_LED': {'pin': 27, 'type': 'Output (Relay)'},
    'RED_LED': {'pin': 23, 'type': 'Output (Relay)'},
    'BUZZER': {'pin': 24, 'type': 'Output (Relay)'}
}

# --- Hardware Device Initialization (gpiozero) ---
ir_sensor = Button(PIN_CONFIG['IR_SENSOR']['pin'], pull_up=True)
gate_relay = LED(PIN_CONFIG['GATE_RELAY']['pin'])
green_led = LED(PIN_CONFIG['GREEN_LED']['pin'])
red_led = LED(PIN_CONFIG['RED_LED']['pin'])
buzzer = Buzzer(PIN_CONFIG['BUZZER']['pin'])

# --- Global State Dictionary ---
state = {
    "object_count": 0,
    "batch_target": 20,
    "gate_wait_time": 10,
    "gate_status": "Closed",
    "ir_status": "Clear",
    "system_status": "Initializing",
    "lock": threading.Lock()
}

# --- Core Control Functions ---
def close_gate():
    with state['lock']:
        if state['gate_status'] != "Closed":
            gate_relay.on()
            state['gate_status'] = "Closed"
            update_lights()
            print("Gate Closed.")

def open_gate():
    with state['lock']:
        if state['gate_status'] != "Open":
            gate_relay.off()
            state['gate_status'] = "Open"
            update_lights()
            print("Gate Open.")

def update_lights():
    if state['gate_status'] == "Open":
        green_led.on()
        red_led.off()
    else:
        green_led.off()
        red_led.on()

def handle_batch_completion():
    print("Batch complete.")
    with state['lock']:
        state['system_status'] = "Batch Complete: Closing Gate"

    buzzer.beep(on_time=2.0, n=1, background=True)
    time.sleep(0.5)
    close_gate()
    
    with state['lock']:
        wait_time = state['gate_wait_time']
        state['system_status'] = f"Waiting for {wait_time}s"
    
    print(f"Waiting for {wait_time} seconds...")
    time.sleep(wait_time)
    
    print("Resetting for next batch.")
    with state['lock']:
        state['object_count'] = 0
        state['system_status'] = "Ready to Count"

    buzzer.beep(on_time=0.1, off_time=0.2, n=3, background=True)
    open_gate()

# --- NEW COUNTING LOGIC: Event Handlers for IR Sensor ---

def object_detected():
    """Called when the object *starts* blocking the sensor."""
    with state['lock']:
        state['ir_status'] = "Blocked"

def object_passed():
    """Called when the object has *finished* passing the sensor."""
    with state['lock']:
        # Update status first
        state['ir_status'] = "Clear"
        
        # Only count if the gate is open and the system is in a counting state
        if state['gate_status'] != "Open" or state['system_status'] not in ["Ready to Count", "Counting"]:
            return
        
        state['object_count'] += 1
        state['system_status'] = "Counting"
        count = state['object_count']
        target = state['batch_target']

    print(f"Object Passed. Count: {count}")
    
    # Beep for 1 second on each count (non-blocking)
    buzzer.beep(on_time=1.0, n=1, background=True)
    
    # Check if batch is complete
    if count >= target:
        completion_thread = threading.Thread(target=handle_batch_completion, daemon=True)
        completion_thread.start()

# Assign the functions to the correct sensor events
ir_sensor.when_pressed = object_detected  # Object starts blocking the sensor
ir_sensor.when_released = object_passed   # Object has finished passing

# --- System Startup ---
def system_startup():
    with state['lock']:
        state['system_status'] = "Initializing"
    close_gate()
    time.sleep(2)

    buzzer.beep(on_time=0.1, off_time=0.2, n=3, background=True)
    open_gate()
    with state['lock']:
        state['system_status'] = "Ready to Count"
    print("System is ready.")

# --- Flask Web Server ---
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/diagnostics')
def diagnostics():
    # Pass the static pin configuration to the template
    return render_template('diagnostics.html', pin_config=PIN_CONFIG)

@app.route('/status')
def status():
    with state['lock']:
        state_for_json = state.copy()
        state_for_json.pop('lock', None)
        return jsonify(state_for_json)

@app.route('/pin_status')
def pin_status():
    # Reads the live electrical value from each pin
    live_pins = {
        'IR_SENSOR': ir_sensor.value, # 1 for clear, 0 for blocked
        'GATE_RELAY': gate_relay.value, # 1 for on, 0 for off
        'GREEN_LED': green_led.value,
        'RED_LED': red_led.value,
        'BUZZER': buzzer.value
    }
    return jsonify(live_pins)

@app.route('/set_config', methods=['POST'])
def set_config():
    try:
        with state['lock']:
            state['batch_target'] = int(request.form['batch_target'])
            state['gate_wait_time'] = int(request.form['gate_wait_time'])
            print(f"Config updated: Batch Target={state['batch_target']}, Wait Time={state['gate_wait_time']}")
        return jsonify({"success": True, "message": "Configuration updated successfully!"})
    except (ValueError, KeyError) as e:
        return jsonify({"success": False, "message": f"Invalid input: {e}"})

@app.route('/reset_counter', methods=['POST'])
def reset_counter():
    with state['lock']:
        state['object_count'] = 0
        state['system_status'] = "Ready to Count"
        print("Counter has been reset from web interface.")
    return jsonify({"success": True, "message": "Live count has been reset to 0."})

# --- Main Execution ---
if __name__ == '__main__':
    try:
        startup_thread = threading.Thread(target=system_startup, daemon=True)
        startup_thread.start()
        
        print("Starting web server on http://0.0.0.0:5000")
        app.run(host='0.0.0.0', port=5000)

    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
    finally:
        ir_sensor.close()
        gate_relay.close()
        green_led.close()
        red_led.close()
        buzzer.close()
        print("GPIO devices closed.")