#!/bin/bash

if [[ -z "${1}" ]]; then
    echo "Usage: $0 <domain> [server_port]" >&2
    exit 1
fi

DOMAIN="${1}"
SERVER_PORT="${2-5000}"

if [[ -z $(which caddy) ]]; then
    sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    chmod o+r /etc/apt/sources.list.d/caddy-stable.list
    sudo apt update
    sudo apt install -y caddy
fi

envsubst < Caddyfile > /etc/caddy/Caddyfile
sudo systemctl reload caddy