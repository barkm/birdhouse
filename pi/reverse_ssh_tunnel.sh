#!/bin/bash

SERVICE_NAME=reverse-ssh-tunnel
UV=$(which uv)

if [[ "$1" == "install" ]]; then
  REMOTE_HOST="$2"
  SSH_PORT="${3-2222}"
  SERVER_PORT="${4-8000}"
  if [[ -z "$REMOTE_HOST" ]]; then
    echo "Usage: $0 install <remote_host> [ssh-port] [server-port]"
    exit 1
  fi
  AUTO_SSH_PATH=$(which autossh)
  if [[ -z "$AUTO_SSH_PATH" ]]; then
    echo "autossh not found. Please install it first."
    exit 1
  fi
  $UV sync
  sudo $UV run service install \
      --name $SERVICE_NAME \
      --command "$AUTO_SSH_PATH -M 0 -N -o "ServerAliveInterval=60" -o "ServerAliveCountMax=3" -R ${SERVER_PORT}:localhost:8000 -R ${SSH_PORT}:localhost:22 -L 5000:localhost:5000 ${REMOTE_HOST}" \
      --environment "AUTOSSH_GATETIME=0"
elif [[ "$1" == "uninstall" ]]; then
  $UV sync
  sudo $UV run service uninstall --name $SERVICE_NAME 
else
  echo "Usage: $0 install <remote_host> or $0 uninstall"
  exit 1
fi

