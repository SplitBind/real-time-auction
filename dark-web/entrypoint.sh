#!/bin/bash

# Ensure proper permissions for Tor hidden service directory
mkdir -p /var/lib/tor/my-website/
chmod 700 /var/lib/tor/my-website/

# Start Tor in the background
tor -f /etc/tor/torrc &

# Start Nginx in the background
nginx

# Start FastAPI/Uvicorn in the foreground (keeps container alive)
uvicorn main:app --host 127.0.0.1 --port 8000
