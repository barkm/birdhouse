#!/bin/bash

sudo $(which uv) run service.py install --name camera-server --command "$(which uv) run fastapi run main.py"