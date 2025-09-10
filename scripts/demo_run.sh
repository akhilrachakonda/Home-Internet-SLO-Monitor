#!/usr/bin/env bash
set -e
make up
sleep 5
python -m webbrowser http://localhost:3000
