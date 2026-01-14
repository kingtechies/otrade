import pandas as pd
from ta.momentum import StochasticOscillator
from .base import BaseStrategy, Signal, TradeSignal


class StochasticStrategy(BaseStrategy):
    name = "Stochastic"
    
    def __init__(self, k: int = 14, d: int = 3, oversold: int = 20, overbought: int = 80):
        super().__init__()
        self.k = k
        self.d = d
        self.oversold = oversold
        self.overbought = overbought
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        stoch = StochasticOscillator(df['high'], df['low'], df['close'], 
                                     window=self.k, smooth_window=self.d)
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        return df
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        df = self.calculate_indicators(df)
        
        if len(df) < self.k + self.d + 2:
            return TradeSignal(Signal.HOLD, self.name, symbol, 0.0, "insufficient data")
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        k = current['stoch_k']
        d = current['stoch_d']
        prev_k = previous['stoch_k']
        prev_d = previous['stoch_d']
        
        if prev_k < prev_d and k > d and k < self.oversold:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.75,
                             f"stoch bullish crossover in oversold {k:.1f}", sl_pips=35, tp_pips=70)
        
        if k < self.oversold and prev_k >= self.oversold:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.6,
                             f"stoch entering oversold {k:.1f}", sl_pips=35, tp_pips=70)
        
        if prev_k > prev_d and k < d and k > self.overbought:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.75,
                             f"stoch bearish crossover in overbought {k:.1f}", sl_pips=35, tp_pips=70)
        
        if k > self.overbought and prev_k <= self.overbought:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.6,
                             f"stoch entering overbought {k:.1f}", sl_pips=35, tp_pips=70)
        
        return TradeSignal(Signal.HOLD, self.name, symbol, 0.3, f"stoch neutral {k:.1f}")
