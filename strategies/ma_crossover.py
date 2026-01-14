import pandas as pd
from ta.trend import SMAIndicator
from .base import BaseStrategy, Signal, TradeSignal


class MACrossover(BaseStrategy):
    name = "MA Crossover"
    
    def __init__(self, fast: int = 10, slow: int = 20):
        super().__init__()
        self.fast = fast
        self.slow = slow
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['ma_fast'] = SMAIndicator(df['close'], window=self.fast).sma_indicator()
        df['ma_slow'] = SMAIndicator(df['close'], window=self.slow).sma_indicator()
        return df
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        df = self.calculate_indicators(df)
        
        if len(df) < self.slow + 2:
            return TradeSignal(Signal.HOLD, self.name, symbol, 0.0, "insufficient data")
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        if previous['ma_fast'] <= previous['ma_slow'] and current['ma_fast'] > current['ma_slow']:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.7, 
                             f"bullish crossover", sl_pips=50, tp_pips=100)
        
        if previous['ma_fast'] >= previous['ma_slow'] and current['ma_fast'] < current['ma_slow']:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.7,
                             f"bearish crossover", sl_pips=50, tp_pips=100)
        
        return TradeSignal(Signal.HOLD, self.name, symbol, 0.3, "no crossover")
