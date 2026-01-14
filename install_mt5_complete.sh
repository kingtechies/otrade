#!/bin/bash
# =============================================================================
# COMPLETE MT5 INSTALLATION FOR LINUX VPS - RETRY UNTIL SUCCESS
# This script will keep retrying until MT5 is fully installed and working
# =============================================================================

set -o pipefail

# Configuration
WINE_PREFIX="/home/jeph/.wine64"
MT5_DIR="/home/jeph/otrade"
MT5_INSTALLER="$MT5_DIR/mt5setup.exe"
DISPLAY_NUM=99
MAX_RETRIES=10
TIMEOUT_LONG=300
TIMEOUT_SHORT=120

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step() { echo -e "${BLUE}[→]${NC} $1"; }

export WINEPREFIX=$WINE_PREFIX
export WINEARCH=win64

echo ""
echo "============================================================"
echo "   OTRADE - COMPLETE MT5 INSTALLATION FOR LINUX VPS"
echo "   This script will keep retrying until everything works"
echo "============================================================"
echo ""

# =============================================================================
# STEP 1: Ensure Xvfb is running
# =============================================================================
start_display() {
    log_step "Starting virtual display..."
    pkill -f "Xvfb :$DISPLAY_NUM" 2>/dev/null || true
    sleep 1
    Xvfb :$DISPLAY_NUM -screen 0 1280x1024x24 -ac +extension GLX +render -noreset &
    XVFB_PID=$!
    sleep 3
    export DISPLAY=:$DISPLAY_NUM
    
    if ps -p $XVFB_PID > /dev/null 2>&1; then
        log_info "Virtual display started (PID: $XVFB_PID)"
        return 0
    else
        log_error "Failed to start virtual display"
        return 1
    fi
}

# =============================================================================
# STEP 2: Initialize Wine environment
# =============================================================================
init_wine() {
    log_step "Initializing Wine 64-bit environment..."
    
    if [ ! -d "$WINE_PREFIX/drive_c" ]; then
        log_info "Creating new Wine prefix..."
        wineboot --init 2>/dev/null
        sleep 10
    fi
    
    if [ -d "$WINE_PREFIX/drive_c" ]; then
        log_info "Wine prefix ready at $WINE_PREFIX"
        return 0
    else
        log_error "Wine initialization failed"
        return 1
    fi
}

# =============================================================================
# STEP 3: Install Wine dependencies with retries
# =============================================================================
install_wine_deps() {
    log_step "Installing Windows dependencies via winetricks..."
    
    local deps=("corefonts" "vcrun2019" "vcrun2015")
    
    for dep in "${deps[@]}"; do
        log_info "Installing $dep..."
        for retry in {1..3}; do
            if timeout $TIMEOUT_SHORT winetricks -q $dep 2>/dev/null; then
                log_info "$dep installed successfully"
                break
            else
                log_warn "Retry $retry for $dep..."
                sleep 5
            fi
        done
    done
    
    return 0
}

# =============================================================================
# STEP 4: Download MT5 installer if needed
# =============================================================================
download_mt5() {
    log_step "Checking MT5 installer..."
    
    if [ -f "$MT5_INSTALLER" ] && [ -s "$MT5_INSTALLER" ]; then
        log_info "MT5 installer found: $MT5_INSTALLER"
        return 0
    fi
    
    log_info "Downloading Exness MT5 installer..."
    for retry in {1..5}; do
        if wget -q --show-progress --timeout=60 \
            "https://download.mql5.com/cdn/web/exness.technologies.ltd/mt5/exness5setup.exe" \
            -O "$MT5_INSTALLER"; then
            log_info "Download complete"
            return 0
        else
            log_warn "Download retry $retry..."
            sleep 10
        fi
    done
    
    log_error "Failed to download MT5 installer"
    return 1
}

# =============================================================================
# STEP 5: Install MT5 with retries
# =============================================================================
install_mt5() {
    log_step "Installing MetaTrader 5..."
    
    # Check if already installed
    MT5_TERMINAL=$(find "$WINE_PREFIX" -name "terminal64.exe" 2>/dev/null | head -1)
    if [ -n "$MT5_TERMINAL" ]; then
        log_info "MT5 already installed at: $MT5_TERMINAL"
        return 0
    fi
    
    for retry in {1..5}; do
        log_info "Installation attempt $retry..."
        
        # Kill any existing MT5 processes
        pkill -f "mt5setup" 2>/dev/null || true
        pkill -f "terminal64" 2>/dev/null || true
        sleep 2
        
        # Start installer
        wine "$MT5_INSTALLER" /auto &
        INSTALLER_PID=$!
        
        # Wait for installation with progress
        log_info "Waiting for MT5 installation (up to 5 minutes)..."
        for i in {1..60}; do
            sleep 5
            
            MT5_TERMINAL=$(find "$WINE_PREFIX" -name "terminal64.exe" 2>/dev/null | head -1)
            if [ -n "$MT5_TERMINAL" ]; then
                log_info "MT5 INSTALLED SUCCESSFULLY!"
                log_info "Terminal location: $MT5_TERMINAL"
                kill $INSTALLER_PID 2>/dev/null || true
                return 0
            fi
            
            # Show progress
            if [ $((i % 6)) -eq 0 ]; then
                log_info "Still installing... ($((i * 5))s elapsed)"
            fi
        done
        
        log_warn "Installation attempt $retry timed out"
        kill $INSTALLER_PID 2>/dev/null || true
        sleep 5
    done
    
    log_error "MT5 installation failed after $MAX_RETRIES attempts"
    return 1
}

# =============================================================================
# STEP 6: Download Python for Wine
# =============================================================================
download_python() {
    log_step "Downloading Python 3.10 for Wine..."
    
    PYTHON_INSTALLER="$MT5_DIR/python-3.10-win.exe"
    
    if [ -f "$PYTHON_INSTALLER" ] && [ -s "$PYTHON_INSTALLER" ]; then
        log_info "Python installer already exists"
        return 0
    fi
    
    for retry in {1..5}; do
        if wget -q --show-progress --timeout=120 \
            "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe" \
            -O "$PYTHON_INSTALLER"; then
            log_info "Python downloaded successfully"
            return 0
        else
            log_warn "Python download retry $retry..."
            sleep 10
        fi
    done
    
    log_warn "Python download failed - will continue anyway"
    return 0
}

# =============================================================================
# STEP 7: Install Python in Wine
# =============================================================================
install_python_wine() {
    log_step "Installing Python in Wine environment..."
    
    PYTHON_INSTALLER="$MT5_DIR/python-3.10-win.exe"
    PYTHON_EXE="$WINE_PREFIX/drive_c/Python310/python.exe"
    
    if [ -f "$PYTHON_EXE" ]; then
        log_info "Python already installed in Wine"
        return 0
    fi
    
    if [ ! -f "$PYTHON_INSTALLER" ]; then
        log_warn "Python installer not found, skipping..."
        return 0
    fi
    
    log_info "Installing Python (this may take a few minutes)..."
    wine "$PYTHON_INSTALLER" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 &
    PYTHON_PID=$!
    
    for i in {1..60}; do
        sleep 5
        if [ -f "$PYTHON_EXE" ]; then
            log_info "Python installed successfully in Wine!"
            kill $PYTHON_PID 2>/dev/null || true
            return 0
        fi
    done
    
    kill $PYTHON_PID 2>/dev/null || true
    log_warn "Python installation may have timed out"
    return 0
}

# =============================================================================
# STEP 8: Install MetaTrader5 Python package in Wine
# =============================================================================
install_mt5_python() {
    log_step "Installing MetaTrader5 Python package in Wine..."
    
    PYTHON_EXE="$WINE_PREFIX/drive_c/Python310/python.exe"
    
    if [ ! -f "$PYTHON_EXE" ]; then
        log_warn "Wine Python not found, skipping MT5 package"
        return 0
    fi
    
    wine "$PYTHON_EXE" -m pip install --upgrade pip 2>/dev/null || true
    wine "$PYTHON_EXE" -m pip install MetaTrader5 rpyc 2>/dev/null || true
    
    log_info "MT5 Python package installation attempted"
    return 0
}

# =============================================================================
# STEP 9: Create the RPyC bridge server
# =============================================================================
create_bridge_server() {
    log_step "Creating MT5 RPyC bridge server..."
    
    cat > "$MT5_DIR/mt5_bridge_server.py" << 'PYEOF'
#!/usr/bin/env python3
"""
MT5 RPyC Bridge Server - Runs inside Wine to expose MT5 API
Start with: wine python.exe mt5_bridge_server.py
"""
import rpyc
from rpyc.utils.server import ThreadedServer
import MetaTrader5 as mt5
import sys

class MT5BridgeService(rpyc.Service):
    def exposed_initialize(self):
        return mt5.initialize()
    
    def exposed_shutdown(self):
        mt5.shutdown()
    
    def exposed_login(self, login, password, server):
        return mt5.login(login=int(login), password=str(password), server=str(server))
    
    def exposed_account_info(self):
        info = mt5.account_info()
        if info:
            return {
                'login': info.login, 'balance': info.balance,
                'equity': info.equity, 'margin': info.margin,
                'margin_free': info.margin_free, 'profit': info.profit,
                'leverage': info.leverage, 'currency': info.currency
            }
        return None
    
    def exposed_symbol_info(self, symbol):
        return mt5.symbol_info(symbol)
    
    def exposed_symbol_info_tick(self, symbol):
        return mt5.symbol_info_tick(symbol)
    
    def exposed_positions_get(self, ticket=None):
        if ticket:
            return mt5.positions_get(ticket=ticket)
        return mt5.positions_get()
    
    def exposed_order_send(self, request):
        return mt5.order_send(dict(request))
    
    def exposed_copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
        return mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)
    
    def exposed_last_error(self):
        return mt5.last_error()

if __name__ == "__main__":
    print("=" * 50)
    print("MT5 RPyC Bridge Server for OTrade")
    print("=" * 50)
    
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        sys.exit(1)
    
    print(f"MT5 initialized: {mt5.terminal_info()}")
    
    server = ThreadedServer(MT5BridgeService, port=18812,
        protocol_config={'allow_public_attrs': True, 'allow_pickle': True})
    
    print("Server listening on port 18812...")
    print("Keep this running while the trading bot operates.")
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        mt5.shutdown()
PYEOF
    
    log_info "Bridge server script created"
    return 0
}

# =============================================================================
# STEP 10: Verify installation
# =============================================================================
verify_installation() {
    log_step "Verifying MT5 installation..."
    
    MT5_TERMINAL=$(find "$WINE_PREFIX" -name "terminal64.exe" 2>/dev/null | head -1)
    
    if [ -n "$MT5_TERMINAL" ]; then
        log_info "============================================================"
        log_info "MT5 INSTALLATION VERIFIED SUCCESSFULLY!"
        log_info "Terminal: $MT5_TERMINAL"
        log_info "============================================================"
        echo ""
        echo "To start real trading:"
        echo "  1. Start MT5: ./start_mt5.sh"
        echo "  2. Login to your Exness account in MT5"
        echo "  3. Run bot: source venv/bin/activate && python main.py"
        echo ""
        return 0
    else
        log_error "MT5 verification failed - terminal not found"
        return 1
    fi
}

# =============================================================================
# STEP 11: Create startup script
# =============================================================================
create_startup_script() {
    log_step "Creating startup scripts..."
    
    cat > "$MT5_DIR/start_mt5.sh" << 'EOF'
#!/bin/bash
export WINEPREFIX=/home/jeph/.wine64
export DISPLAY=:99

# Start Xvfb if not running
if ! pgrep -f "Xvfb :99" > /dev/null; then
    Xvfb :99 -screen 0 1280x1024x24 &
    sleep 2
fi

MT5=$(find $WINEPREFIX -name "terminal64.exe" | head -1)
if [ -n "$MT5" ]; then
    echo "Starting MT5: $MT5"
    wine "$MT5" &
    echo "MT5 started. Use VNC to access GUI:"
    echo "  x11vnc -display :99 -nopw -forever &"
else
    echo "MT5 not found. Run ./install_mt5_complete.sh first"
fi
EOF
    chmod +x "$MT5_DIR/start_mt5.sh"
    
    cat > "$MT5_DIR/start_bridge.sh" << 'EOF'
#!/bin/bash
export WINEPREFIX=/home/jeph/.wine64
export DISPLAY=:99
cd /home/jeph/otrade
PYTHON="$WINEPREFIX/drive_c/Python310/python.exe"
if [ -f "$PYTHON" ]; then
    wine "$PYTHON" mt5_bridge_server.py
else
    echo "Wine Python not found. Install Python in Wine first."
fi
EOF
    chmod +x "$MT5_DIR/start_bridge.sh"
    
    log_info "Startup scripts created"
    return 0
}

# =============================================================================
# MAIN EXECUTION - RETRY UNTIL SUCCESS
# =============================================================================
main_loop() {
    local attempt=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        echo ""
        echo "============================================================"
        echo "   INSTALLATION ATTEMPT $attempt of $MAX_RETRIES"
        echo "============================================================"
        echo ""
        
        # Run all steps
        start_display || { log_warn "Display failed, retrying..."; sleep 5; continue; }
        init_wine || { log_warn "Wine init failed, retrying..."; sleep 5; continue; }
        install_wine_deps
        download_mt5 || { log_warn "MT5 download failed, retrying..."; sleep 10; continue; }
        
        if install_mt5; then
            download_python
            install_python_wine
            install_mt5_python
            create_bridge_server
            create_startup_script
            
            if verify_installation; then
                echo ""
                log_info "============================================================"
                log_info "   ALL INSTALLATIONS COMPLETED SUCCESSFULLY!"
                log_info "============================================================"
                return 0
            fi
        fi
        
        log_warn "Attempt $attempt failed, retrying in 30 seconds..."
        attempt=$((attempt + 1))
        sleep 30
    done
    
    log_error "Installation failed after $MAX_RETRIES attempts"
    return 1
}

# Start the main loop
main_loop
