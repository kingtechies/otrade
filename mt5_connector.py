import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random

from config import config


TIMEFRAME_MAP = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 60, "H4": 240, "D1": 1440, "W1": 10080, "MN1": 43200
}


class MT5Connector:
    def __init__(self, host: str = "localhost", port: int = 18812):
        self.host = host
        self.port = port
        self.connected = False
        self._cache = {}
        self._positions = []
        self._order_counter = 1000
        self._balance = config.INITIAL_DEPOSIT
        self._equity = config.INITIAL_DEPOSIT
        self._profit = 0.0
        self._prices = {
            "XAUUSD": 2650.50,
            "USTECm": 21450.00
        }
        
    def connect(self) -> bool:
        try:
            import rpyc
            self.conn = rpyc.connect(self.host, self.port)
            self.mt5 = self.conn.root
            
            if not self.mt5.initialize():
                print("[MT5] Initialize failed, using simulation mode")
                return self._start_simulation()
            
            authorized = self.mt5.login(
                login=config.MT5_LOGIN,
                password=config.MT5_PASSWORD,
                server=config.MT5_SERVER
            )
            
            if not authorized:
                print("[MT5] Login failed, using simulation mode")
                return self._start_simulation()
            
            self.connected = True
            self.simulation = False
            print("[MT5] Connected to real account")
            return True
            
        except Exception as e:
            print(f"[MT5] Connection error: {e}")
            return self._start_simulation()
    
    def _start_simulation(self) -> bool:
        print("[MT5] Running in SIMULATION MODE")
        print(f"[MT5] Starting balance: ${self._balance:.2f}")
        self.connected = True
        self.simulation = True
        return True
    
    def disconnect(self):
        self.connected = False
        print("[MT5] Disconnected")
    
    def get_account_info(self) -> Dict[str, Any]:
        if not self.connected:
            return {}
        
        if hasattr(self, 'simulation') and self.simulation:
            self._update_simulation()
            return {
                "login": config.MT5_LOGIN,
                "balance": self._balance,
                "equity": self._equity,
                "margin": 100.0,
                "free_margin": self._equity - 100,
                "profit": self._profit,
                "leverage": 500,
                "currency": "USD"
            }
        
        info = self.mt5.account_info()
        return {
            "login": info.login,
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "profit": info.profit,
            "leverage": info.leverage,
            "currency": info.currency
        }
    
    def _update_simulation(self):
        total_profit = 0.0
        for pos in self._positions:
            current_price = self._get_sim_price(pos['symbol'])
            if pos['type'] == 'buy':
                profit = (current_price - pos['open_price']) * pos['volume'] * 100
            else:
                profit = (pos['open_price'] - current_price) * pos['volume'] * 100
            pos['current_price'] = current_price
            pos['profit'] = profit
            total_profit += profit
        
        self._profit = total_profit
        self._equity = self._balance + total_profit
    
    def _get_sim_price(self, symbol: str) -> float:
        if symbol not in self._prices:
            self._prices[symbol] = 1000.0
        
        change = random.uniform(-0.001, 0.001)
        self._prices[symbol] *= (1 + change)
        return self._prices[symbol]
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        if not self.connected:
            return None
        
        if hasattr(self, 'simulation') and self.simulation:
            price = self._get_sim_price(symbol)
            spread = 0.5 if symbol == "XAUUSD" else 1.0
            return {
                "symbol": symbol,
                "bid": price - spread/2,
                "ask": price + spread/2,
                "spread": int(spread * 10),
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
                "point": 0.01 if symbol == "XAUUSD" else 0.01,
                "digits": 2,
                "contract_size": 100,
                "tick_value": 1.0,
                "tick_size": 0.01
            }
        
        info = self.mt5.symbol_info(symbol)
        if info is None:
            return None
        
        tick = self.mt5.symbol_info_tick(symbol)
        
        return {
            "symbol": info.name,
            "bid": tick.bid if tick else info.bid,
            "ask": tick.ask if tick else info.ask,
            "spread": info.spread,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
            "point": info.point,
            "digits": info.digits,
            "contract_size": info.trade_contract_size,
            "tick_value": info.trade_tick_value,
            "tick_size": info.trade_tick_size
        }
    
    def get_rates(self, symbol: str, timeframe: str, count: int = 500) -> pd.DataFrame:
        if not self.connected:
            return pd.DataFrame()
        
        if hasattr(self, 'simulation') and self.simulation:
            return self._generate_sim_data(symbol, timeframe, count)
        
        tf = TIMEFRAME_MAP.get(timeframe, 15)
        rates = self.mt5.copy_rates_from_pos(symbol, tf, 0, count)
        
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
        
        df = pd.DataFrame(list(rates))
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        return df
    
    def _generate_sim_data(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        base_price = self._prices.get(symbol, 1000)
        
        dates = pd.date_range(end=datetime.now(), periods=count, freq='15min')
        
        np.random.seed(42 + hash(symbol + timeframe) % 1000)
        returns = np.random.randn(count) * 0.001
        prices = base_price * (1 + np.cumsum(returns))
        
        volatility = np.abs(np.random.randn(count)) * 0.002 * base_price
        
        df = pd.DataFrame({
            'open': prices,
            'high': prices + volatility,
            'low': prices - volatility,
            'close': prices + np.random.randn(count) * volatility * 0.5,
            'tick_volume': np.random.randint(100, 10000, count),
            'spread': np.random.randint(1, 10, count),
            'real_volume': np.random.randint(1000, 100000, count)
        }, index=dates)
        
        return df
    
    def get_all_timeframes(self, symbol: str) -> Dict[str, pd.DataFrame]:
        data = {}
        for tf in config.TIMEFRAMES:
            df = self.get_rates(symbol, tf)
            if not df.empty:
                data[tf] = df
        return data
    
    def get_realtime_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        info = self.get_symbol_info(symbol)
        if not info:
            return None
        
        return {
            "bid": info['bid'],
            "ask": info['ask'],
            "last": (info['bid'] + info['ask']) / 2,
            "volume": random.randint(100, 1000),
            "time": datetime.now()
        }
    
    def buy(self, symbol: str, volume: float, sl: float = 0, tp: float = 0) -> Optional[int]:
        return self._execute_order(symbol, "buy", volume, sl, tp)
    
    def sell(self, symbol: str, volume: float, sl: float = 0, tp: float = 0) -> Optional[int]:
        return self._execute_order(symbol, "sell", volume, sl, tp)
    
    def _execute_order(self, symbol: str, order_type: str, volume: float,
                       sl: float, tp: float) -> Optional[int]:
        if not self.connected:
            return None
        
        info = self.get_symbol_info(symbol)
        if not info:
            return None
        
        price = info['ask'] if order_type == 'buy' else info['bid']
        
        if hasattr(self, 'simulation') and self.simulation:
            ticket = self._order_counter
            self._order_counter += 1
            
            self._positions.append({
                "ticket": ticket,
                "symbol": symbol,
                "type": order_type,
                "volume": volume,
                "open_price": price,
                "current_price": price,
                "profit": 0.0,
                "sl": sl,
                "tp": tp,
                "time": datetime.now()
            })
            
            print(f"[SIM] Opened #{ticket} {order_type.upper()} {volume}L {symbol} @ {price:.2f}")
            return ticket
        
        order_type_mt5 = 0 if order_type == "buy" else 1
        
        request = {
            "action": 1,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type_mt5,
            "price": float(price),
            "sl": float(sl) if sl else 0.0,
            "tp": float(tp) if tp else 0.0,
            "deviation": 20,
            "magic": 234000,
            "comment": "OTrade",
            "type_time": 0,
            "type_filling": 1,
        }
        
        result = self.mt5.order_send(request)
        
        if result.retcode != 10009:
            return None
        
        return result.order
    
    def close_position(self, ticket: int) -> bool:
        if not self.connected:
            return False
        
        if hasattr(self, 'simulation') and self.simulation:
            for i, pos in enumerate(self._positions):
                if pos['ticket'] == ticket:
                    self._balance += pos['profit']
                    print(f"[SIM] Closed #{ticket} P/L: ${pos['profit']:.2f}")
                    self._positions.pop(i)
                    return True
            return False
        
        positions = self.mt5.positions_get(ticket=ticket)
        if not positions:
            return False
        
        pos = positions[0]
        symbol = pos.symbol
        volume = pos.volume
        
        tick = self.mt5.symbol_info_tick(symbol)
        order_type = 1 if pos.type == 0 else 0
        price = tick.bid if pos.type == 0 else tick.ask
        
        request = {
            "action": 1,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "position": ticket,
            "price": float(price),
            "deviation": 20,
            "magic": 234000,
            "comment": "OTrade",
            "type_time": 0,
            "type_filling": 1,
        }
        
        result = self.mt5.order_send(request)
        return result.retcode == 10009
    
    def close_all_positions(self, symbol: str = None) -> int:
        closed = 0
        positions = self.get_positions()
        
        for pos in positions:
            if symbol is None or pos['symbol'] == symbol:
                if self.close_position(pos['ticket']):
                    closed += 1
        
        return closed
    
    def modify_position(self, ticket: int, sl: float = None, tp: float = None) -> bool:
        if hasattr(self, 'simulation') and self.simulation:
            for pos in self._positions:
                if pos['ticket'] == ticket:
                    if sl is not None:
                        pos['sl'] = sl
                    if tp is not None:
                        pos['tp'] = tp
                    return True
            return False
        
        if not self.connected:
            return False
        
        positions = self.mt5.positions_get(ticket=ticket)
        if not positions:
            return False
        
        pos = positions[0]
        
        request = {
            "action": 3,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": float(sl) if sl else float(pos.sl),
            "tp": float(tp) if tp else float(pos.tp)
        }
        
        result = self.mt5.order_send(request)
        return result.retcode == 10009
    
    def get_positions(self) -> List[Dict[str, Any]]:
        if not self.connected:
            return []
        
        if hasattr(self, 'simulation') and self.simulation:
            self._update_simulation()
            return self._positions.copy()
        
        positions = self.mt5.positions_get()
        if not positions:
            return []
        
        return [{
            "ticket": p.ticket,
            "symbol": p.symbol,
            "type": "buy" if p.type == 0 else "sell",
            "volume": p.volume,
            "open_price": p.price_open,
            "current_price": p.price_current,
            "profit": p.profit,
            "sl": p.sl,
            "tp": p.tp,
            "time": datetime.fromtimestamp(p.time),
            "swap": p.swap,
            "commission": p.commission
        } for p in positions]


mt5 = MT5Connector()
