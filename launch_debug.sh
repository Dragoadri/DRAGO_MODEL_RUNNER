#!/bin/bash
LOG="/tmp/dmr_launch_debug.log"
exec > "$LOG" 2>&1
echo "=== LAUNCH DEBUG $(date) ==="
echo "DISPLAY=$DISPLAY"
echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY"
echo "XDG_SESSION_TYPE=$XDG_SESSION_TYPE"
echo "USER=$USER"
echo "HOME=$HOME"
echo "PATH=$PATH"
echo "==="

cd "/home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER" || { echo "CD FAILED"; exit 1; }
echo "CWD=$(pwd)"

PYTHON="/home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER/.venv/bin/python"
echo "PYTHON=$PYTHON"
"$PYTHON" --version || { echo "PYTHON NOT FOUND"; exit 1; }

echo "=== STARTING APP ==="
"$PYTHON" main.py
echo "=== APP EXITED: $? ==="
