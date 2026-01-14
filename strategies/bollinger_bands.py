import pandas as pd
from ta.volatility import BollingerBands as BB
from .base import BaseStrategy, Signal, TradeSignal


class BollingerBands(BaseStrategy):
    name = "Bollinger Bands"
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__()
        self.period = period
        self.std_dev = std_dev
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        bb = BB(df['close'], window=self.period, window_dev=self.std_dev)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        return df
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        df = self.calculate_indicators(df)
        
        if len(df) < self.period + 2:
            return TradeSignal(Signal.HOLD, self.name, symbol, 0.0, "insufficient data")
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        close = current['close']
        
        if previous['close'] <= previous['bb_lower'] and close > current['bb_lower']:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.7,
                             "bounce off lower band", sl_pips=30, tp_pips=60)
        
        if close <= current['bb_lower']:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.6,
                             "at lower band", sl_pips=30, tp_pips=60)
        
        if previous['close'] >= previous['bb_upper'] and close < current['bb_upper']:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.7,
                             "bounce off upper band", sl_pips=30, tp_pips=60)
        
        if close >= current['bb_upper']:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.6,
                             "at upper band", sl_pips=30, tp_pips=60)
        
        return TradeSignal(Signal.HOLD, self.name, symbol, 0.3, "in middle zone")
