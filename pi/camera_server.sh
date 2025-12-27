#!/bin/bash

SERVICE_NAME=camera-server
UV=$(which uv)

if [[ "$1" == "install" ]]; then
  $UV sync
  sudo $UV run service install --name $SERVICE_NAME --command "$(which uv) run --group sensor fastapi run main.py"
elif [[ "$1" == "uninstall" ]]; then
  $UV sync
  sudo $UV run service uninstall --name $SERVICE_NAME 
else
  echo "Usage: $0 <install|uninstall>"
  exit 1
fi
