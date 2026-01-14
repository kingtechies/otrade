#!/bin/bash
# =============================================================================
# MT5 Linux VPS Setup Script for OTrade Real Trading
# =============================================================================

set -e

echo "=============================================="
echo "  OTrade MT5 Setup for Ubuntu VPS"
echo "=============================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
WINE_PREFIX="$HOME/.wine64"
MT5_INSTALLER="$HOME/otrade/mt5setup.exe"
DISPLAY_NUM=99

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Step 1: Check/Install dependencies
log_info "Checking dependencies..."

if ! command -v wine &> /dev/null; then
    log_info "Installing Wine..."
    sudo dpkg --add-architecture i386
    sudo apt update
    sudo apt install -y wine64 wine32
fi

if ! command -v Xvfb &> /dev/null; then
    log_info "Installing Xvfb..."
    sudo apt install -y xvfb
fi

if ! command -v winetricks &> /dev/null; then
    log_info "Installing winetricks..."
    sudo apt install -y winetricks
fi

# Step 2: Initialize Wine 64-bit environment
log_info "Initializing Wine environment..."
export WINEPREFIX=$WINE_PREFIX
export WINEARCH=win64

if [ ! -d "$WINE_PREFIX" ]; then
    wineboot --init 2>/dev/null || true
    sleep 5
fi

# Step 3: Install required Windows components
log_info "Installing Windows components via winetricks..."
winetricks -q corefonts vcrun2019 2>/dev/null || true

# Step 4: Start Xvfb virtual display
log_info "Starting virtual display..."
pkill -f "Xvfb :$DISPLAY_NUM" 2>/dev/null || true
Xvfb :$DISPLAY_NUM -screen 0 1280x1024x24 &
XVFB_PID=$!
sleep 3
export DISPLAY=:$DISPLAY_NUM

# Step 5: Install MT5
log_info "Installing MetaTrader 5..."
if [ -f "$MT5_INSTALLER" ]; then
    wine "$MT5_INSTALLER" /auto &
    INSTALLER_PID=$!
    
    # Wait for installation with timeout
    log_info "Waiting for MT5 installation (max 5 minutes)..."
    for i in {1..60}; do
        sleep 5
        if find "$WINE_PREFIX" -name "terminal64.exe" 2>/dev/null | grep -q terminal64; then
            log_info "MT5 installed successfully!"
            break
        fi
        echo -n "."
    done
    echo ""
    
    # Kill installer if still running
    kill $INSTALLER_PID 2>/dev/null || true
else
    log_error "MT5 installer not found at $MT5_INSTALLER"
    log_info "Downloading from Exness..."
    wget -q "https://download.mql5.com/cdn/web/exness.technologies.ltd/mt5/exness5setup.exe" -O "$MT5_INSTALLER" || true
fi

# Step 6: Find MT5 terminal
MT5_TERMINAL=$(find "$WINE_PREFIX" -name "terminal64.exe" 2>/dev/null | head -1)
if [ -z "$MT5_TERMINAL" ]; then
    log_error "MT5 terminal not found. Installation may have failed."
    log_info "Trying direct download of Exness MT5..."
    
    # Alternative: Download Exness-specific installer
    wget -q "https://download.mql5.com/cdn/web/exness.technologies.ltd/mt5/exness5setup.exe" -O /tmp/exness_mt5.exe
    wine /tmp/exness_mt5.exe /auto &
    sleep 120
    
    MT5_TERMINAL=$(find "$WINE_PREFIX" -name "terminal64.exe" 2>/dev/null | head -1)
fi

if [ -n "$MT5_TERMINAL" ]; then
    log_info "MT5 Terminal found: $MT5_TERMINAL"
    echo "MT5_PATH=$MT5_TERMINAL" >> "$HOME/otrade/.env"
    
    # Step 7: Download and install Python for Wine
    log_info "Setting up Python in Wine..."
    PYTHON_INSTALLER="/tmp/python-3.10-win.exe"
    if [ ! -f "$PYTHON_INSTALLER" ]; then
        wget -q "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe" -O "$PYTHON_INSTALLER" &
        log_info "Downloading Python in background..."
    fi
    
    # Step 8: Create systemd service for MT5
    log_info "Creating systemd service..."
    cat > /tmp/mt5-trading.service << 'EOF'
[Unit]
Description=MetaTrader 5 Trading Server
After=network.target

[Service]
Type=simple
Environment=DISPLAY=:99
Environment=WINEPREFIX=/home/jeph/.wine64
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1280x1024x24
ExecStart=/usr/bin/wine /path/to/terminal64.exe
Restart=always
RestartSec=10
User=jeph

[Install]
WantedBy=multi-user.target
EOF
    
    log_info "=============================================="
    log_info "MT5 Setup Complete!"
    log_info "=============================================="
    log_info "Next steps:"
    log_info "1. Start MT5: DISPLAY=:99 wine '$MT5_TERMINAL'"
    log_info "2. Login with your Exness credentials"
    log_info "3. Run the trading bot: python main.py"
else
    log_error "MT5 installation failed!"
    log_info "Manual installation required."
    log_info "Run: wine $MT5_INSTALLER"
fi

# Cleanup
kill $XVFB_PID 2>/dev/null || true

log_info "Script completed."
