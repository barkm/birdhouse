#!/bin/bash

SERVICE_NAME=relay
UV=$(which uv)

if [[ "$1" == "install" ]]; then
  sudo $UV run service.py install \
    --name $SERVICE_NAME \
    --environment ALLOWED_EMAILS=$ALLOWED_EMAILS \
    --command "$(which uv) run fastapi run main.py --port 5000"
elif [[ "$1" == "uninstall" ]]; then
  sudo $UV run service.py uninstall --name $SERVICE_NAME 
else
  echo "Usage: $0 <install|uninstall>"
  exit 1
fi
