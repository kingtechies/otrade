import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from ta.trend import SMAIndicator, EMAIndicator, MACD, IchimokuIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

from config import config


@dataclass
class TimeframeAnalysis:
    timeframe: str
    trend: str
    strength: float
    momentum: str
    volatility: str
    key_levels: Dict[str, float]
    signals: List[str]


@dataclass
class MarketRegime:
    regime: str
    confidence: float
    description: str


class MultiTimeframeAnalyzer:
    def __init__(self):
        self.timeframe_weights = {
            "MN1": 0.15,
            "W1": 0.15,
            "D1": 0.20,
            "H4": 0.15,
            "H1": 0.15,
            "M30": 0.08,
            "M15": 0.07,
            "M5": 0.03,
            "M1": 0.02
        }
    
    def analyze_all_timeframes(self, data: Dict[str, pd.DataFrame], symbol: str) -> Dict[str, TimeframeAnalysis]:
        results = {}
        
        for tf, df in data.items():
            if df.empty or len(df) < 50:
                continue
            
            analysis = self._analyze_single_timeframe(df, tf)
            results[tf] = analysis
        
        return results
    
    def _analyze_single_timeframe(self, df: pd.DataFrame, timeframe: str) -> TimeframeAnalysis:
        df = df.copy()
        
        df['sma_20'] = SMAIndicator(df['close'], window=20).sma_indicator()
        df['sma_50'] = SMAIndicator(df['close'], window=50).sma_indicator()
        df['sma_200'] = SMAIndicator(df['close'], window=min(200, len(df)-1)).sma_indicator()
        df['ema_12'] = EMAIndicator(df['close'], window=12).ema_indicator()
        df['ema_26'] = EMAIndicator(df['close'], window=26).ema_indicator()
        
        macd = MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_hist'] = macd.macd_diff()
        
        df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
        
        stoch = StochasticOscillator(df['high'], df['low'], df['close'])
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        bb = BollingerBands(df['close'])
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mavg()
        
        atr = AverageTrueRange(df['high'], df['low'], df['close'])
        df['atr'] = atr.average_true_range()
        
        current = df.iloc[-1]
        close = current['close']
        
        trend = self._determine_trend(current, df)
        strength = self._calculate_trend_strength(current, df)
        momentum = self._determine_momentum(current)
        volatility = self._determine_volatility(current, df)
        
        key_levels = {
            "resistance": df['high'].rolling(50).max().iloc[-1],
            "support": df['low'].rolling(50).min().iloc[-1],
            "pivot": (df['high'].iloc[-1] + df['low'].iloc[-1] + df['close'].iloc[-1]) / 3,
            "bb_upper": current['bb_upper'],
            "bb_lower": current['bb_lower'],
            "sma_200": current['sma_200'] if not pd.isna(current['sma_200']) else close
        }
        
        signals = self._generate_signals(current, df)
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            trend=trend,
            strength=strength,
            momentum=momentum,
            volatility=volatility,
            key_levels=key_levels,
            signals=signals
        )
    
    def _determine_trend(self, current: pd.Series, df: pd.DataFrame) -> str:
        close = current['close']
        sma_20 = current['sma_20']
        sma_50 = current['sma_50']
        sma_200 = current['sma_200'] if not pd.isna(current['sma_200']) else sma_50
        
        above_20 = close > sma_20
        above_50 = close > sma_50
        above_200 = close > sma_200
        ma_aligned_bull = sma_20 > sma_50 > sma_200 if not pd.isna(sma_200) else sma_20 > sma_50
        ma_aligned_bear = sma_20 < sma_50 < sma_200 if not pd.isna(sma_200) else sma_20 < sma_50
        
        if ma_aligned_bull and above_20 and above_50:
            return "strong_bullish"
        elif above_20 and above_50:
            return "bullish"
        elif ma_aligned_bear and not above_20 and not above_50:
            return "strong_bearish"
        elif not above_20 and not above_50:
            return "bearish"
        else:
            return "neutral"
    
    def _calculate_trend_strength(self, current: pd.Series, df: pd.DataFrame) -> float:
        rsi = current['rsi']
        macd_hist = current['macd_hist']
        
        rsi_strength = abs(rsi - 50) / 50
        
        macd_max = df['macd_hist'].abs().max()
        macd_strength = abs(macd_hist) / macd_max if macd_max > 0 else 0
        
        return min(1.0, (rsi_strength + macd_strength) / 2)
    
    def _determine_momentum(self, current: pd.Series) -> str:
        rsi = current['rsi']
        macd_hist = current['macd_hist']
        stoch_k = current['stoch_k']
        
        if rsi > 70 and stoch_k > 80:
            return "extremely_overbought"
        elif rsi > 60 and macd_hist > 0:
            return "bullish_momentum"
        elif rsi < 30 and stoch_k < 20:
            return "extremely_oversold"
        elif rsi < 40 and macd_hist < 0:
            return "bearish_momentum"
        else:
            return "neutral"
    
    def _determine_volatility(self, current: pd.Series, df: pd.DataFrame) -> str:
        atr = current['atr']
        avg_atr = df['atr'].rolling(20).mean().iloc[-1]
        bb_width = (current['bb_upper'] - current['bb_lower']) / current['bb_middle']
        
        if atr > avg_atr * 1.5 or bb_width > 0.05:
            return "high"
        elif atr < avg_atr * 0.5 or bb_width < 0.02:
            return "low"
        else:
            return "normal"
    
    def _generate_signals(self, current: pd.Series, df: pd.DataFrame) -> List[str]:
        signals = []
        previous = df.iloc[-2]
        
        if previous['macd'] < previous['macd_signal'] and current['macd'] > current['macd_signal']:
            signals.append("macd_bullish_cross")
        if previous['macd'] > previous['macd_signal'] and current['macd'] < current['macd_signal']:
            signals.append("macd_bearish_cross")
        
        if previous['rsi'] < 30 and current['rsi'] >= 30:
            signals.append("rsi_oversold_exit")
        if previous['rsi'] > 70 and current['rsi'] <= 70:
            signals.append("rsi_overbought_exit")
        
        if previous['stoch_k'] < previous['stoch_d'] and current['stoch_k'] > current['stoch_d']:
            signals.append("stoch_bullish_cross")
        if previous['stoch_k'] > previous['stoch_d'] and current['stoch_k'] < current['stoch_d']:
            signals.append("stoch_bearish_cross")
        
        if previous['close'] < previous['bb_lower'] and current['close'] > current['bb_lower']:
            signals.append("bb_lower_bounce")
        if previous['close'] > previous['bb_upper'] and current['close'] < current['bb_upper']:
            signals.append("bb_upper_bounce")
        
        return signals
    
    def get_market_regime(self, analyses: Dict[str, TimeframeAnalysis]) -> MarketRegime:
        if not analyses:
            return MarketRegime("unknown", 0.0, "No data available")
        
        bullish_score = 0.0
        bearish_score = 0.0
        total_weight = 0.0
        
        for tf, analysis in analyses.items():
            weight = self.timeframe_weights.get(tf, 0.05)
            total_weight += weight
            
            if "bullish" in analysis.trend:
                bullish_score += weight * analysis.strength
            elif "bearish" in analysis.trend:
                bearish_score += weight * analysis.strength
        
        if total_weight == 0:
            return MarketRegime("unknown", 0.0, "No analysis data")
        
        bullish_score /= total_weight
        bearish_score /= total_weight
        
        volatility_high = sum(1 for a in analyses.values() if a.volatility == "high")
        volatility_low = sum(1 for a in analyses.values() if a.volatility == "low")
        
        if bullish_score > bearish_score * 1.5 and bullish_score > 0.3:
            regime = "trending_bullish"
            confidence = min(1.0, bullish_score)
            desc = "Strong uptrend across multiple timeframes"
        elif bearish_score > bullish_score * 1.5 and bearish_score > 0.3:
            regime = "trending_bearish"
            confidence = min(1.0, bearish_score)
            desc = "Strong downtrend across multiple timeframes"
        elif volatility_high > len(analyses) / 2:
            regime = "volatile"
            confidence = 0.6
            desc = "High volatility environment"
        elif volatility_low > len(analyses) / 2:
            regime = "consolidating"
            confidence = 0.6
            desc = "Low volatility, consolidation phase"
        else:
            regime = "ranging"
            confidence = 0.5
            desc = "Mixed signals, range-bound market"
        
        return MarketRegime(regime, confidence, desc)
    
    def get_best_entry_timeframe(self, analyses: Dict[str, TimeframeAnalysis], 
                                  direction: str) -> Tuple[str, float]:
        best_tf = None
        best_score = -1
        
        for tf, analysis in analyses.items():
            if tf in ["M1", "M5"]:
                continue
            
            score = 0.0
            
            if direction == "buy":
                if "bullish" in analysis.trend:
                    score += 0.3
                if analysis.momentum in ["bullish_momentum", "extremely_oversold"]:
                    score += 0.2
                if "macd_bullish_cross" in analysis.signals or "stoch_bullish_cross" in analysis.signals:
                    score += 0.3
                if "bb_lower_bounce" in analysis.signals:
                    score += 0.2
            else:
                if "bearish" in analysis.trend:
                    score += 0.3
                if analysis.momentum in ["bearish_momentum", "extremely_overbought"]:
                    score += 0.2
                if "macd_bearish_cross" in analysis.signals or "stoch_bearish_cross" in analysis.signals:
                    score += 0.3
                if "bb_upper_bounce" in analysis.signals:
                    score += 0.2
            
            score *= analysis.strength
            
            if score > best_score:
                best_score = score
                best_tf = tf
        
        return best_tf or config.PRIMARY_TIMEFRAME, best_score


mtf_analyzer = MultiTimeframeAnalyzer()
