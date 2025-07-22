"""
Definitive version of routes.py with all features. This version uses the
new thread-safe BLE loop runner for API calls.
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

@main_bp.route('/support')
def support(): return render_template('main/support.html')


# --- API Endpoints ---
@main_bp.route('/api/status')
def api_status():
    with hardware.state['lock']:
        # Exclude non-JSON serializable objects
        return jsonify({k: v for k, v in hardware.state.items() if k not in ['lock', 'ble_printer_client', 'ble_loop']})

@main_bp.route('/api/pin_status')
def api_pin_status():
    return jsonify(hardware.get_live_pin_status())

@main_bp.route('/api/system_health')
def api_system_health(): return jsonify(system.get_system_health_info())

@main_bp.route('/api/network_status')
def api_network_status():
    ble_address = database.get_setting('printer_address')
    network_info = system.get_consolidated_network_info()
    response_data = {
        "ip_address": network_info["ip_address"],
        "ssid": network_info["wifi_ssid"],
        "wifi_connected": network_info["is_wifi"],
        "eth_connected": network_info["is_ethernet"],
        "ble_connected": (ble_address is not None),
        "ble_device": ble_address or 'None'
    }
    return jsonify(response_data)


@main_bp.route('/api/manual_relay_control', methods=['POST'])
def api_manual_relay_control():
    data = request.json
    device, action = data.get('device'), data.get('action')
    if not hardware.green_led: 
        return jsonify({"success": False, "message": "Hardware not initialized."}), 503

    relay_map = {'green_led': hardware.green_led, 'red_led': hardware.red_led}

    if device == 'gate':
        if action == 'on': hardware.open_gate()
        elif action == 'off': hardware.close_gate()
        return jsonify({"success": True, "message": f"Gate action '{action}' triggered."})
    elif device in relay_map:
        if action == 'on': relay_map[device].on()
        elif action == 'off': relay_map[device].off()
        return jsonify({"success": True, "message": f"{device} turned {action}."})
    elif device == 'buzzer' and action == 'beep':
        hardware.buzzer.beep(on_time=0.2, n=1, background=True)
        return jsonify({"success": True, "message": "Buzzer beeped."})
    return jsonify({"success": False, "message": "Invalid device or action."}), 400

@main_bp.route('/api/set_config', methods=['POST'])
def api_set_config():
    try:
        data = request.json
        with hardware.state['lock']:
            hardware.state['batch_target'] = int(data.get('batch_target'))
            hardware.state['gate_wait_time'] = int(data.get('gate_wait_time'))
        hardware.broadcast_status()
        return jsonify({"success": True, "message": "Configuration updated successfully!"})
    except (ValueError, KeyError, TypeError) as e:
        return jsonify({"success": False, "message": f"Invalid input: {e}"})

@main_bp.route('/api/reset_counter', methods=['POST'])
def api_reset_counter():
    with hardware.state['lock']:
        hardware.state['object_count'] = 0
        if hardware.state['system_status'] not in ["Ready to Count", "Counting"]:
             hardware.state['system_status'] = "Ready to Count"
    hardware.broadcast_status()
    return jsonify({"success": True, "message": "Live count has been reset to 0."})

@main_bp.route('/api/wifi/scan', methods=['POST'])
def api_wifi_scan(): return jsonify(wifi.scan_wifi())

@main_bp.route('/api/wifi/connect', methods=['POST'])
def api_wifi_connect():
    data = request.json
    ssid = data.get('ssid')
    password = data.get('password')
    return jsonify(wifi.connect_to_wifi(ssid, password))

@main_bp.route('/api/ble/scan', methods=['POST'])
def api_ble_scan(): return jsonify(ble.run_async(ble.scan_ble_devices()))

@main_bp.route('/api/ble/get-characteristics', methods=['POST'])
def api_ble_get_characteristics():
    data = request.json
    address = data.get('address')
    return jsonify(ble.run_async(ble.get_characteristics(address)))

@main_bp.route('/api/ble/save-device', methods=['POST'])
def api_ble_save_device():
    data = request.json
    database.set_setting('printer_address', data.get('address'))
    database.set_setting('write_characteristic_uuid', data.get('characteristic_uuid'))
    return jsonify({"success": True, "message": "Default printer saved successfully."})

@main_bp.route('/api/ble/remove-device', methods=['POST'])
def api_ble_remove_device():
    try:
        database.remove_setting('printer_address')
        database.remove_setting('write_characteristic_uuid')
        return jsonify({"success": True, "message": "Default printer removed."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@main_bp.route('/api/ble/test-print', methods=['POST'])
def api_ble_test_print():
    data = request.json
    text_to_send = data.get('text')
    if not text_to_send:
        return jsonify({"success": False, "message": "No text provided."}), 400
    try:
        with hardware.state['lock']:
            client = hardware.state.get('ble_printer_client')
            is_connected = client and client.is_connected
            char_uuid = database.get_setting('write_characteristic_uuid')

        if not is_connected:
            return jsonify({"success": False, "message": "Printer is not connected."})
        if not char_uuid:
            return jsonify({"success": False, "message": "No write characteristic is saved."})
        
        print(f"[API Test Print] Sending to UUID: {char_uuid}")
        print(f"[API Test Print] Payload: '{text_to_send}'")
        
        # ## FIX: Use the new thread-safe runner
        coro = client.write_gatt_char(char_uuid, text_to_send.encode('utf-8'))
        ble.run_on_ble_loop(coro)
        
        return jsonify({"success": True, "message": f"Sent: '{text_to_send}'"})
    except Exception as e:
        print(f"[API Test Print] An error occurred: {e}")
        return jsonify({"success": False, "message": f"An error occurred: {e}"}), 500

@main_bp.route('/api/get_printer_config')
def get_printer_config():
    config = {
        "enabled": database.get_setting('printer_enabled', 'false') == 'true',
        "delay_ms": database.get_setting('printer_delay_ms', '0'),
        "var1": database.get_setting('printer_var1', 'PartNo:'),
        "val1": database.get_setting('printer_var1_val', '12345'),
        "var2": database.get_setting('printer_var2', 'QRCode:'),
        "val2": database.get_setting('printer_var2_val', 'ABC-XYZ'),
    }
    return jsonify(config)

@main_bp.route('/api/save_printer_config', methods=['POST'])
def save_printer_config():
    try:
        data = request.json
        database.set_setting('printer_enabled', str(data.get('enabled', False)).lower())
        database.set_setting('printer_delay_ms', str(data.get('delay_ms', 0)))
        database.set_setting('printer_var1', data.get('var1', ''))
        database.set_setting('printer_var1_val', data.get('val1', ''))
        database.set_setting('printer_var2', data.get('var2', ''))
        database.set_setting('printer_var2_val', data.get('val2', ''))
        with hardware.state['lock']:
            hardware.state['printer_enabled'] = data.get('enabled', False)
        hardware.broadcast_status()
        return jsonify({"success": True, "message": "Printer configuration saved successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"An error occurred: {e}"}), 500

@main_bp.route('/api/unlock', methods=['POST'])
def api_unlock():
    data = request.json
    unlock_code = data.get('code')
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
    except Exception as e: 
        return jsonify({"success": False, "message": f"Error: {e}. Ensure user has sudo rights."}), 500

@main_bp.route('/api/reboot_system', methods=['POST'])
def api_reboot_system():
    try:
        subprocess.run(['sudo', '/bin/systemctl', 'reboot'], check=True)
        return jsonify({"success": True, "message": "System is rebooting..."})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@main_bp.route('/api/shutdown_system', methods=['POST'])
def api_shutdown_system():
    try:
        subprocess.run(['sudo', '/bin/systemctl', 'poweroff'], check=True)
        return jsonify({"success": True, "message": "System is shutting down..."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500