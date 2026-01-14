#!/bin/bash
# =============================================================================
# Start MT5 Terminal in Headless Mode + RPyC Bridge Server
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WINE_PREFIX="/home/jeph/.wine64"
DISPLAY_NUM=99

echo "=============================================="
echo "  OTrade MT5 Trading Server"
echo "=============================================="

# Find MT5 terminal
MT5_TERMINAL=$(find "$WINE_PREFIX" -name "terminal64.exe" 2>/dev/null | head -1)

if [ -z "$MT5_TERMINAL" ]; then
    echo "[ERROR] MT5 not found. Run ./setup_mt5_linux.sh first."
    exit 1
fi

echo "[INFO] Found MT5 at: $MT5_TERMINAL"

# Start Xvfb if not running
if ! pgrep -f "Xvfb :$DISPLAY_NUM" > /dev/null; then
    echo "[INFO] Starting virtual display..."
    Xvfb :$DISPLAY_NUM -screen 0 1280x1024x24 &
    sleep 2
fi

export DISPLAY=:$DISPLAY_NUM
export WINEPREFIX=$WINE_PREFIX

# Start MT5 terminal
echo "[INFO] Starting MetaTrader 5..."
wine "$MT5_TERMINAL" /portable &
MT5_PID=$!

# Wait for MT5 to start
echo "[INFO] Waiting for MT5 to initialize..."
sleep 15

# Check if MT5 is running
if ps -p $MT5_PID > /dev/null 2>&1; then
    echo "[OK] MT5 is running (PID: $MT5_PID)"
    echo "[INFO] MT5 Terminal started successfully!"
    echo ""
    echo "=============================================="
    echo "IMPORTANT: You need to login to MT5 manually"
    echo "Use VNC or x11vnc to access the GUI:"
    echo "  x11vnc -display :99 -nopw -forever &"
    echo "  Then connect with VNC viewer to localhost:5900"
    echo "=============================================="
    echo ""
    echo "[INFO] Now starting the trading bot..."
    
    cd "$SCRIPT_DIR"
    source venv/bin/activate
    python main.py
else
    echo "[ERROR] MT5 failed to start"
    exit 1
fi
