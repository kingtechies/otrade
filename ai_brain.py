import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from openai import OpenAI

from config import config
from strategies.base import TradeSignal, Signal
from mtf_analyzer import TimeframeAnalysis, MarketRegime
from neural_brain import LearningInsight, neural_brain


class AdvancedAIBrain:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = "gpt-4o"
        self.conversation_history = []
        self.max_history = 10
        
    def analyze_market(self, 
                       symbol: str,
                       account_info: Dict[str, Any],
                       positions: List[Dict[str, Any]],
                       strategy_signals: List[TradeSignal],
                       mtf_analysis: Dict[str, TimeframeAnalysis],
                       market_regime: MarketRegime,
                       learning_insight: LearningInsight) -> Dict[str, Any]:
        
        balance = account_info.get('balance', 0)
        equity = account_info.get('equity', 0)
        free_margin = account_info.get('free_margin', 0)
        current_profit = account_info.get('profit', 0)
        leverage = account_info.get('leverage', 100)
        
        progress = (balance / config.PRIMARY_TARGET) * 100 if config.PRIMARY_TARGET > 0 else 0
        
        mtf_summary = self._format_mtf_analysis(mtf_analysis)
        signals_summary = self._format_signals(strategy_signals)
        positions_summary = self._format_positions(positions)
        
        strategy_weights = {s.strategy: neural_brain.get_strategy_weight(s.strategy) 
                          for s in strategy_signals}
        symbol_bias = neural_brain.get_symbol_bias(symbol)
        
        prompt = f"""You are an elite institutional-grade trading AI with access to complete market data.

=== ACCOUNT STATUS ===
Balance: ${balance:.2f}
Equity: ${equity:.2f}
Free Margin: ${free_margin:.2f}
Leverage: 1:{leverage}
Open P/L: ${current_profit:+.2f}
Target: ${config.PRIMARY_TARGET:.2f} ({progress:.1f}% achieved)
Max Risk/Trade: {config.MAX_RISK_PER_TRADE * 100}%

=== OPEN POSITIONS ({len(positions)}/{config.MAX_OPEN_POSITIONS}) ===
{positions_summary or "None"}

=== MARKET REGIME ===
Symbol: {symbol}
Regime: {market_regime.regime.upper()} (confidence: {market_regime.confidence:.0%})
Analysis: {market_regime.description}

=== MULTI-TIMEFRAME ANALYSIS ===
{mtf_summary}

=== STRATEGY SIGNALS (weighted by historical performance) ===
{signals_summary}
Strategy Weights from Learning: {json.dumps(strategy_weights, indent=2)}

=== NEURAL BRAIN INSIGHT ===
Type: {learning_insight.insight_type}
Insight: {learning_insight.description}
Confidence: {learning_insight.confidence:.0%}
Data: {json.dumps(learning_insight.data)}

=== HISTORICAL PERFORMANCE ON {symbol} ===
Win Rate: {symbol_bias['win_rate']:.0%}
Avg Profit: ${symbol_bias['avg_profit']:.2f}
Total Trades: {symbol_bias['trades']}

=== DECISION FRAMEWORK ===
1. Analyze trend alignment across ALL timeframes (higher TF = more weight)
2. Consider market regime and volatility conditions
3. Weight strategy signals by their learned performance
4. Factor in neural brain patterns and insights
5. Calculate optimal position size based on confidence and risk
6. Set dynamic SL/TP based on ATR and key levels

=== REQUIRED OUTPUT (JSON) ===
{{
    "action": "buy" | "sell" | "hold" | "close_all" | "partial_close",
    "symbol": "{symbol}",
    "confidence": 0.0-1.0,
    "lot_size": calculated optimal lots,
    "sl_price": specific price level,
    "tp_price": specific price level,
    "sl_pips": backup if price not available,
    "tp_pips": backup if price not available,
    "entry_reason": "detailed analysis",
    "risk_reward": "calculated R:R ratio",
    "timeframe_alignment": "which timeframes agree",
    "key_levels_considered": ["level1", "level2"],
    "learning_applied": "how brain insights influenced decision"
}}"""

        try:
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
            ]
            
            for hist in self.conversation_history[-self.max_history:]:
                messages.append(hist)
            
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1000
            )
            
            decision = json.loads(response.choices[0].message.content)
            
            self.conversation_history.append({"role": "user", "content": f"Market analysis for {symbol}"})
            self.conversation_history.append({"role": "assistant", "content": json.dumps(decision)})
            
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]
            
            decision = self._validate_decision(decision, account_info, symbol)
            
            return decision
            
        except Exception as e:
            return {
                "action": "hold",
                "symbol": symbol,
                "confidence": 0,
                "entry_reason": f"Error: {str(e)}"
            }
    
    def _get_system_prompt(self) -> str:
        return """You are an elite quantitative trading AI managing real capital. Your core principles:

1. CAPITAL PRESERVATION is paramount. Never risk more than specified limits.
2. TREND IS YOUR FRIEND. Higher timeframes dictate direction, lower timeframes optimize entry.
3. CONFLUENCE is key. Only trade when multiple timeframes and indicators align.
4. LEARN AND ADAPT. Weight strategies based on their proven performance.
5. PATIENCE OVER ACTION. No trade is better than a bad trade.
6. DYNAMIC RISK. Adjust position size based on confidence and volatility.

You have complete market visibility from 1-minute to monthly charts. Use this comprehensive view to make institutional-quality decisions.

Always respond with valid JSON. Be precise with price levels and lot sizes."""
    
    def _format_mtf_analysis(self, analysis: Dict[str, TimeframeAnalysis]) -> str:
        if not analysis:
            return "No multi-timeframe data available"
        
        lines = []
        for tf in ["MN1", "W1", "D1", "H4", "H1", "M30", "M15", "M5", "M1"]:
            if tf in analysis:
                a = analysis[tf]
                signals_str = ", ".join(a.signals[:3]) if a.signals else "none"
                lines.append(
                    f"[{tf}] Trend: {a.trend} | Strength: {a.strength:.0%} | "
                    f"Momentum: {a.momentum} | Volatility: {a.volatility} | "
                    f"Signals: {signals_str}"
                )
        
        return "\n".join(lines)
    
    def _format_signals(self, signals: List[TradeSignal]) -> str:
        if not signals:
            return "No strategy signals"
        
        lines = []
        for sig in signals:
            weight = neural_brain.get_strategy_weight(sig.strategy)
            weighted_conf = sig.confidence * weight
            lines.append(
                f"[{sig.strategy}] {sig.signal.value.upper()} "
                f"(raw: {sig.confidence:.0%}, weighted: {weighted_conf:.0%}) - {sig.reason}"
            )
        
        return "\n".join(lines)
    
    def _format_positions(self, positions: List[Dict[str, Any]]) -> str:
        if not positions:
            return ""
        
        lines = []
        for pos in positions:
            lines.append(
                f"#{pos['ticket']} {pos['symbol']} {pos['type'].upper()} "
                f"{pos['volume']}L @ {pos['open_price']:.2f} -> {pos['current_price']:.2f} "
                f"P/L: ${pos['profit']:+.2f}"
            )
        
        return "\n".join(lines)
    
    def _validate_decision(self, decision: Dict[str, Any], 
                           account_info: Dict[str, Any],
                           symbol: str) -> Dict[str, Any]:
        
        decision['action'] = decision.get('action', 'hold').lower()
        decision['symbol'] = symbol
        decision['confidence'] = min(1.0, max(0.0, float(decision.get('confidence', 0))))
        
        if decision['action'] in ['buy', 'sell']:
            lot_size = float(decision.get('lot_size', 0.01))
            
            max_lot = account_info.get('free_margin', 0) / 1000
            lot_size = min(lot_size, max_lot, 10.0)
            lot_size = max(0.01, lot_size)
            
            decision['lot_size'] = round(lot_size, 2)
            
            if decision['confidence'] < 0.4:
                decision['action'] = 'hold'
                decision['entry_reason'] = f"Confidence too low ({decision['confidence']:.0%})"
        
        return decision
    
    def get_position_management_advice(self, 
                                        position: Dict[str, Any],
                                        current_analysis: Dict[str, TimeframeAnalysis],
                                        market_regime: MarketRegime) -> Dict[str, Any]:
        
        profit = position['profit']
        direction = position['type']
        symbol = position['symbol']
        
        prompt = f"""Analyze this open position and recommend management action:

Position: {direction.upper()} {position['volume']}L {symbol}
Entry: {position['open_price']:.2f}
Current: {position['current_price']:.2f}
P/L: ${profit:+.2f}
SL: {position['sl']:.2f}
TP: {position['tp']:.2f}

Market Regime: {market_regime.regime} ({market_regime.confidence:.0%})

Recommend one of:
1. HOLD - Keep position as is
2. PARTIAL_CLOSE - Take partial profits
3. MOVE_SL - Trail stop loss
4. CLOSE - Exit position
5. ADD - Scale into position

Respond in JSON with action, reason, and any new SL/TP levels."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a position management AI. Respond with JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=300
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception:
            return {"action": "hold", "reason": "Analysis error"}
    
    def should_close_position(self, position: Dict[str, Any],
                               signals: List[TradeSignal],
                               regime: MarketRegime) -> Tuple[bool, str]:
        
        direction = position['type']
        symbol = position['symbol']
        
        opposing_count = 0
        total_weight = 0
        
        for sig in signals:
            if sig.symbol != symbol:
                continue
            
            weight = neural_brain.get_strategy_weight(sig.strategy)
            total_weight += weight
            
            if direction == "buy" and sig.signal == Signal.SELL and sig.confidence > 0.6:
                opposing_count += weight
            elif direction == "sell" and sig.signal == Signal.BUY and sig.confidence > 0.6:
                opposing_count += weight
        
        if total_weight > 0 and opposing_count / total_weight > 0.6:
            return True, "Majority of strategies now opposing position"
        
        if direction == "buy" and regime.regime == "trending_bearish" and regime.confidence > 0.7:
            return True, "Market regime shifted bearish"
        elif direction == "sell" and regime.regime == "trending_bullish" and regime.confidence > 0.7:
            return True, "Market regime shifted bullish"
        
        return False, ""


from typing import Tuple
ai_brain = AdvancedAIBrain()
