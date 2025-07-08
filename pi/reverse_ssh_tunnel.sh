#!/bin/bash

SERVICE_NAME=reverse-ssh-tunnel
UV=$(which uv)

if [[ "$1" == "install" ]]; then
  REMOTE_HOST="$2"
  if [[ -z "$REMOTE_HOST" ]]; then
    echo "Usage: $0 install <remote_host>"
    exit 1
  fi
  sudo $UV run service.py install \
      --name $SERVICE_NAME \
      --command "$(which autossh) -M 0 -N -o "ServerAliveInterval=60" -o "ServerAliveCountMax=3" -R 8000:localhost:8000 -R 2222:localhost:22 ${REMOTE_HOST}"
elif [[ "$1" == "uninstall" ]]; then
  sudo $UV run service.py uninstall --name $SERVICE_NAME 
else
  echo "Usage: $0 install <remote_host> or $0 uninstall"
  exit 1
fi

