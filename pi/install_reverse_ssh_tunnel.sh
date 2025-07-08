#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: $0 <remote_host>"
  exit 1
fi

REMOTE_HOST="$1"

sudo $(which uv) run service.py install \
    --name reverse-ssh-tunnel \
    --command "$(which autossh) -M 0 -N -o "ServerAliveInterval=60" -o "ServerAliveCountMax=3" -R 8000:localhost:8000 -R 2222:localhost:22 ${REMOTE_HOST}"