import sqlite3
import json
import numpy as np
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
import pickle

from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from scipy.stats import pearsonr

from config import config


@dataclass
class TradeMemory:
    timestamp: datetime
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    profit: float
    market_state: Dict[str, Any]
    strategy_signals: Dict[str, str]
    ai_reasoning: str
    outcome: str


@dataclass
class MarketPattern:
    pattern_id: str
    pattern_type: str
    conditions: Dict[str, Any]
    success_rate: float
    avg_profit: float
    occurrences: int
    last_seen: datetime


@dataclass
class LearningInsight:
    insight_type: str
    description: str
    confidence: float
    data: Dict[str, Any]


class NeuralTradingBrain:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.BRAIN_DB
        self._init_database()
        
        self.short_term_memory = deque(maxlen=100)
        self.working_memory = {}
        self.pattern_cache = {}
        
        self.scaler = StandardScaler()
        self.pattern_classifier = None
        self.outcome_predictor = None
        
        self.strategy_weights = {}
        self.symbol_biases = {}
        self.timeframe_preferences = {}
        
        self._load_learned_state()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                direction TEXT,
                entry_price REAL,
                exit_price REAL,
                profit REAL,
                market_state TEXT,
                strategy_signals TEXT,
                ai_reasoning TEXT,
                outcome TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT,
                conditions TEXT,
                success_rate REAL,
                avg_profit REAL,
                occurrences INTEGER,
                last_seen TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_type TEXT,
                description TEXT,
                confidence REAL,
                data TEXT,
                created_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS brain_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                symbol TEXT,
                trades INTEGER,
                wins INTEGER,
                losses INTEGER,
                total_profit REAL,
                avg_win REAL,
                avg_loss REAL,
                max_drawdown REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_learned_state(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM brain_state")
        rows = cursor.fetchall()
        
        for key, value in rows:
            try:
                data = json.loads(value)
                if key == "strategy_weights":
                    self.strategy_weights = data
                elif key == "symbol_biases":
                    self.symbol_biases = data
                elif key == "timeframe_preferences":
                    self.timeframe_preferences = data
            except:
                pass
        
        cursor.execute('''
            SELECT * FROM trade_memories 
            ORDER BY timestamp DESC LIMIT 1000
        ''')
        rows = cursor.fetchall()
        
        conn.close()
        
        if len(rows) >= 50:
            self._train_models(rows)
    
    def _save_state(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        states = [
            ("strategy_weights", json.dumps(self.strategy_weights)),
            ("symbol_biases", json.dumps(self.symbol_biases)),
            ("timeframe_preferences", json.dumps(self.timeframe_preferences))
        ]
        
        for key, value in states:
            cursor.execute('''
                INSERT OR REPLACE INTO brain_state (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, now))
        
        conn.commit()
        conn.close()
    
    def remember_trade(self, memory: TradeMemory):
        self.short_term_memory.append(memory)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trade_memories 
            (timestamp, symbol, direction, entry_price, exit_price, profit,
             market_state, strategy_signals, ai_reasoning, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            memory.timestamp.isoformat(),
            memory.symbol,
            memory.direction,
            memory.entry_price,
            memory.exit_price,
            memory.profit,
            json.dumps(memory.market_state),
            json.dumps(memory.strategy_signals),
            memory.ai_reasoning,
            memory.outcome
        ))
        
        conn.commit()
        conn.close()
        
        self._update_learning(memory)
    
    def _update_learning(self, memory: TradeMemory):
        for strategy, signal in memory.strategy_signals.items():
            if strategy not in self.strategy_weights:
                self.strategy_weights[strategy] = 1.0
            
            if memory.outcome == "win":
                if signal == memory.direction:
                    self.strategy_weights[strategy] *= (1 + config.LEARNING_RATE)
                else:
                    self.strategy_weights[strategy] *= (1 - config.LEARNING_RATE * 0.5)
            else:
                if signal == memory.direction:
                    self.strategy_weights[strategy] *= (1 - config.LEARNING_RATE)
                else:
                    self.strategy_weights[strategy] *= (1 + config.LEARNING_RATE * 0.5)
            
            self.strategy_weights[strategy] = max(0.1, min(3.0, self.strategy_weights[strategy]))
        
        symbol = memory.symbol
        if symbol not in self.symbol_biases:
            self.symbol_biases[symbol] = {"win_rate": 0.5, "avg_profit": 0, "trades": 0}
        
        bias = self.symbol_biases[symbol]
        bias["trades"] += 1
        old_avg = bias["avg_profit"]
        bias["avg_profit"] = old_avg + (memory.profit - old_avg) / bias["trades"]
        
        if memory.outcome == "win":
            old_wr = bias["win_rate"]
            bias["win_rate"] = old_wr + (1 - old_wr) * 0.1
        else:
            old_wr = bias["win_rate"]
            bias["win_rate"] = old_wr * 0.9
        
        self._detect_patterns(memory)
        self._save_state()
    
    def _detect_patterns(self, memory: TradeMemory):
        market_state = memory.market_state
        
        pattern_key = self._generate_pattern_key(market_state)
        
        if pattern_key not in self.pattern_cache:
            self.pattern_cache[pattern_key] = {
                "wins": 0,
                "losses": 0,
                "total_profit": 0,
                "occurrences": 0,
                "last_seen": datetime.now()
            }
        
        pattern = self.pattern_cache[pattern_key]
        pattern["occurrences"] += 1
        pattern["total_profit"] += memory.profit
        pattern["last_seen"] = datetime.now()
        
        if memory.outcome == "win":
            pattern["wins"] += 1
        else:
            pattern["losses"] += 1
        
        if pattern["occurrences"] >= 5:
            success_rate = pattern["wins"] / pattern["occurrences"]
            avg_profit = pattern["total_profit"] / pattern["occurrences"]
            
            if success_rate >= 0.6 or avg_profit > 0:
                self._save_pattern(pattern_key, market_state, success_rate, avg_profit, pattern)
    
    def _generate_pattern_key(self, market_state: Dict[str, Any]) -> str:
        key_elements = []
        
        regime = market_state.get("regime", "unknown")
        key_elements.append(regime)
        
        for tf in ["D1", "H4", "H1"]:
            if tf in market_state.get("trends", {}):
                key_elements.append(f"{tf}:{market_state['trends'][tf]}")
        
        momentum = market_state.get("momentum", "neutral")
        key_elements.append(momentum)
        
        volatility = market_state.get("volatility", "normal")
        key_elements.append(volatility)
        
        pattern_str = "|".join(key_elements)
        return hashlib.md5(pattern_str.encode()).hexdigest()[:12]
    
    def _save_pattern(self, pattern_id: str, conditions: Dict[str, Any],
                      success_rate: float, avg_profit: float, stats: Dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO market_patterns
            (pattern_id, pattern_type, conditions, success_rate, avg_profit, occurrences, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern_id,
            "composite",
            json.dumps(conditions),
            success_rate,
            avg_profit,
            stats["occurrences"],
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _train_models(self, trade_data: List):
        if len(trade_data) < 50:
            return
        
        X = []
        y = []
        
        for row in trade_data:
            try:
                market_state = json.loads(row[7])
                features = self._extract_features(market_state)
                outcome = 1 if row[10] == "win" else 0
                
                X.append(features)
                y.append(outcome)
            except:
                continue
        
        if len(X) < 30:
            return
        
        X = np.array(X)
        y = np.array(y)
        
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        
        self.outcome_predictor = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1
        )
        self.outcome_predictor.fit(X_scaled, y)
    
    def _extract_features(self, market_state: Dict[str, Any]) -> List[float]:
        features = []
        
        regime_map = {
            "trending_bullish": 1.0,
            "bullish": 0.5,
            "neutral": 0.0,
            "bearish": -0.5,
            "trending_bearish": -1.0,
            "volatile": 0.0,
            "consolidating": 0.0,
            "ranging": 0.0
        }
        regime = market_state.get("regime", "neutral")
        features.append(regime_map.get(regime, 0.0))
        
        trend_map = {"strong_bullish": 1.0, "bullish": 0.5, "neutral": 0.0, 
                     "bearish": -0.5, "strong_bearish": -1.0}
        for tf in ["D1", "H4", "H1", "M15"]:
            trend = market_state.get("trends", {}).get(tf, "neutral")
            features.append(trend_map.get(trend, 0.0))
        
        momentum_map = {
            "extremely_overbought": 1.0,
            "bullish_momentum": 0.5,
            "neutral": 0.0,
            "bearish_momentum": -0.5,
            "extremely_oversold": -1.0
        }
        momentum = market_state.get("momentum", "neutral")
        features.append(momentum_map.get(momentum, 0.0))
        
        volatility_map = {"high": 1.0, "normal": 0.5, "low": 0.0}
        volatility = market_state.get("volatility", "normal")
        features.append(volatility_map.get(volatility, 0.5))
        
        features.append(market_state.get("regime_confidence", 0.5))
        
        return features
    
    def predict_trade_outcome(self, market_state: Dict[str, Any], 
                               direction: str) -> Tuple[float, float]:
        if self.outcome_predictor is None:
            return 0.5, 0.5
        
        features = self._extract_features(market_state)
        
        direction_factor = 1.0 if direction == "buy" else -1.0
        features[0] *= direction_factor
        
        X = np.array([features])
        X_scaled = self.scaler.transform(X)
        
        proba = self.outcome_predictor.predict_proba(X_scaled)[0]
        
        return proba[1], 1 - proba[1]
    
    def get_strategy_weight(self, strategy_name: str) -> float:
        return self.strategy_weights.get(strategy_name, 1.0)
    
    def get_symbol_bias(self, symbol: str) -> Dict[str, Any]:
        return self.symbol_biases.get(symbol, {"win_rate": 0.5, "avg_profit": 0, "trades": 0})
    
    def get_best_patterns(self, current_state: Dict[str, Any], limit: int = 5) -> List[MarketPattern]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM market_patterns
            WHERE success_rate >= 0.55
            ORDER BY (success_rate * avg_profit * occurrences) DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        patterns = []
        for row in rows:
            patterns.append(MarketPattern(
                pattern_id=row[0],
                pattern_type=row[1],
                conditions=json.loads(row[2]),
                success_rate=row[3],
                avg_profit=row[4],
                occurrences=row[5],
                last_seen=datetime.fromisoformat(row[6])
            ))
        
        return patterns
    
    def get_learning_summary(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM trade_memories")
        total_trades = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM trade_memories WHERE outcome = 'win'")
        total_wins = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM market_patterns")
        patterns_learned = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(success_rate) FROM market_patterns WHERE occurrences >= 5")
        avg_pattern_success = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_trades_learned": total_trades,
            "win_rate": total_wins / total_trades if total_trades > 0 else 0,
            "patterns_discovered": patterns_learned,
            "avg_pattern_success": avg_pattern_success,
            "strategies_analyzed": len(self.strategy_weights),
            "symbols_traded": len(self.symbol_biases),
            "model_trained": self.outcome_predictor is not None
        }
    
    def generate_market_insight(self, market_state: Dict[str, Any], 
                                 symbol: str) -> LearningInsight:
        pattern_key = self._generate_pattern_key(market_state)
        
        if pattern_key in self.pattern_cache:
            pattern = self.pattern_cache[pattern_key]
            if pattern["occurrences"] >= 3:
                success_rate = pattern["wins"] / pattern["occurrences"]
                return LearningInsight(
                    insight_type="pattern_match",
                    description=f"Similar market conditions seen {pattern['occurrences']} times with {success_rate:.0%} success",
                    confidence=min(0.9, success_rate),
                    data={
                        "pattern_id": pattern_key,
                        "success_rate": success_rate,
                        "avg_profit": pattern["total_profit"] / pattern["occurrences"]
                    }
                )
        
        bias = self.get_symbol_bias(symbol)
        if bias["trades"] >= 10:
            return LearningInsight(
                insight_type="symbol_analysis",
                description=f"Historical win rate on {symbol}: {bias['win_rate']:.0%} over {bias['trades']} trades",
                confidence=min(0.8, 0.5 + bias["trades"] / 100),
                data=bias
            )
        
        return LearningInsight(
            insight_type="learning",
            description="Gathering data to form patterns",
            confidence=0.3,
            data={}
        )


neural_brain = NeuralTradingBrain()
