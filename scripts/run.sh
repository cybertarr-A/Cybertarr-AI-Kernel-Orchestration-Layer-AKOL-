#!/bin/bash
set -e

# Must run as root for eBPF and Cgroups
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

cd "$(dirname "$0")/.."

echo "Starting Cybertarr API and AI Engine..."
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "Starting Cybertarr C Daemon..."
cd daemon
./cybertarr-daemon

# If daemon exits
kill $API_PID
