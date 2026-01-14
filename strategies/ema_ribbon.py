import pandas as pd
from ta.trend import EMAIndicator
from .base import BaseStrategy, Signal, TradeSignal


class EMARibbon(BaseStrategy):
    name = "EMA Ribbon"
    
    def __init__(self):
        super().__init__()
        self.periods = [8, 13, 21, 34, 55]
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for p in self.periods:
            df[f'ema_{p}'] = EMAIndicator(df['close'], window=p).ema_indicator()
        return df
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        df = self.calculate_indicators(df)
        
        if len(df) < max(self.periods) + 2:
            return TradeSignal(Signal.HOLD, self.name, symbol, 0.0, "insufficient data")
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        ema_values = [current[f'ema_{p}'] for p in self.periods]
        prev_ema_values = [previous[f'ema_{p}'] for p in self.periods]
        
        bullish = all(ema_values[i] > ema_values[i+1] for i in range(len(ema_values)-1))
        bearish = all(ema_values[i] < ema_values[i+1] for i in range(len(ema_values)-1))
        
        prev_bullish = all(prev_ema_values[i] > prev_ema_values[i+1] for i in range(len(prev_ema_values)-1))
        prev_bearish = all(prev_ema_values[i] < prev_ema_values[i+1] for i in range(len(prev_ema_values)-1))
        
        if bullish and not prev_bullish:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.8,
                             "ema ribbon aligned bullish", sl_pips=40, tp_pips=80)
        
        if bearish and not prev_bearish:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.8,
                             "ema ribbon aligned bearish", sl_pips=40, tp_pips=80)
        
        if bullish:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.5, "ema ribbon bullish trend")
        
        if bearish:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.5, "ema ribbon bearish trend")
        
        return TradeSignal(Signal.HOLD, self.name, symbol, 0.3, "ema ribbon mixed")
