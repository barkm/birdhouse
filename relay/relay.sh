#!/bin/bash

SERVICE_NAME=relay
UV=$(which uv)

if [[ "$1" == "install" ]]; then
  sudo $UV run service install \
    --name $SERVICE_NAME \
    --command "$(which uv) run fastapi run main.py --port 5000"
elif [[ "$1" == "uninstall" ]]; then
  sudo $UV run service uninstall --name $SERVICE_NAME 
else
  echo "Usage: $0 <install|uninstall>"
  exit 1
fi
