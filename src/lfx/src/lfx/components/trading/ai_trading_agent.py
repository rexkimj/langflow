"""AI trading agent component for intelligent decision making."""

import json
import time
from typing import Any

from lfx.base.agents.agent import LCAgentComponent
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, FloatInput, HandleInput, MessageTextInput, Output, StrInput
from lfx.schema.data import Data
from lfx.schema.message import Message


class TradingAIAgent(Component):
    """AI-powered trading agent for analyzing market data and making trading decisions."""

    display_name = "Trading AI Agent"
    description = "AI agent that analyzes market data and provides trading recommendations"
    icon = "Brain"
    name = "TradingAIAgent"

    inputs = [
        DataInput(
            name="price_data",
            display_name="Price Data",
            required=True,
            info="Current price and market data",
        ),
        DataInput(
            name="portfolio_data",
            display_name="Portfolio Data",
            required=False,
            info="Current portfolio information",
        ),
        DataInput(
            name="risk_analysis",
            display_name="Risk Analysis",
            required=False,
            info="Risk analysis data",
        ),
        HandleInput(
            name="llm",
            display_name="Language Model",
            input_types=["LanguageModel"],
            required=True,
            info="LLM for decision making (e.g., OpenAI, Anthropic)",
        ),
        MessageTextInput(
            name="trading_strategy",
            display_name="Trading Strategy",
            value="You are a professional trading AI assistant. Analyze the provided market data and make informed trading decisions based on technical analysis and risk management principles.",
            info="System prompt defining the trading strategy",
        ),
        DropdownInput(
            name="analysis_mode",
            display_name="Analysis Mode",
            options=["technical", "fundamental", "sentiment", "comprehensive"],
            value="comprehensive",
            info="Type of market analysis to perform",
        ),
        BoolInput(
            name="include_reasoning",
            display_name="Include Reasoning",
            value=True,
            info="Include detailed reasoning in the recommendation",
        ),
        BoolInput(
            name="auto_execute",
            display_name="Auto Execute",
            value=False,
            info="Automatically execute recommended trades (CAUTION)",
        ),
        FloatInput(
            name="confidence_threshold",
            display_name="Confidence Threshold",
            value=0.7,
            info="Minimum confidence level to recommend trade (0-1)",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Trading Decision",
            name="trading_decision",
            method="analyze_and_decide",
        ),
    ]

    async def analyze_and_decide(self) -> Data:
        """Analyze market data using AI and provide trading recommendations."""
        try:
            price_info = self.price_data.data
            portfolio_info = self.portfolio_data.data if self.portfolio_data else {}
            risk_info = self.risk_analysis.data if self.risk_analysis else {}

            # Prepare market analysis context
            market_context = self._prepare_market_context(price_info, portfolio_info, risk_info)

            # Construct prompt for LLM
            analysis_prompt = self._construct_analysis_prompt(market_context)

            # Call LLM for analysis
            try:
                # Invoke the language model
                from langchain_core.messages import HumanMessage, SystemMessage

                messages = [
                    SystemMessage(content=self.trading_strategy),
                    HumanMessage(content=analysis_prompt),
                ]

                response = await self.llm.ainvoke(messages)
                ai_analysis = response.content

            except Exception as e:
                self.log(f"LLM invocation error: {e}")
                # Fallback to rule-based analysis
                ai_analysis = self._fallback_analysis(market_context)

            # Parse AI response and extract trading decision
            decision = self._parse_trading_decision(ai_analysis, market_context)

            # Apply confidence threshold
            if decision["confidence"] < self.confidence_threshold:
                decision["action"] = "hold"
                decision["reason"] = (
                    f"Confidence ({decision['confidence']:.2f}) below threshold "
                    f"({self.confidence_threshold:.2f}). Holding position."
                )

            # Log decision
            self.log(
                f"Trading Decision: {decision['action'].upper()} "
                f"(Confidence: {decision['confidence']:.2%})"
            )
            if self.include_reasoning:
                self.log(f"Reasoning: {decision['reason']}")

            result = {
                "status": "success",
                "action": decision["action"],
                "confidence": decision["confidence"],
                "reasoning": decision["reason"] if self.include_reasoning else "",
                "entry_price": decision.get("entry_price"),
                "target_price": decision.get("target_price"),
                "stop_loss_price": decision.get("stop_loss_price"),
                "position_size": decision.get("position_size"),
                "risk_reward_ratio": decision.get("risk_reward_ratio"),
                "technical_indicators": decision.get("technical_indicators", {}),
                "market_context": market_context,
                "ai_analysis": ai_analysis,
                "auto_execute": self.auto_execute,
                "timestamp": int(time.time() * 1000),
            }

            return Data(data=result)

        except Exception as e:
            self.log(f"Error in AI trading agent: {e}")
            return Data(
                data={
                    "status": "error",
                    "error": str(e),
                    "action": "hold",
                    "confidence": 0.0,
                    "timestamp": int(time.time() * 1000),
                }
            )

    def _prepare_market_context(
        self, price_info: dict, portfolio_info: dict, risk_info: dict
    ) -> dict:
        """Prepare comprehensive market context for analysis."""
        context = {
            "current_price": price_info.get("current_price", 0),
            "symbol": price_info.get("symbol", "UNKNOWN"),
            "exchange": price_info.get("exchange", "UNKNOWN"),
        }

        # Price movements
        if "price_change_24h" in price_info:
            context["price_change_24h"] = price_info["price_change_24h"]
        if "price_change_percent_24h" in price_info:
            context["price_change_percent_24h"] = price_info["price_change_percent_24h"]

        # Price range
        context["high_24h"] = price_info.get("high_24h", 0)
        context["low_24h"] = price_info.get("low_24h", 0)
        context["volume_24h"] = price_info.get("volume_24h", 0)

        # Technical indicators from candles
        if "candles" in price_info and len(price_info["candles"]) > 0:
            candles = price_info["candles"]
            context["technical_indicators"] = self._calculate_technical_indicators(candles)

        # Order book data
        if "orderbook" in price_info:
            orderbook = price_info["orderbook"]
            context["orderbook_imbalance"] = self._calculate_orderbook_imbalance(orderbook)

        # Portfolio information
        if portfolio_info:
            context["account_balance"] = portfolio_info.get("total_balance", 0)
            context["available_balance"] = portfolio_info.get("available_balance", 0)
            context["current_positions"] = len(portfolio_info.get("positions", []))
            context["total_pnl"] = portfolio_info.get("total_pnl", 0)

        # Risk information
        if risk_info:
            context["risk_level"] = risk_info.get("risk_level", "UNKNOWN")
            context["risk_warnings"] = risk_info.get("warnings", [])

        return context

    def _calculate_technical_indicators(self, candles: list) -> dict:
        """Calculate basic technical indicators from candle data."""
        if len(candles) < 20:
            return {}

        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c["volume"] for c in candles]

        indicators = {}

        # Simple Moving Averages
        indicators["sma_20"] = sum(closes[-20:]) / 20
        if len(closes) >= 50:
            indicators["sma_50"] = sum(closes[-50:]) / 50

        # Relative Strength Index (RSI)
        indicators["rsi_14"] = self._calculate_rsi(closes, 14)

        # MACD
        macd_data = self._calculate_macd(closes)
        indicators.update(macd_data)

        # Bollinger Bands
        bb_data = self._calculate_bollinger_bands(closes, 20, 2)
        indicators.update(bb_data)

        # Volume trend
        if len(volumes) >= 20:
            indicators["volume_sma_20"] = sum(volumes[-20:]) / 20
            indicators["volume_trend"] = "increasing" if volumes[-1] > indicators["volume_sma_20"] else "decreasing"

        # Price momentum
        indicators["momentum"] = (closes[-1] - closes[-10]) / closes[-10] * 100 if len(closes) >= 10 else 0

        return indicators

    def _calculate_rsi(self, prices: list, period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return 50.0

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(self, prices: list, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """Calculate MACD indicator."""
        if len(prices) < slow:
            return {}

        # Calculate EMAs
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)

        macd_line = ema_fast - ema_slow

        # For simplicity, using SMA for signal line
        # In production, should use EMA
        return {"macd": macd_line, "ema_fast": ema_fast, "ema_slow": ema_slow}

    def _calculate_ema(self, prices: list, period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return sum(prices) / len(prices)

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def _calculate_bollinger_bands(self, prices: list, period: int = 20, std_dev: int = 2) -> dict:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return {}

        sma = sum(prices[-period:]) / period
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std = variance**0.5

        return {
            "bb_middle": sma,
            "bb_upper": sma + (std_dev * std),
            "bb_lower": sma - (std_dev * std),
            "bb_width": (std_dev * std * 2) / sma * 100,
        }

    def _calculate_orderbook_imbalance(self, orderbook: dict) -> float:
        """Calculate order book imbalance ratio."""
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        if not bids or not asks:
            return 0

        bid_volume = sum(b[1] for b in bids[:10])
        ask_volume = sum(a[1] for a in asks[:10])

        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return 0

        # Positive = more buying pressure, Negative = more selling pressure
        return (bid_volume - ask_volume) / total_volume

    def _construct_analysis_prompt(self, market_context: dict) -> str:
        """Construct comprehensive prompt for LLM analysis."""
        prompt = f"""Analyze the following market data and provide a trading recommendation:

**Symbol:** {market_context.get('symbol')}
**Current Price:** ${market_context.get('current_price', 0):,.2f}
**24h Change:** {market_context.get('price_change_percent_24h', 0):.2f}%
**24h High:** ${market_context.get('high_24h', 0):,.2f}
**24h Low:** ${market_context.get('low_24h', 0):,.2f}
**24h Volume:** {market_context.get('volume_24h', 0):,.2f}

"""

        # Add technical indicators
        if "technical_indicators" in market_context:
            ti = market_context["technical_indicators"]
            prompt += "**Technical Indicators:**\n"
            if "rsi_14" in ti:
                prompt += f"- RSI(14): {ti['rsi_14']:.2f}\n"
            if "sma_20" in ti:
                prompt += f"- SMA(20): ${ti['sma_20']:,.2f}\n"
            if "sma_50" in ti:
                prompt += f"- SMA(50): ${ti['sma_50']:,.2f}\n"
            if "bb_middle" in ti:
                prompt += (
                    f"- Bollinger Bands: ${ti['bb_lower']:,.2f} / ${ti['bb_middle']:,.2f} / ${ti['bb_upper']:,.2f}\n"
                )
            if "momentum" in ti:
                prompt += f"- Momentum: {ti['momentum']:.2f}%\n"
            prompt += "\n"

        # Add portfolio context
        if "account_balance" in market_context:
            prompt += f"""**Account Information:**
- Total Balance: ${market_context.get('account_balance', 0):,.2f}
- Available Balance: ${market_context.get('available_balance', 0):,.2f}
- Current Positions: {market_context.get('current_positions', 0)}
- Total PnL: ${market_context.get('total_pnl', 0):,.2f}

"""

        # Add risk context
        if "risk_level" in market_context:
            prompt += f"**Risk Level:** {market_context.get('risk_level')}\n"
            if market_context.get("risk_warnings"):
                prompt += "**Risk Warnings:**\n"
                for warning in market_context.get("risk_warnings", []):
                    prompt += f"- {warning}\n"
            prompt += "\n"

        prompt += """
Please provide a trading recommendation in the following JSON format:
{
    "action": "buy|sell|hold",
    "confidence": 0.0-1.0,
    "reason": "detailed explanation",
    "entry_price": <price>,
    "target_price": <price>,
    "stop_loss_price": <price>,
    "position_size_percent": <percentage of available balance>
}

Consider:
1. Technical indicators and price action
2. Risk management principles
3. Account balance and position sizing
4. Market conditions and volatility
5. Risk/reward ratio (minimum 1.5:1)
"""

        return prompt

    def _parse_trading_decision(self, ai_response: str, market_context: dict) -> dict:
        """Parse AI response and extract trading decision."""
        try:
            # Try to extract JSON from response
            import re

            json_match = re.search(r"\{[^}]+\}", ai_response, re.DOTALL)
            if json_match:
                decision_json = json.loads(json_match.group())
                return {
                    "action": decision_json.get("action", "hold").lower(),
                    "confidence": float(decision_json.get("confidence", 0.5)),
                    "reason": decision_json.get("reason", "AI analysis completed"),
                    "entry_price": decision_json.get("entry_price"),
                    "target_price": decision_json.get("target_price"),
                    "stop_loss_price": decision_json.get("stop_loss_price"),
                    "position_size": decision_json.get("position_size_percent", 10),
                    "technical_indicators": market_context.get("technical_indicators", {}),
                }
        except Exception as e:
            self.log(f"Error parsing AI response: {e}")

        # Fallback: analyze keywords in response
        response_lower = ai_response.lower()
        if "buy" in response_lower or "long" in response_lower:
            action = "buy"
            confidence = 0.6
        elif "sell" in response_lower or "short" in response_lower:
            action = "sell"
            confidence = 0.6
        else:
            action = "hold"
            confidence = 0.7

        return {
            "action": action,
            "confidence": confidence,
            "reason": ai_response[:500],  # First 500 chars
            "entry_price": market_context.get("current_price"),
            "technical_indicators": market_context.get("technical_indicators", {}),
        }

    def _fallback_analysis(self, market_context: dict) -> str:
        """Fallback rule-based analysis when LLM is unavailable."""
        ti = market_context.get("technical_indicators", {})
        current_price = market_context.get("current_price", 0)

        reasons = []
        score = 0

        # RSI analysis
        if "rsi_14" in ti:
            rsi = ti["rsi_14"]
            if rsi < 30:
                reasons.append("RSI indicates oversold condition")
                score += 2
            elif rsi > 70:
                reasons.append("RSI indicates overbought condition")
                score -= 2
            elif 40 < rsi < 60:
                reasons.append("RSI is neutral")

        # Moving average analysis
        if "sma_20" in ti and "sma_50" in ti:
            if ti["sma_20"] > ti["sma_50"]:
                reasons.append("Bullish: SMA(20) > SMA(50)")
                score += 1
            else:
                reasons.append("Bearish: SMA(20) < SMA(50)")
                score -= 1

        # Price vs SMA
        if "sma_20" in ti:
            if current_price > ti["sma_20"]:
                reasons.append("Price above SMA(20)")
                score += 1
            else:
                reasons.append("Price below SMA(20)")
                score -= 1

        # Momentum
        if "momentum" in ti:
            momentum = ti["momentum"]
            if momentum > 2:
                reasons.append(f"Strong positive momentum ({momentum:.2f}%)")
                score += 1
            elif momentum < -2:
                reasons.append(f"Strong negative momentum ({momentum:.2f}%)")
                score -= 1

        # Determine action
        if score >= 3:
            action = "buy"
            confidence = min(0.8, 0.5 + (score * 0.05))
        elif score <= -3:
            action = "sell"
            confidence = min(0.8, 0.5 + (abs(score) * 0.05))
        else:
            action = "hold"
            confidence = 0.6

        reason_text = " | ".join(reasons) if reasons else "Insufficient data for decision"

        return json.dumps(
            {
                "action": action,
                "confidence": confidence,
                "reason": f"Rule-based analysis: {reason_text}",
                "position_size_percent": 5,
            }
        )

    def build(self):
        return self.analyze_and_decide
