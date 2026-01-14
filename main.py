import time
import signal
import sys
import traceback
from datetime import datetime
from typing import List, Dict, Any

from config import config
from mt5_connector import mt5
from ai_brain import ai_brain
from risk_manager import risk_manager
from mtf_analyzer import mtf_analyzer
from neural_brain import neural_brain, TradeMemory
from strategies import ALL_STRATEGIES


class TradingBot:
    def __init__(self):
        self.running = False
        self.strategies = [s() for s in ALL_STRATEGIES]
        self.loop_interval = 10
        self.last_analysis = {}
        
    def start(self):
        config.validate()
        
        if not mt5.connect():
            raise ConnectionError("Failed to connect to MT5")
        
        self.running = True
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        self._log("=" * 60)
        self._log("OTRADE ULTRA ADVANCED TRADING BOT")
        self._log("=" * 60)
        self._log(f"Target: ${config.PRIMARY_TARGET:,.2f}")
        self._log(f"Symbols: {', '.join(config.SYMBOLS)}")
        self._log(f"Strategies: {len(self.strategies)}")
        self._log(f"Timeframes: {', '.join(config.TIMEFRAMES)}")
        self._log("=" * 60)
        
        learning_summary = neural_brain.get_learning_summary()
        self._log(f"Brain Status:")
        self._log(f"  Trades Learned: {learning_summary['total_trades_learned']}")
        self._log(f"  Patterns Found: {learning_summary['patterns_discovered']}")
        self._log(f"  Model Trained: {learning_summary['model_trained']}")
        self._log("=" * 60)
        
        self._run_loop()
    
    def _run_loop(self):
        while self.running:
            try:
                cycle_start = datetime.now()
                
                self._trading_cycle()
                
                cycle_time = (datetime.now() - cycle_start).seconds
                sleep_time = max(1, self.loop_interval - cycle_time)
                
                time.sleep(sleep_time)
                
            except Exception as e:
                self._log(f"Error: {e}")
                traceback.print_exc()
                time.sleep(5)
    
    def _trading_cycle(self):
        account = mt5.get_account_info()
        if not account:
            self._log("Failed to get account info")
            return
        
        balance = account['balance']
        equity = account['equity']
        margin_level = (equity / account['margin'] * 100) if account['margin'] > 0 else 0
        
        risk_manager.log_account_snapshot(balance, equity, account['profit'], margin_level)
        
        positions = mt5.get_positions()
        
        if balance >= config.PRIMARY_TARGET:
            self._log(f"TARGET REACHED: ${balance:,.2f}")
            if not config.CONTINUE_AFTER_TARGET:
                self.running = False
                return
        
        self._manage_positions(positions)
        
        for symbol in config.SYMBOLS:
            self._analyze_and_trade(symbol, account, positions)
    
    def _analyze_and_trade(self, symbol: str, account: Dict[str, Any], 
                           positions: List[Dict[str, Any]]):
        
        symbol_positions = [p for p in positions if p['symbol'] == symbol]
        if len(symbol_positions) >= 2:
            return
        
        if len(positions) >= config.MAX_OPEN_POSITIONS:
            return
        
        can_trade, reason = risk_manager.can_trade()
        if not can_trade:
            self._log(f"Cannot trade: {reason}")
            return
        
        all_tf_data = mt5.get_all_timeframes(symbol)
        if not all_tf_data:
            return
        
        mtf_analysis = mtf_analyzer.analyze_all_timeframes(all_tf_data, symbol)
        market_regime = mtf_analyzer.get_market_regime(mtf_analysis)
        
        primary_df = all_tf_data.get(config.PRIMARY_TIMEFRAME)
        strategy_signals = []
        
        if primary_df is not None and not primary_df.empty:
            for strategy in self.strategies:
                try:
                    sig = strategy.analyze(primary_df, symbol)
                    strategy_signals.append(sig)
                except:
                    pass
        
        market_state = self._build_market_state(mtf_analysis, market_regime)
        learning_insight = neural_brain.generate_market_insight(market_state, symbol)
        
        decision = ai_brain.analyze_market(
            symbol=symbol,
            account_info=account,
            positions=positions,
            strategy_signals=strategy_signals,
            mtf_analysis=mtf_analysis,
            market_regime=market_regime,
            learning_insight=learning_insight
        )
        
        if decision.get('action') == 'hold' or decision.get('confidence', 0) < 0.4:
            decision = self._fallback_strategy_decision(strategy_signals, symbol, account)
        
        self._execute_decision(decision, account, market_state)
    
    def _fallback_strategy_decision(self, signals: List, symbol: str, account: Dict) -> Dict[str, Any]:
        buy_votes = 0
        sell_votes = 0
        buy_confidence = 0.0
        sell_confidence = 0.0
        
        for sig in signals:
            weight = neural_brain.get_strategy_weight(sig.strategy)
            if sig.signal.value == 'buy' and sig.confidence > 0.5:
                buy_votes += 1
                buy_confidence += sig.confidence * weight
            elif sig.signal.value == 'sell' and sig.confidence > 0.5:
                sell_votes += 1
                sell_confidence += sig.confidence * weight
        
        if buy_votes >= 4 and buy_confidence > sell_confidence:
            avg_conf = buy_confidence / max(buy_votes, 1)
            self._log(f"[FALLBACK] {buy_votes} strategies say BUY (conf: {avg_conf:.0%})")
            return {
                'action': 'buy',
                'symbol': symbol,
                'confidence': min(0.8, avg_conf),
                'sl_pips': 50,
                'tp_pips': 100,
                'entry_reason': f'Strategy consensus: {buy_votes}/10 BUY signals'
            }
        elif sell_votes >= 4 and sell_confidence > buy_confidence:
            avg_conf = sell_confidence / max(sell_votes, 1)
            self._log(f"[FALLBACK] {sell_votes} strategies say SELL (conf: {avg_conf:.0%})")
            return {
                'action': 'sell',
                'symbol': symbol,
                'confidence': min(0.8, avg_conf),
                'sl_pips': 50,
                'tp_pips': 100,
                'entry_reason': f'Strategy consensus: {sell_votes}/10 SELL signals'
            }
        
        return {'action': 'hold', 'confidence': 0}

    
    def _build_market_state(self, mtf_analysis: Dict, market_regime) -> Dict[str, Any]:
        trends = {}
        for tf, analysis in mtf_analysis.items():
            trends[tf] = analysis.trend
        
        primary = mtf_analysis.get(config.PRIMARY_TIMEFRAME)
        
        return {
            "regime": market_regime.regime,
            "regime_confidence": market_regime.confidence,
            "trends": trends,
            "momentum": primary.momentum if primary else "neutral",
            "volatility": primary.volatility if primary else "normal",
            "signals": primary.signals if primary else []
        }
    
    def _execute_decision(self, decision: Dict[str, Any], account: Dict[str, Any],
                          market_state: Dict[str, Any]):
        
        action = decision.get('action', 'hold')
        
        if action == 'hold':
            return
        
        if action == 'close_all':
            self._close_all_positions(decision.get('symbol'))
            return
        
        symbol = decision.get('symbol')
        if not symbol:
            return
        
        confidence = decision.get('confidence', 0)
        if confidence < 0.4:
            return
        
        symbol_info = mt5.get_symbol_info(symbol)
        if not symbol_info:
            return
        
        sl_pips = decision.get('sl_pips', 50)
        lot_size = risk_manager.calculate_position_size(
            account['balance'], confidence, sl_pips, symbol
        )
        
        if decision.get('lot_size'):
            lot_size = min(lot_size, float(decision['lot_size']))
        
        price = symbol_info['ask'] if action == 'buy' else symbol_info['bid']
        point = symbol_info['point']
        
        if decision.get('sl_price'):
            sl = float(decision['sl_price'])
        else:
            if symbol == 'XAUUSD':
                pip_size = 0.1
            elif 'USTECH' in symbol:
                pip_size = 0.1
            else:
                pip_size = 0.0001
            
            if action == 'buy':
                sl = price - (sl_pips * pip_size)
            else:
                sl = price + (sl_pips * pip_size)
        
        tp_pips = decision.get('tp_pips', sl_pips * 2)
        if decision.get('tp_price'):
            tp = float(decision['tp_price'])
        else:
            if action == 'buy':
                tp = price + (tp_pips * pip_size)
            else:
                tp = price - (tp_pips * pip_size)
        
        if action == 'buy':
            ticket = mt5.buy(symbol, lot_size, sl, tp)
        else:
            ticket = mt5.sell(symbol, lot_size, sl, tp)
        
        if ticket:
            risk_manager.log_trade_open(
                ticket, symbol, action, lot_size, price, sl, tp,
                decision, market_state
            )
            
            self._log(f"OPENED: {action.upper()} {lot_size}L {symbol} @ {price:.2f}")
            self._log(f"  SL: {sl:.2f} | TP: {tp:.2f} | Conf: {confidence:.0%}")
            self._log(f"  Reason: {decision.get('entry_reason', 'N/A')[:80]}")
    
    def _manage_positions(self, positions: List[Dict[str, Any]]):
        for pos in positions:
            symbol = pos['symbol']
            
            all_tf_data = mt5.get_all_timeframes(symbol)
            if not all_tf_data:
                continue
            
            mtf_analysis = mtf_analyzer.analyze_all_timeframes(all_tf_data, symbol)
            market_regime = mtf_analyzer.get_market_regime(mtf_analysis)
            
            primary_df = all_tf_data.get(config.PRIMARY_TIMEFRAME)
            signals = []
            
            if primary_df is not None and not primary_df.empty:
                for strategy in self.strategies:
                    try:
                        sig = strategy.analyze(primary_df, symbol)
                        signals.append(sig)
                    except:
                        pass
            
            should_close, reason = ai_brain.should_close_position(pos, signals, market_regime)
            
            if should_close:
                if mt5.close_position(pos['ticket']):
                    profit = pos['profit']
                    
                    risk_manager.log_trade_close(pos['ticket'], pos['current_price'], profit)
                    
                    market_state = self._build_market_state(mtf_analysis, market_regime)
                    strategy_signals = {s.strategy: s.signal.value for s in signals}
                    
                    memory = TradeMemory(
                        timestamp=datetime.now(),
                        symbol=symbol,
                        direction=pos['type'],
                        entry_price=pos['open_price'],
                        exit_price=pos['current_price'],
                        profit=profit,
                        market_state=market_state,
                        strategy_signals=strategy_signals,
                        ai_reasoning=reason,
                        outcome="win" if profit > 0 else "loss"
                    )
                    neural_brain.remember_trade(memory)
                    
                    self._log(f"CLOSED: #{pos['ticket']} {symbol} P/L: ${profit:+.2f}")
                    self._log(f"  Reason: {reason}")
            
            elif pos['profit'] > 0:
                self._trail_stop(pos, mtf_analysis)
    
    def _trail_stop(self, pos: Dict[str, Any], mtf_analysis: Dict):
        profit_pips = abs(pos['current_price'] - pos['open_price'])
        
        primary = mtf_analysis.get(config.PRIMARY_TIMEFRAME)
        if not primary:
            return
        
        atr_level = primary.key_levels.get('bb_middle', pos['open_price'])
        
        if pos['type'] == 'buy':
            if pos['current_price'] > pos['open_price']:
                new_sl = max(pos['sl'], pos['open_price'])
                
                if profit_pips > 0.005 * pos['open_price']:
                    new_sl = max(new_sl, atr_level)
                
                if new_sl > pos['sl']:
                    mt5.modify_position(pos['ticket'], sl=new_sl)
        else:
            if pos['current_price'] < pos['open_price']:
                new_sl = min(pos['sl'], pos['open_price']) if pos['sl'] > 0 else pos['open_price']
                
                if profit_pips > 0.005 * pos['open_price']:
                    new_sl = min(new_sl, atr_level)
                
                if pos['sl'] == 0 or new_sl < pos['sl']:
                    mt5.modify_position(pos['ticket'], sl=new_sl)
    
    def _close_all_positions(self, symbol: str = None):
        closed = mt5.close_all_positions(symbol)
        self._log(f"Closed {closed} positions")
    
    def _handle_shutdown(self, signum, frame):
        self._log("Shutting down...")
        self.running = False
        
        stats = risk_manager.get_performance_stats()
        self._log("=" * 60)
        self._log("SESSION SUMMARY")
        self._log(f"  Total Trades: {stats['total_trades']}")
        self._log(f"  Win Rate: {stats['win_rate']:.0%}")
        self._log(f"  Total P/L: ${stats['total_profit']:+.2f}")
        self._log("=" * 60)
        
        mt5.disconnect()
        sys.exit(0)
    
    def _log(self, message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")


def main():
    bot = TradingBot()
    bot.start()


if __name__ == "__main__":
    main()
