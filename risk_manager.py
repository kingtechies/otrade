import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

from config import config


class RiskManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.TRADES_DB
        self._init_db()
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_reset = datetime.now().date()
        self.consecutive_losses = 0
        self.max_consecutive_losses = 5
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket INTEGER UNIQUE,
                symbol TEXT,
                direction TEXT,
                lot_size REAL,
                entry_price REAL,
                exit_price REAL,
                sl REAL,
                tp REAL,
                profit REAL,
                ai_reasoning TEXT,
                market_state TEXT,
                opened_at TEXT,
                closed_at TEXT,
                status TEXT,
                timeframe_alignment TEXT,
                confidence REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                balance REAL,
                equity REAL,
                profit REAL,
                margin_level REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                trades INTEGER,
                wins INTEGER,
                losses INTEGER,
                gross_profit REAL,
                gross_loss REAL,
                net_profit REAL,
                max_drawdown REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _reset_daily_if_needed(self):
        today = datetime.now().date()
        if today != self.last_reset:
            self._save_daily_summary()
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_reset = today
    
    def _save_daily_summary(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_str = self.last_reset.isoformat()
        
        cursor.execute('''
            SELECT COUNT(*), 
                   SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN profit <= 0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN profit > 0 THEN profit ELSE 0 END),
                   SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END)
            FROM trades 
            WHERE DATE(closed_at) = ?
        ''', (date_str,))
        
        row = cursor.fetchone()
        if row and row[0]:
            cursor.execute('''
                INSERT OR REPLACE INTO daily_summary
                (date, trades, wins, losses, gross_profit, gross_loss, net_profit, max_drawdown)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date_str,
                row[0] or 0,
                row[1] or 0,
                row[2] or 0,
                row[3] or 0,
                row[4] or 0,
                (row[3] or 0) + (row[4] or 0),
                0
            ))
        
        conn.commit()
        conn.close()
    
    def can_trade(self) -> tuple:
        self._reset_daily_if_needed()
        
        if self.daily_trades >= config.MAX_DAILY_TRADES:
            return False, "Daily trade limit reached"
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, "Consecutive loss limit reached"
        
        return True, ""
    
    def calculate_position_size(self, balance: float, confidence: float,
                                 sl_pips: float, symbol: str) -> float:
        
        base_risk = config.MAX_RISK_PER_TRADE
        
        adjusted_risk = base_risk * confidence
        
        if self.consecutive_losses >= 3:
            adjusted_risk *= 0.5
        
        if self.daily_pnl < 0:
            adjusted_risk *= 0.75
        
        risk_amount = balance * adjusted_risk
        
        if symbol == "XAUUSD":
            pip_value = 1.0
        elif "USTECH" in symbol:
            pip_value = 1.0
        else:
            pip_value = 10.0
        
        if sl_pips <= 0:
            sl_pips = 50
        
        lot_size = risk_amount / (sl_pips * pip_value)
        lot_size = max(0.01, min(10.0, lot_size))
        
        return round(lot_size, 2)
    
    def log_trade_open(self, ticket: int, symbol: str, direction: str,
                       lot_size: float, entry_price: float, sl: float,
                       tp: float, ai_decision: Dict[str, Any], market_state: Dict[str, Any]):
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trades 
            (ticket, symbol, direction, lot_size, entry_price, sl, tp,
             ai_reasoning, market_state, opened_at, status, 
             timeframe_alignment, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticket,
            symbol,
            direction,
            lot_size,
            entry_price,
            sl,
            tp,
            ai_decision.get('entry_reason', ''),
            json.dumps(market_state),
            datetime.now().isoformat(),
            'open',
            ai_decision.get('timeframe_alignment', ''),
            ai_decision.get('confidence', 0)
        ))
        
        conn.commit()
        conn.close()
        
        self.daily_trades += 1
    
    def log_trade_close(self, ticket: int, exit_price: float, profit: float):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trades SET 
                exit_price = ?,
                profit = ?,
                closed_at = ?,
                status = ?
            WHERE ticket = ?
        ''', (exit_price, profit, datetime.now().isoformat(), 'closed', ticket))
        
        conn.commit()
        conn.close()
        
        self.daily_pnl += profit
        
        if profit > 0:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
    
    def log_account_snapshot(self, balance: float, equity: float, 
                             profit: float, margin_level: float):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO account_history (timestamp, balance, equity, profit, margin_level)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), balance, equity, profit, margin_level))
        
        conn.commit()
        conn.close()
    
    def get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins,
                SUM(profit) as total_profit,
                AVG(CASE WHEN profit > 0 THEN profit END) as avg_win,
                AVG(CASE WHEN profit < 0 THEN profit END) as avg_loss,
                MAX(profit) as best_trade,
                MIN(profit) as worst_trade
            FROM trades
            WHERE closed_at >= ? AND status = 'closed'
        ''', (since,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "total_profit": 0,
                "profit_factor": 0,
                "avg_win": 0,
                "avg_loss": 0
            }
        
        total = row[0]
        wins = row[1] or 0
        total_profit = row[2] or 0
        avg_win = row[3] or 0
        avg_loss = row[4] or 0
        
        win_rate = wins / total if total > 0 else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss else 0
        
        return {
            "total_trades": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "best_trade": row[5] or 0,
            "worst_trade": row[6] or 0
        }
    
    def get_open_trades(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ticket, symbol, direction, lot_size, entry_price, sl, tp, opened_at
            FROM trades WHERE status = 'open'
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "ticket": r[0],
            "symbol": r[1],
            "direction": r[2],
            "lot_size": r[3],
            "entry_price": r[4],
            "sl": r[5],
            "tp": r[6],
            "opened_at": r[7]
        } for r in rows]


risk_manager = RiskManager()
