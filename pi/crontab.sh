#!/bin/bash

export SERVER_PORT="${1-8000}"

envsubst < crontab.txt | sudo crontab -