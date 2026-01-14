import pandas as pd
from ta.momentum import RSIIndicator
from .base import BaseStrategy, Signal, TradeSignal


class RSIReversal(BaseStrategy):
    name = "RSI Reversal"
    
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__()
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['rsi'] = RSIIndicator(df['close'], window=self.period).rsi()
        return df
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        df = self.calculate_indicators(df)
        
        if len(df) < self.period + 2:
            return TradeSignal(Signal.HOLD, self.name, symbol, 0.0, "insufficient data")
        
        current_rsi = df['rsi'].iloc[-1]
        previous_rsi = df['rsi'].iloc[-2]
        
        if previous_rsi < self.oversold and current_rsi >= self.oversold:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.75,
                             f"rsi reversal from {current_rsi:.1f}", sl_pips=40, tp_pips=80)
        
        if current_rsi < self.oversold:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.6,
                             f"rsi oversold {current_rsi:.1f}", sl_pips=40, tp_pips=80)
        
        if previous_rsi > self.overbought and current_rsi <= self.overbought:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.75,
                             f"rsi reversal from {current_rsi:.1f}", sl_pips=40, tp_pips=80)
        
        if current_rsi > self.overbought:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.6,
                             f"rsi overbought {current_rsi:.1f}", sl_pips=40, tp_pips=80)
        
        return TradeSignal(Signal.HOLD, self.name, symbol, 0.3, f"rsi neutral {current_rsi:.1f}")
