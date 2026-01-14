import pandas as pd
from ta.volatility import AverageTrueRange
from .base import BaseStrategy, Signal, TradeSignal


class ATRBreakout(BaseStrategy):
    name = "ATR Breakout"
    
    def __init__(self, atr_period: int = 14, multiplier: float = 1.5):
        super().__init__()
        self.atr_period = atr_period
        self.multiplier = multiplier
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        atr = AverageTrueRange(df['high'], df['low'], df['close'], window=self.atr_period)
        df['atr'] = atr.average_true_range()
        df['upper_band'] = df['close'].shift(1) + (df['atr'] * self.multiplier)
        df['lower_band'] = df['close'].shift(1) - (df['atr'] * self.multiplier)
        return df
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        df = self.calculate_indicators(df)
        
        if len(df) < self.atr_period + 5:
            return TradeSignal(Signal.HOLD, self.name, symbol, 0.0, "insufficient data")
        
        current = df.iloc[-1]
        close = current['close']
        atr = current['atr']
        
        if close > current['upper_band']:
            sl_pips = int(atr * 100)
            tp_pips = int(atr * 200)
            return TradeSignal(Signal.BUY, self.name, symbol, 0.7,
                             f"atr breakout above band", sl_pips=sl_pips, tp_pips=tp_pips)
        
        if close < current['lower_band']:
            sl_pips = int(atr * 100)
            tp_pips = int(atr * 200)
            return TradeSignal(Signal.SELL, self.name, symbol, 0.7,
                             f"atr breakout below band", sl_pips=sl_pips, tp_pips=tp_pips)
        
        return TradeSignal(Signal.HOLD, self.name, symbol, 0.3, "within atr range")
