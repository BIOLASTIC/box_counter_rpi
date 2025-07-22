
sudo systemctl daemon-reload
sudo systemctl restart conveyor.service
sudo systemctl stop conveyor.service
sudo systemctl start conveyor.service

source .venv/bin/activate

sudo nano /etc/systemd/system/conveyor.service


[Unit]
Description=Conveyor Control Flask Application
# This ensures the service starts after the network is ready
After=network-online.target
Wants=network-online.target

[Service]
# IMPORTANT: Change the user and paths below
User=pi
Group=www-data

# Set the absolute path to your project's root folder (the one containing run.py)
WorkingDirectory=/home/kobidkunda/project/counting

# Set the absolute path to your python executable and your run.py script
ExecStart=/usr/bin/python3 /home/kobidkunda/project/counting/run.py

# Restart the service automatically if it fails
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target


sudo systemctl daemon-reload      # Reload systemd to recognize the new file
sudo systemctl enable conveyor.service  # Enable the service to start on every boot
sudo systemctl start conveyor.service   # Start the service immediately to test it



nano ~/.config/lxsession/LXDE-pi/autostart


@chromium-browser --kiosk --incognito --disable-pinch --noerrdialogs --disable-session-crashed-bubble http://localhost:5000

nano ~/.config/autostart/kiosk.desktop


