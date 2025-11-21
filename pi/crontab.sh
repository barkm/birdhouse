#!/bin/bash

export NAME="${1-birdhouse}"
export SERVER_PORT="${2-8000}"

envsubst < crontab.txt | sudo crontab -