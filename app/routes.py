"""
Definitive version of routes.py with all features, including the new
support page and system shutdown API endpoint.
"""
import subprocess
from flask import Blueprint, render_template, jsonify, request
from . import hardware, wifi, ble, database, system

main_bp = Blueprint('main', __name__)

# --- Page Rendering Routes ---
@main_bp.route('/')
def index(): return render_template('index.html')

@main_bp.route('/manual-control')
def manual_control(): return render_template('main/manual_control.html')

@main_bp.route('/diagnostics')
def diagnostics(): return render_template('main/diagnostics.html', pin_config=hardware.PIN_CONFIG)

@main_bp.route('/system-health')
def system_health(): return render_template('main/system_health.html')

@main_bp.route('/network-status')
def network_status(): return render_template('main/network_status.html')

@main_bp.route('/wifi-configure')
def wifi_configure(): return render_template('wifi/configure.html')

@main_bp.route('/ble-configure')
def ble_configure():
    saved_address = database.get_setting('printer_address')
    saved_char = database.get_setting('write_characteristic_uuid')
    return render_template('ble/configure.html', saved_address=saved_address, saved_char=saved_char)

@main_bp.route('/app-settings')
def app_settings(): return render_template('main/app_settings.html')

@main_bp.route('/printer-configure')
def printer_configure(): return render_template('main/printer_configure.html')

@main_bp.route('/admin-unlock')
def admin_unlock_page(): return render_template('admin/unlock.html')

# --- NEW: Support Page Route ---
@main_bp.route('/support')
def support():
    return render_template('main/support.html')


# --- API Endpoints ---
@main_bp.route('/api/status')
def api_status():
    with hardware.state['lock']:
        return jsonify({k: v for k, v in hardware.state.items() if k not in ['lock', 'ble_printer_client']})

@main_bp.route('/api/pin_status')
def api_pin_status():
    return jsonify({
        'IR_SENSOR': hardware.ir_sensor.value, 'GATE_RELAY': hardware.gate_relay.value,
        'GREEN_LED': hardware.green_led.value, 'RED_LED': hardware.red_led.value,
        'BUZZER': hardware.buzzer.value
    })

@main_bp.route('/api/system_health')
def api_system_health(): return jsonify(system.get_system_health_info())

@main_bp.route('/api/network_status')
def api_network_status():
    ble_address = database.get_setting('printer_address')
    network_info = system.get_network_info()
    network_info['wifi_connected'] = (network_info['ssid'] != "Not connected")
    network_info['ble_connected'] = (ble_address is not None)
    network_info['ble_device'] = ble_address or 'None'
    network_info['eth_connected'] = (network_info['ip_address'] != "Not connected" and not network_info['wifi_connected'])
    return jsonify(network_info)

@main_bp.route('/api/manual_relay_control', methods=['POST'])
def api_manual_relay_control():
    device, action = request.form.get('device'), request.form.get('action')
    relay_map = {'gate': hardware.gate_relay, 'green_led': hardware.green_led, 'red_led': hardware.red_led}
    if device in relay_map:
        if action == 'on': relay_map[device].on()
        elif action == 'off': relay_map[device].off()
        return jsonify({"success": True, "message": f"{device} turned {action}."})
    elif device == 'buzzer' and action == 'beep':
        hardware.buzzer.beep(on_time=0.2, n=1, background=True)
        return jsonify({"success": True, "message": "Buzzer beeped."})
    return jsonify({"success": False, "message": "Invalid device or action."}), 400

@main_bp.route('/api/set_config', methods=['POST'])
def api_set_config():
    with hardware.state['lock']:
        hardware.state['batch_target'] = int(request.form.get('batch_target'))
        hardware.state['gate_wait_time'] = int(request.form.get('gate_wait_time'))
    return jsonify({"success": True, "message": "Configuration updated!"})

@main_bp.route('/api/reset_counter', methods=['POST'])
def api_reset_counter():
    with hardware.state['lock']:
        hardware.state['object_count'] = 0; hardware.state['system_status'] = "Ready to Count"
    return jsonify({"success": True, "message": "Live count has been reset."})

@main_bp.route('/api/wifi/scan', methods=['POST'])
def api_wifi_scan(): return jsonify(wifi.scan_wifi())

@main_bp.route('/api/wifi/connect', methods=['POST'])
def api_wifi_connect(): return jsonify(wifi.connect_to_wifi(request.form.get('ssid'), request.form.get('password')))

@main_bp.route('/api/ble/scan', methods=['POST'])
def api_ble_scan(): return jsonify(ble.run_async(ble.scan_ble_devices()))

@main_bp.route('/api/ble/get-characteristics', methods=['POST'])
def api_ble_get_characteristics(): return jsonify(ble.run_async(ble.get_characteristics(request.form.get('address'))))

@main_bp.route('/api/ble/save-device', methods=['POST'])
def api_ble_save_device():
    database.set_setting('printer_address', request.form.get('address'))
    database.set_setting('write_characteristic_uuid', request.form.get('characteristic_uuid'))
    return jsonify({"success": True, "message": "Default printer saved successfully."})

@main_bp.route('/api/ble/test-print', methods=['POST'])
def api_ble_test_print():
    address, char_uuid, text = database.get_setting('printer_address'), database.get_setting('write_characteristic_uuid'), request.form.get('text')
    return jsonify(ble.run_async(ble.write_to_device(address, char_uuid, text)))

@main_bp.route('/api/unlock', methods=['POST'])
def api_unlock():
    unlock_code = request.form.get('code')
    if unlock_code == "RPI_MASTER_8080":
        try:
            subprocess.run(['pkill', 'chromium-browser']); return jsonify({"success": True, "message": "Browser terminated."})
        except Exception as e: return jsonify({"success": False, "message": f"Error: {e}"})
    else: return jsonify({"success": False, "message": "Invalid Code"}), 403

@main_bp.route('/api/restart_application', methods=['POST'])
def api_restart_application():
    try:
        subprocess.run(['sudo', '/bin/systemctl', 'restart', 'conveyor.service'], check=True)
        return jsonify({"success": True, "message": "Application is restarting..."})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@main_bp.route('/api/reboot_system', methods=['POST'])
def api_reboot_system():
    try:
        subprocess.run(['sudo', '/bin/systemctl', 'reboot'], check=True)
        return jsonify({"success": True, "message": "System is rebooting..."})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

# --- NEW: System Shutdown API ---
@main_bp.route('/api/shutdown_system', methods=['POST'])
def api_shutdown_system():
    try:
        # Use poweroff for a safe shutdown.
        subprocess.run(['sudo', '/bin/systemctl', 'poweroff'], check=True)
        return jsonify({"success": True, "message": "System is shutting down..."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500