#!/bin/bash
HOSTNAME=$(hostname)
envsubst < Caddyfile > /etc/caddy/Caddyfile