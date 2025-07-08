#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: $0 <remote_host>"
  exit 1
fi

REMOTE_HOST="$1"
SERVICE_NAME="reverse-ssh-tunnel"

echo "Creating systemd service ${SERVICE_NAME}"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Persistent Reverse SSH Tunnel to ${REMOTE_HOST}
After=network.target

[Service]
User=$USER
ExecStart=/usr/bin/autossh -M 0 -N -o "ServerAliveInterval=60" -o "ServerAliveCountMax=3" -R 8000:localhost:8000 -R 2222:localhost:22 ${REMOTE_HOST}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# === Step 3: Enable and start the service ===
echo "Enabling and starting the systemd service ${SERVICE_NAME}"
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

echo "Reverse SSH tunnel is now active."

