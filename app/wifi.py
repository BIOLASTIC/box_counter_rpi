"""
This module handles all WiFi-related tasks using the nmcli command-line tool.
"""
import subprocess
import time

def scan_wifi():
    """
    Scans for WiFi networks using nmcli in a machine-readable "terse" mode
    and parses the output robustly.
    """
    networks = []
    print("[WiFi] Starting WiFi network scan...")
    try:
        # Rescan to get the latest list from the hardware
        subprocess.run(['nmcli', 'dev', 'wifi', 'rescan'], timeout=10)
        time.sleep(5)  # Allow time for the hardware to complete the scan

        # --- THIS IS THE FIX ---
        # We now use '-t' for terse (machine-readable) mode and '-f' to specify fields.
        # nmcli will separate fields with a colon ':', which is much safer for parsing.
        command = ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY', 'dev', 'wifi', 'list', '--rescan', 'no']
        
        result = subprocess.check_output(command, text=True).strip()
        
        lines = result.split('\n')
        seen_ssids = set()

        for line in lines:
            if not line:
                continue # Skip empty lines

            try:
                # Split the line by the colon separator
                parts = line.split(':')
                
                # Basic validation to ensure the line has the expected number of parts
                if len(parts) < 3:
                    continue

                ssid = parts[0]
                signal_str = parts[1]
                security = parts[2] if parts[2] else "Open"

                # Check for duplicate SSIDs and ignore empty ones from nmcli
                if ssid and ssid not in seen_ssids:
                    networks.append({
                        "ssid": ssid,
                        "signal": int(signal_str), # This is now safe
                        "security": security
                    })
                    seen_ssids.add(ssid)

            except (ValueError, IndexError) as e:
                # This robust error handling ensures that one malformed network
                # name from nmcli doesn't crash the entire scan process.
                print(f"[WiFi] Warning: Could not parse line '{line}'. Error: {e}")
                continue

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[WiFi] Error scanning WiFi: {e}")
        return {"error": str(e)}

    print(f"[WiFi] Scan complete. Found {len(networks)} unique networks.")
    # Sort by signal strength, strongest first
    return sorted(networks, key=lambda x: x['signal'], reverse=True)


def connect_to_wifi(ssid, password):
    """Connects to a WiFi network using nmcli."""
    print(f"[WiFi] Attempting to connect to SSID: {ssid}")
    try:
        command = ['nmcli', 'dev', 'wifi', 'connect', ssid]
        if password:
            command.extend(['password', password])
            
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"[WiFi] Successfully connected to {ssid}")
            return {"success": True, "message": f"Successfully connected to {ssid}."}
        else:
            error_message = result.stderr.strip()
            print(f"[WiFi] Failed to connect to {ssid}: {error_message}")
            return {"success": False, "message": f"Failed to connect. Error: {error_message}"}
            
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Connection attempt timed out."}
    except Exception as e:
        print(f"[WiFi] An exception occurred during WiFi connection: {e}")
        return {"success": False, "message": f"An unexpected error occurred: {e}"}