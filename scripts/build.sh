#!/bin/bash
set -e

echo "[BUILD] Compiling Cybertarr AKOL Stack"

# Ensure we are in the cybertarr-akol root dir
cd "$(dirname "$0")/.."

echo "1. Building eBPF Kernel Tracker..."
cd ebpf
make clean
make
cd ..

echo "2. Building Userspace C Daemon..."
cd daemon
make clean
make
cd ..

echo "3. Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

echo "[BUILD] Build Complete Successfully!"
