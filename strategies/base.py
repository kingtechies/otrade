from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import pandas as pd


class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradeSignal:
    signal: Signal
    strategy: str
    symbol: str
    confidence: float
    reason: str
    sl_pips: Optional[float] = None
    tp_pips: Optional[float] = None
    suggested_lot: Optional[float] = None


class BaseStrategy(ABC):
    name: str = "BaseStrategy"
    
    def __init__(self):
        self.weight = 1.0
    
    @abstractmethod
    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal:
        pass
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        return df
