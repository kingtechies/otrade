import pandas as pd
import numpy as np
from .base import BaseStrategy, Signal, TradeSignal


class SRBreakout(BaseStrategy):
    name = "S/R Breakout"
    
    def __init__(self, lookback: int = 50):
        super().__init__()
        self.lookback = lookback
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['resistance'] = df['high'].rolling(window=self.lookback).max()
        df['support'] = df['low'].rolling(window=self.lookback).min()
        return df
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        df = self.calculate_indicators(df)
        
        if len(df) < self.lookback + 5:
            return TradeSignal(Signal.HOLD, self.name, symbol, 0.0, "insufficient data")
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        close = current['close']
        
        prev_resistance = df['high'].iloc[-self.lookback:-1].max()
        prev_support = df['low'].iloc[-self.lookback:-1].min()
        
        if close > prev_resistance and previous['close'] <= prev_resistance:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.75,
                             f"resistance breakout at {prev_resistance:.2f}", sl_pips=60, tp_pips=120)
        
        if close < prev_support and previous['close'] >= prev_support:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.75,
                             f"support breakdown at {prev_support:.2f}", sl_pips=60, tp_pips=120)
        
        return TradeSignal(Signal.HOLD, self.name, symbol, 0.3, "in range")
