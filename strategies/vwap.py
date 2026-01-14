import pandas as pd
import numpy as np
from .base import BaseStrategy, Signal, TradeSignal


class VWAPStrategy(BaseStrategy):
    name = "VWAP"
    
    def __init__(self):
        super().__init__()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['tick_volume']).cumsum() / df['tick_volume'].cumsum()
        df['vwap_upper'] = df['vwap'] * 1.001
        df['vwap_lower'] = df['vwap'] * 0.999
        return df
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        df = self.calculate_indicators(df)
        
        if len(df) < 20:
            return TradeSignal(Signal.HOLD, self.name, symbol, 0.0, "insufficient data")
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        close = current['close']
        vwap = current['vwap']
        
        if previous['close'] < previous['vwap'] and close > vwap:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.7,
                             "price crossed above vwap", sl_pips=30, tp_pips=60)
        
        if previous['close'] > previous['vwap'] and close < vwap:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.7,
                             "price crossed below vwap", sl_pips=30, tp_pips=60)
        
        if close > vwap and close < current['vwap_upper']:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.4, "above vwap trend")
        
        if close < vwap and close > current['vwap_lower']:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.4, "below vwap trend")
        
        return TradeSignal(Signal.HOLD, self.name, symbol, 0.3, "at vwap level")
