"""
This version ensures that when a user sets a new configuration,
it is correctly saved to the database for persistence.
"""
import subprocess
from flask import Blueprint, render_template, jsonify, request
from . import hardware, wifi, database, system 

main_bp = Blueprint('main', __name__)

# --- Page Rendering Routes ---
@main_bp.route('/')
def index(): return render_template('index.html')
@main_bp.route('/manual-control')
def manual_control(): return render_template('main/manual_control.html')
@main_bp.route('/diagnostics')
def diagnostics(): 
    diag_config = hardware.get_diagnostics_config()
    return render_template('main/diagnostics.html', pin_config=diag_config)
@main_bp.route('/system-health')
def system_health(): return render_template('main/system_health.html')
@main_bp.route('/network-status')
def network_status(): return render_template('main/network_status.html')
@main_bp.route('/wifi-configure')
def wifi_configure(): return render_template('wifi/configure.html')
@main_bp.route('/app-settings')
def app_settings(): return render_template('main/app_settings.html')
@main_bp.route('/admin-unlock')
def admin_unlock_page(): return render_template('admin/unlock.html')
@main_bp.route('/support')
def support(): return render_template('main/support.html')


# --- API Endpoints ---
@main_bp.route('/api/status')
def api_status():
    with hardware.state['lock']: return jsonify({k: v for k, v in hardware.state.items() if k != 'lock'})

@main_bp.route('/api/pin_status')
def api_pin_status(): return jsonify(hardware.get_live_io_status())

@main_bp.route('/api/set_config', methods=['POST'])
def api_set_config():
    """
    NEW: This now saves the configuration to the database for persistence.
    """
    try:
        new_target = int(request.form['batch_target'])
        new_wait_time = int(request.form['gate_wait_time'])
        
        # Save to database
        database.set_setting('batch_target', new_target)
        database.set_setting('gate_wait_time', new_wait_time)
        
        # Update live state
        with hardware.state['lock']:
            hardware.state['batch_target'] = new_target
            hardware.state['gate_wait_time'] = new_wait_time
        
        hardware.broadcast_status()
        print(f"Config updated and saved: Batch Target={new_target}, Wait Time={new_wait_time}")
        return jsonify({"success": True, "message": "Configuration updated successfully!"})
    except (ValueError, KeyError) as e: 
        return jsonify({"success": False, "message": f"Invalid input: {e}"})

# ... (The rest of the routes file is unchanged) ...
@main_bp.route('/api/system_health')
def api_system_health(): return jsonify(system.get_system_health_info())
@main_bp.route('/api/network_status')
def api_network_status():
    network_info = system.get_consolidated_network_info()
    return jsonify({
        "ip_address": network_info["ip_address"], "ssid": network_info["wifi_ssid"],
        "wifi_connected": network_info["is_wifi"], "eth_connected": network_info["is_ethernet"],
    })
@main_bp.route('/api/manual_relay_control', methods=['POST'])
def api_manual_relay_control():
    device, action = request.form.get('device'), request.form.get('action')
    relay_map = {'green_led': hardware.green_led, 'red_led': hardware.red_led}
    if device == 'gate':
        if action == 'on': hardware.open_gate()
        elif action == 'off': hardware.close_gate()
        return jsonify({"success": True, "message": f"Gate action '{action}' triggered."})
    elif device in relay_map and relay_map[device]:
        if action == 'on': relay_map[device].on()
        elif action == 'off': relay_map[device].off()
        return jsonify({"success": True, "message": f"{device} turned {action}."})
    elif device == 'buzzer' and action == 'beep' and hardware.buzzer:
        hardware.buzzer.beep(on_time=0.2, n=1, background=True)
        return jsonify({"success": True, "message": "Buzzer beeped."})
    return jsonify({"success": False, "message": "Invalid device or action."}), 400
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
def api_wifi_connect(): return jsonify(wifi.connect_to_wifi(request.form.get('ssid'), request.form.get('password')))
@main_bp.route('/api/unlock', methods=['POST'])
def api_unlock():
    unlock_code = request.form.get('code')
    if unlock_code == "RPI_MASTER_8080":
        try: subprocess.run(['pkill', 'chromium-browser']); return jsonify({"success": True, "message": "Browser terminated."})
        except Exception as e: return jsonify({"success": False, "message": f"Error: {e}"})
    else: return jsonify({"success": False, "message": "Invalid Code"}), 403
@main_bp.route('/api/restart_application', methods=['POST'])
def api_restart_application():
    try: subprocess.run(['sudo', '/bin/systemctl', 'restart', 'conveyor.service'], check=True); return jsonify({"success": True, "message": "Application is restarting..."})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500
@main_bp.route('/api/reboot_system', methods=['POST'])
def api_reboot_system():
    try: subprocess.run(['sudo', '/bin/systemctl', 'reboot'], check=True); return jsonify({"success": True, "message": "System is rebooting..."})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500
@main_bp.route('/api/shutdown_system', methods=['POST'])
def api_shutdown_system():
    try: subprocess.run(['sudo', '/bin/systemctl', 'poweroff'], check=True); return jsonify({"success": True, "message": "System is shutting down..."})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500