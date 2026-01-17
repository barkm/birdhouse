#!/bin/bash

export NAME="${1-birdhouse}"
export URL="${2-http://localhost:8000}"

envsubst < crontab.txt | sudo crontab -