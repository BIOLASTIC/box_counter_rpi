"""
This is the CORRECTED version of system.py.
It ONLY contains functions for getting system-level information.
All duplicated gpiozero hardware initializations have been removed.
"""
import psutil
import time
import subprocess

# Uptime calculation starts when the module is first imported
start_time = time.time()

def get_cpu_temp():
    """Reads the CPU temperature from the system file."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            # The value in the file is in millidegrees Celsius
            temp = int(f.read().strip()) / 1000.0
        return f"{temp:.1f}°C"
    except (FileNotFoundError, ValueError):
        return "N/A"

def get_system_health_info():
    """Compiles all system health metrics into a dictionary."""
    uptime_seconds = time.time() - start_time
    # Format the uptime into HH:MM:SS
    uptime_string = time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))
    
    return {
        "cpu_usage": f"{psutil.cpu_percent()}%",
        "cpu_temp": get_cpu_temp(),
        "memory_usage": f"{psutil.virtual_memory().percent}%",
        "uptime": uptime_string
    }

def get_network_info():
    """Gets the current WiFi SSID and IP address."""
    ip_addr = "Not connected"
    ssid = "Not connected"
    try:
        # Get IP Address. The 'hostname -I' command can return multiple IPs. We take the first one.
        ip_addr = subprocess.check_output(['hostname', '-I']).decode('utf-8').strip().split()[0]
    except Exception:
        # This will fail if there is no network connection at all.
        pass
    
    try:
        # Get WiFi SSID. This will fail if not connected to a WiFi network.
        ssid = subprocess.check_output(['iwgetid', '-r']).decode('utf-8').strip()
    except Exception:
        # This is expected if using Ethernet or no connection.
        pass
        
    return {"ip_address": ip_addr, "ssid": ssid}