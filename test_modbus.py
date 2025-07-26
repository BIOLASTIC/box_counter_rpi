import time
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException

# --- Configuration ---
# These settings must exactly match your hardware setup.
PORT = '/dev/ttyUSB0'
BAUDRATE = 9600
PARITY = 'N'
STOPBITS = 1
BYTESIZE = 8
SLAVE_ID = 1

def run_test():
    """
    This script attempts to connect to a Modbus RTU device and read a single register.
    It is used to isolate and diagnose connection issues outside of the main application.
    """
    print("--- Modbus Connection Test ---")
    print(f"Target Port: {PORT}")
    print(f"Settings: {BAUDRATE} baud, {BYTESIZE}{PARITY}{STOPBITS}")
    print(f"Slave ID: {SLAVE_ID}")
    print("-" * 30)

    # 1. Initialize the Modbus Client
    try:
        client = ModbusSerialClient(
            port=PORT,
            baudrate=BAUDRATE,
            parity=PARITY,
            stopbits=STOPBITS,
            bytesize=BYTESIZE,
            timeout=2  # Increased timeout for more reliability
        )
        print("[INFO] Client configured.")
    except Exception as e:
        print(f"[FATAL] Failed to initialize the client object: {e}")
        return

    # 2. Attempt to Connect
    print("[INFO] Attempting to connect to the serial port...")
    try:
        is_connected = client.connect()
    except Exception as e:
        print(f"[FATAL] An error occurred during the .connect() call: {e}")
        print("        This often indicates a low-level system or hardware issue.")
        is_connected = False
        
    if not is_connected:
        print("\n[RESULT] FAILURE: The Modbus client could NOT connect.")
        print("         Troubleshooting Steps:")
        print("         1. Is the user in the 'dialout' group? (Have you rebooted since adding it?)")
        print("         2. Is the USB adapter securely plugged in?")
        print("         3. Is the I/O module powered on and correctly wired (A to A, B to B)?")
        print("-" * 30)
        return

    print("[INFO] Connection successful! The port was opened.")
    print("[INFO] Now attempting to communicate with the device...")
    
    # 3. Attempt to Read Data
    try:
        # We will try to read the first discrete input (Channel 1, Address 0)
        read_request = client.read_discrete_inputs(address=0, count=1, slave=SLAVE_ID)

        if read_request.isError():
            print("\n[RESULT] PARTIAL FAILURE: Connected to the port, but the device did not respond correctly.")
            print(f"         Modbus Error: {read_request}")
            print("         Troubleshooting Steps:")
            print("         1. Is the Slave ID set to '1' on the physical device?")
            print("         2. Is the wiring correct (A/B terminals)?")
            print("         3. Is the device powered on?")
        else:
            print(f"[INFO] Received response: {read_request.bits}")
            print("\n[RESULT] SUCCESS! Communication with the Modbus device is working correctly.")
            print("         The issue is likely within the main Flask application's logic or threading.")

    except ModbusIOException as e:
        print(f"\n[RESULT] FAILURE: A Modbus I/O error occurred after connecting: {e}")
        print("         This usually indicates a timeout. Check wiring and device power.")
    except Exception as e:
        print(f"\n[RESULT] FAILURE: An unexpected error occurred during the read operation: {e}")

    # 4. Clean Up
    client.close()
    print("[INFO] Client connection closed.")
    print("-" * 30)


if __name__ == "__main__":
    run_test()