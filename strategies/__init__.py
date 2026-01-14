from .base import BaseStrategy, Signal, TradeSignal
from .ma_crossover import MACrossover
from .rsi_reversal import RSIReversal
from .bollinger_bands import BollingerBands
from .macd_momentum import MACDMomentum
from .sr_breakout import SRBreakout
from .ema_ribbon import EMARibbon
from .stochastic import StochasticStrategy
from .atr_breakout import ATRBreakout
from .ichimoku import IchimokuStrategy
from .vwap import VWAPStrategy

ALL_STRATEGIES = [
    MACrossover,
    RSIReversal,
    BollingerBands,
    MACDMomentum,
    SRBreakout,
    EMARibbon,
    StochasticStrategy,
    ATRBreakout,
    IchimokuStrategy,
    VWAPStrategy
]

__all__ = [
    "BaseStrategy",
    "Signal",
    "TradeSignal",
    "ALL_STRATEGIES",
    "MACrossover",
    "RSIReversal",
    "BollingerBands",
    "MACDMomentum",
    "SRBreakout",
    "EMARibbon",
    "StochasticStrategy",
    "ATRBreakout",
    "IchimokuStrategy",
    "VWAPStrategy"
]
