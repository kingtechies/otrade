import pandas as pd
from ta.trend import MACD
from .base import BaseStrategy, Signal, TradeSignal


class MACDMomentum(BaseStrategy):
    name = "MACD Momentum"
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__()
        self.fast = fast
        self.slow = slow
        self.signal_period = signal
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        macd = MACD(df['close'], window_fast=self.fast, window_slow=self.slow, 
                    window_sign=self.signal_period)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_hist'] = macd.macd_diff()
        return df
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        df = self.calculate_indicators(df)
        
        if len(df) < self.slow + self.signal_period + 2:
            return TradeSignal(Signal.HOLD, self.name, symbol, 0.0, "insufficient data")
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        if previous['macd'] <= previous['macd_signal'] and current['macd'] > current['macd_signal']:
            conf = 0.75 if current['macd'] < 0 else 0.65
            return TradeSignal(Signal.BUY, self.name, symbol, conf,
                             "bullish macd crossover", sl_pips=50, tp_pips=100)
        
        if previous['macd'] >= previous['macd_signal'] and current['macd'] < current['macd_signal']:
            conf = 0.75 if current['macd'] > 0 else 0.65
            return TradeSignal(Signal.SELL, self.name, symbol, conf,
                             "bearish macd crossover", sl_pips=50, tp_pips=100)
        
        if current['macd_hist'] > 0 and current['macd_hist'] > previous['macd_hist']:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.4, "macd histogram rising")
        
        if current['macd_hist'] < 0 and current['macd_hist'] < previous['macd_hist']:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.4, "macd histogram falling")
        
        return TradeSignal(Signal.HOLD, self.name, symbol, 0.3, "no macd signal")
