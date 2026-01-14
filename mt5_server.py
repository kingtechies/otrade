#!/usr/bin/env python3
"""
MT5 RPyC Bridge Server
Run this script on a Windows machine (or Wine with Python + MetaTrader5) 
to enable real trading from the Linux bot.

Usage:
    On Windows: python mt5_server.py
    On Linux with Wine: wine python.exe mt5_server.py
"""

import rpyc
from rpyc.utils.server import ThreadedServer
import MetaTrader5 as mt5
import time
import sys

class MT5Service(rpyc.Service):
    """RPyC service that exposes MT5 functions over the network"""
    
    def exposed_initialize(self):
        """Initialize MT5 connection"""
        return mt5.initialize()
    
    def exposed_shutdown(self):
        """Shutdown MT5 connection"""
        mt5.shutdown()
    
    def exposed_login(self, login, password, server):
        """Login to MT5 account"""
        return mt5.login(login=int(login), password=str(password), server=str(server))
    
    def exposed_account_info(self):
        """Get account information"""
        return mt5.account_info()
    
    def exposed_symbol_info(self, symbol):
        """Get symbol information"""
        return mt5.symbol_info(symbol)
    
    def exposed_symbol_info_tick(self, symbol):
        """Get symbol tick"""
        return mt5.symbol_info_tick(symbol)
    
    def exposed_positions_get(self, ticket=None):
        """Get positions"""
        if ticket:
            return mt5.positions_get(ticket=ticket)
        return mt5.positions_get()
    
    def exposed_orders_get(self):
        """Get pending orders"""
        return mt5.orders_get()
    
    def exposed_order_send(self, request):
        """Send order"""
        # Convert rpyc netref to dict
        req = dict(request)
        return mt5.order_send(req)
    
    def exposed_copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
        """Get rates/candles"""
        return mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)
    
    def exposed_last_error(self):
        """Get last error"""
        return mt5.last_error()


def main():
    print("=" * 60)
    print("MT5 RPyC Bridge Server for OTrade")
    print("=" * 60)
    
    # Initialize MT5
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        sys.exit(1)
    
    print(f"[OK] MT5 initialized")
    print(f"[OK] Terminal: {mt5.terminal_info().name}")
    print(f"[OK] Version: {mt5.version()}")
    
    # Start RPyC server
    server = ThreadedServer(
        MT5Service, 
        port=18812,
        protocol_config={
            'allow_public_attrs': True,
            'allow_pickle': True
        }
    )
    
    print(f"[OK] Server listening on port 18812")
    print("=" * 60)
    print("Keep this running while the trading bot operates.")
    print("Press Ctrl+C to stop.")
    print("=" * 60)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        mt5.shutdown()
        print("MT5 shutdown complete")


if __name__ == "__main__":
    main()
