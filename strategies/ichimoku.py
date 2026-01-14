import pandas as pd
from ta.trend import IchimokuIndicator
from .base import BaseStrategy, Signal, TradeSignal


class IchimokuStrategy(BaseStrategy):
    name = "Ichimoku"
    
    def __init__(self):
        super().__init__()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        ichimoku = IchimokuIndicator(df['high'], df['low'])
        df['tenkan'] = ichimoku.ichimoku_conversion_line()
        df['kijun'] = ichimoku.ichimoku_base_line()
        df['senkou_a'] = ichimoku.ichimoku_a()
        df['senkou_b'] = ichimoku.ichimoku_b()
        return df
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        df = self.calculate_indicators(df)
        
        if len(df) < 52 + 26:
            return TradeSignal(Signal.HOLD, self.name, symbol, 0.0, "insufficient data")
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        close = current['close']
        
        above_cloud = close > max(current['senkou_a'], current['senkou_b'])
        below_cloud = close < min(current['senkou_a'], current['senkou_b'])
        
        tk_cross_bull = previous['tenkan'] <= previous['kijun'] and current['tenkan'] > current['kijun']
        tk_cross_bear = previous['tenkan'] >= previous['kijun'] and current['tenkan'] < current['kijun']
        
        if tk_cross_bull and above_cloud:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.85,
                             "ichimoku tk cross above cloud", sl_pips=50, tp_pips=100)
        
        if tk_cross_bull:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.6,
                             "ichimoku tk cross", sl_pips=50, tp_pips=100)
        
        if tk_cross_bear and below_cloud:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.85,
                             "ichimoku tk cross below cloud", sl_pips=50, tp_pips=100)
        
        if tk_cross_bear:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.6,
                             "ichimoku tk cross", sl_pips=50, tp_pips=100)
        
        if above_cloud and current['tenkan'] > current['kijun']:
            return TradeSignal(Signal.BUY, self.name, symbol, 0.4, "ichimoku bullish trend")
        
        if below_cloud and current['tenkan'] < current['kijun']:
            return TradeSignal(Signal.SELL, self.name, symbol, 0.4, "ichimoku bearish trend")
        
        return TradeSignal(Signal.HOLD, self.name, symbol, 0.3, "ichimoku neutral")
