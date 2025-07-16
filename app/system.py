"""
This module contains functions for getting system-level information.
It now includes a function for checking live internet connectivity.
"""
import psutil
import time
import subprocess
import requests # <-- New import

# Uptime calculation starts when the module is first imported
start_time = time.time()

def check_internet_connection():
    """Checks for a live internet connection by making a request to a reliable server."""
    # Using a timeout is crucial so this function doesn't block for too long.
    try:
        requests.get("http://www.google.com", timeout=3)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False

def get_cpu_temp():
    """Reads the CPU temperature from the system file."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read().strip()) / 1000.0
        return f"{temp:.1f}°C"
    except (FileNotFoundError, ValueError):
        return "N/A"

def get_system_health_info():
    """Compiles all system health metrics into a dictionary."""
    uptime_seconds = time.time() - start_time
    uptime_string = time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))
    
    return {
        "cpu_usage": f"{psutil.cpu_percent()}%",
        "cpu_temp": get_cpu_temp(),
        "memory_usage": f"{psutil.virtual_memory().percent}%",
        "uptime": uptime_string
    }

def get_consolidated_network_info():
    """
    Gets all network interface information (IP, SSID, Strength, Type) and
    checks for a live internet connection.
    """
    info = {
        "ip_address": "Not connected",
        "wifi_ssid": "N/A",
        "wifi_strength": 0,
        "is_wifi": False,
        "is_ethernet": False,
        "has_internet": False,
    }
    
    try:
        # Check for internet first
        info["has_internet"] = check_internet_connection()

        # Get IP Address. 'hostname -I' can return multiple IPs, we take the first.
        ip_addr = subprocess.check_output(['hostname', '-I'], text=True).strip().split()
        if ip_addr:
            info["ip_address"] = ip_addr[0]

        # Check WiFi details
        wifi_output = subprocess.check_output(['iwgetid'], text=True).strip()
        if "ESSID" in wifi_output:
            info["is_wifi"] = True
            info["wifi_ssid"] = wifi_output.split('ESSID:"')[1][:-1]
            # Get signal strength
            nmcli_output = subprocess.check_output(['nmcli', '-t', '-f', 'ACTIVE,SIGNAL', 'dev', 'wifi'], text=True)
            for line in nmcli_output.strip().split('\n'):
                if line.startswith('yes:'):
                    info["wifi_strength"] = int(line.split(':')[1])
                    break
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        # This can fail if no network is active or tools are not present.
        # Check if an IP exists but WiFi is not active, suggesting Ethernet.
        if info["ip_address"] != "Not connected":
            info["is_ethernet"] = True
    
    # Final check for ethernet if wifi wasn't detected
    if info["ip_address"] != "Not connected" and not info["is_wifi"]:
        info["is_ethernet"] = True

    return info