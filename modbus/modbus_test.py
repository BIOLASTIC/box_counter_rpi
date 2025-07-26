from flask import Flask, request, render_template_string
from pymodbus.client import ModbusSerialClient, ModbusTcpClient
from pymodbus.exceptions import ModbusException

app = Flask(__name__)

# HTML template for the web interface
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Modbus Tester</title>
</head>
<body>
    <h1>Modbus Connection Setup</h1>
    <form method="post" action="/connect">
        <label>Connection Type:</label><br>
        <input type="radio" name="conn_type" value="serial" checked> Serial (RTU)<br>
        <input type="radio" name="conn_type" value="tcp"> TCP/IP<br><br>
        
        <label>Serial Port (e.g., /dev/ttyUSB0):</label>
        <input type="text" name="serial_port" value="/dev/ttyUSB0"><br>
        <label>Baud Rate:</label>
        <input type="number" name="baudrate" value="9600"><br>
        <label>Data Bits:</label>
        <input type="number" name="bytesize" value="8"><br>
        <label>Parity:</label>
        <select name="parity">
            <option value="N">None</option>
        </select><br>
        <label>Stop Bits:</label>
        <input type="number" name="stopbits" value="1"><br><br>
        
        <label>TCP IP Address:</label>
        <input type="text" name="tcp_ip" value="192.168.1.53"><br>
        <label>TCP Port:</label>
        <input type="number" name="tcp_port" value="502"><br><br>
        
        <input type="submit" value="Connect">
    </form>
    
    {% if message %}
        <p>{{ message }}</p>
    {% endif %}
    
    {% if connected %}
        <h2>Write Single Coil (Function 05)</h2>
        <form method="post" action="/write_coil">
            <label>Slave ID:</label>
            <input type="number" name="slave_id" value="1"><br>
            <label>Address:</label>
            <input type="number" name="address" value="0"><br>
            <label>Value:</label>
            <input type="radio" name="value" value="1" checked> On
            <input type="radio" name="value" value="0"> Off<br><br>
            <input type="submit" value="Write Coil">
        </form>
        
        <h2>Write Single Register (Function 06)</h2>
        <form method="post" action="/write_register">
            <label>Slave ID:</label>
            <input type="number" name="slave_id" value="1"><br>
            <label>Address:</label>
            <input type="number" name="address" value="0"><br>
            <label>Value (16-bit int):</label>
            <input type="number" name="value" value="0"><br><br>
            <input type="submit" value="Write Register">
        </form>
    {% endif %}
</body>
</html>
'''

client = None
connected = False

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML, connected=connected, message=None)

@app.route('/connect', methods=['POST'])
def connect():
    global client, connected
    conn_type = request.form.get('conn_type')
    
    try:
        if conn_type == 'serial':
            client = ModbusSerialClient(
                port=request.form.get('serial_port'),
                baudrate=int(request.form.get('baudrate')),
                bytesize=int(request.form.get('bytesize')),
                parity=request.form.get('parity'),
                stopbits=int(request.form.get('stopbits')),
                timeout=3
            )
        elif conn_type == 'tcp':
            client = ModbusTcpClient(
                host=request.form.get('tcp_ip'),
                port=int(request.form.get('tcp_port')),
                timeout=3
            )
        
        if client.connect():
            connected = True
            return render_template_string(HTML, connected=connected, message="Connected successfully!")
        else:
            return render_template_string(HTML, connected=False, message="Connection failed.")
    except Exception as e:
        return render_template_string(HTML, connected=False, message=f"Error: {str(e)}")

@app.route('/write_coil', methods=['POST'])
def write_coil():
    if not connected:
        return render_template_string(HTML, connected=False, message="Not connected.")
    
    try:
        slave_id = int(request.form.get('slave_id'))
        address = int(request.form.get('address'))
        value = bool(int(request.form.get('value')))
        
        result = client.write_coil(address, value, slave=slave_id)
        if not result.isError():
            return render_template_string(HTML, connected=connected, message="Coil written successfully!")
        else:
            return render_template_string(HTML, connected=connected, message="Failed to write coil.")
    except ModbusException as e:
        return render_template_string(HTML, connected=connected, message=f"Modbus Error: {str(e)}")
    except Exception as e:
        return render_template_string(HTML, connected=connected, message=f"Error: {str(e)}")

@app.route('/write_register', methods=['POST'])
def write_register():
    if not connected:
        return render_template_string(HTML, connected=False, message="Not connected.")
    
    try:
        slave_id = int(request.form.get('slave_id'))
        address = int(request.form.get('address'))
        value = int(request.form.get('value'))
        
        result = client.write_register(address, value, slave=slave_id)
        if not result.isError():
            return render_template_string(HTML, connected=connected, message="Register written successfully!")
        else:
            return render_template_string(HTML, connected=connected, message="Failed to write register.")
    except ModbusException as e:
        return render_template_string(HTML, connected=connected, message=f"Modbus Error: {str(e)}")
    except Exception as e:
        return render_template_string(HTML, connected=connected, message=f"Error: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
