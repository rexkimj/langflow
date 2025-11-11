"""Risk management components for stop-loss, take-profit, and risk analysis."""

import time
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, FloatInput, IntInput, Output, StrInput
from lfx.schema.data import Data


class StopLossManager(Component):
    """Manage stop-loss and take-profit orders with trailing stop support."""

    display_name = "Stop Loss Manager"
    description = "Set and manage stop-loss and take-profit levels with trailing stop"
    icon = "Shield"
    name = "StopLossManager"

    inputs = [
        DataInput(
            name="price_data",
            display_name="Price Data",
            required=True,
            info="Current price data from price feed",
        ),
        DataInput(
            name="position_data",
            display_name="Position Data",
            required=False,
            info="Current position information",
        ),
        FloatInput(
            name="entry_price",
            display_name="Entry Price",
            required=True,
            info="Position entry price",
        ),
        DropdownInput(
            name="position_side",
            display_name="Position Side",
            options=["long", "short"],
            value="long",
            required=True,
            info="Long or short position",
        ),
        FloatInput(
            name="stop_loss_percent",
            display_name="Stop Loss %",
            value=2.0,
            info="Stop loss percentage from entry price",
        ),
        FloatInput(
            name="take_profit_percent",
            display_name="Take Profit %",
            value=5.0,
            info="Take profit percentage from entry price",
        ),
        BoolInput(
            name="use_trailing_stop",
            display_name="Use Trailing Stop",
            value=False,
            info="Enable trailing stop loss",
        ),
        FloatInput(
            name="trailing_stop_percent",
            display_name="Trailing Stop %",
            value=1.0,
            info="Trailing stop percentage from highest/lowest price",
        ),
        BoolInput(
            name="use_atr_stop",
            display_name="Use ATR-based Stop",
            value=False,
            info="Use Average True Range for dynamic stop loss",
            advanced=True,
        ),
        FloatInput(
            name="atr_multiplier",
            display_name="ATR Multiplier",
            value=2.0,
            info="Multiplier for ATR-based stop loss",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Risk Management",
            name="risk_management",
            method="calculate_stop_loss",
        ),
    ]

    def calculate_stop_loss(self) -> Data:
        """Calculate stop-loss and take-profit levels."""
        try:
            price_info = self.price_data.data
            current_price = price_info.get("current_price", 0)

            if current_price == 0:
                raise ValueError("Invalid current price")

            # Calculate basic stop loss and take profit
            if self.position_side == "long":
                stop_loss_price = self.entry_price * (1 - self.stop_loss_percent / 100)
                take_profit_price = self.entry_price * (1 + self.take_profit_percent / 100)
            else:  # short
                stop_loss_price = self.entry_price * (1 + self.stop_loss_percent / 100)
                take_profit_price = self.entry_price * (1 - self.take_profit_percent / 100)

            # Calculate trailing stop if enabled
            trailing_stop_price = None
            if self.use_trailing_stop:
                if self.position_side == "long":
                    # For long, trail from highest price
                    highest_price = max(current_price, self.entry_price)
                    trailing_stop_price = highest_price * (1 - self.trailing_stop_percent / 100)
                    # Use higher of basic stop or trailing stop
                    stop_loss_price = max(stop_loss_price, trailing_stop_price)
                else:  # short
                    # For short, trail from lowest price
                    lowest_price = min(current_price, self.entry_price)
                    trailing_stop_price = lowest_price * (1 + self.trailing_stop_percent / 100)
                    # Use lower of basic stop or trailing stop
                    stop_loss_price = min(stop_loss_price, trailing_stop_price)

            # Calculate ATR-based stop if enabled
            atr_stop_price = None
            if self.use_atr_stop and "candles" in price_info:
                atr = self._calculate_atr(price_info["candles"])
                if self.position_side == "long":
                    atr_stop_price = current_price - (atr * self.atr_multiplier)
                    stop_loss_price = max(stop_loss_price, atr_stop_price)
                else:
                    atr_stop_price = current_price + (atr * self.atr_multiplier)
                    stop_loss_price = min(stop_loss_price, atr_stop_price)

            # Check if stop loss or take profit triggered
            stop_triggered = False
            take_profit_triggered = False

            if self.position_side == "long":
                stop_triggered = current_price <= stop_loss_price
                take_profit_triggered = current_price >= take_profit_price
            else:
                stop_triggered = current_price >= stop_loss_price
                take_profit_triggered = current_price <= take_profit_price

            # Calculate risk metrics
            risk_amount = abs(self.entry_price - stop_loss_price)
            reward_amount = abs(take_profit_price - self.entry_price)
            risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0

            pnl_percent = ((current_price - self.entry_price) / self.entry_price * 100) * (
                1 if self.position_side == "long" else -1
            )

            result = {
                "status": "success",
                "entry_price": self.entry_price,
                "current_price": current_price,
                "position_side": self.position_side,
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_price,
                "trailing_stop_price": trailing_stop_price,
                "atr_stop_price": atr_stop_price,
                "stop_triggered": stop_triggered,
                "take_profit_triggered": take_profit_triggered,
                "risk_amount": risk_amount,
                "reward_amount": reward_amount,
                "risk_reward_ratio": risk_reward_ratio,
                "pnl_percent": pnl_percent,
                "distance_to_stop_percent": abs(current_price - stop_loss_price) / current_price * 100,
                "distance_to_target_percent": abs(take_profit_price - current_price)
                / current_price
                * 100,
                "timestamp": int(time.time() * 1000),
            }

            if stop_triggered:
                self.log(f"⚠️ STOP LOSS TRIGGERED at {current_price}")
            elif take_profit_triggered:
                self.log(f"✅ TAKE PROFIT TRIGGERED at {current_price}")
            else:
                self.log(
                    f"Position monitoring: Entry: {self.entry_price}, Current: {current_price}, "
                    f"Stop: {stop_loss_price:.2f}, Target: {take_profit_price:.2f}"
                )

            return Data(data=result)

        except Exception as e:
            self.log(f"Error calculating stop loss: {e}")
            return Data(
                data={
                    "status": "error",
                    "error": str(e),
                    "timestamp": int(time.time() * 1000),
                }
            )

    def _calculate_atr(self, candles: list, period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(candles) < period + 1:
            return 0

        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]

            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)

        # Return average of last 'period' true ranges
        return sum(true_ranges[-period:]) / period if true_ranges else 0

    def build(self):
        return self.calculate_stop_loss


class RiskAnalyzer(Component):
    """Analyze trading risk including position size, leverage, and portfolio risk."""

    display_name = "Risk Analyzer"
    description = "Analyze risk metrics and provide risk warnings for trades"
    icon = "AlertTriangle"
    name = "RiskAnalyzer"

    inputs = [
        DataInput(
            name="price_data",
            display_name="Price Data",
            required=True,
            info="Current price data",
        ),
        DataInput(
            name="portfolio_data",
            display_name="Portfolio Data",
            required=True,
            info="Current portfolio/account balance",
        ),
        FloatInput(
            name="position_size",
            display_name="Position Size",
            required=True,
            info="Size of position to open (in quote currency)",
        ),
        FloatInput(
            name="entry_price",
            display_name="Entry Price",
            required=True,
            info="Planned entry price",
        ),
        FloatInput(
            name="stop_loss_price",
            display_name="Stop Loss Price",
            required=True,
            info="Stop loss price",
        ),
        IntInput(
            name="leverage",
            display_name="Leverage",
            value=1,
            info="Leverage multiplier",
        ),
        FloatInput(
            name="max_risk_per_trade_percent",
            display_name="Max Risk Per Trade %",
            value=2.0,
            info="Maximum risk per trade as % of account",
        ),
        FloatInput(
            name="max_portfolio_risk_percent",
            display_name="Max Portfolio Risk %",
            value=10.0,
            info="Maximum total portfolio risk %",
        ),
        FloatInput(
            name="max_leverage",
            display_name="Max Leverage",
            value=10.0,
            info="Maximum allowed leverage",
        ),
        BoolInput(
            name="check_volatility",
            display_name="Check Volatility",
            value=True,
            info="Analyze volatility risk",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Risk Analysis",
            name="risk_analysis",
            method="analyze_risk",
        ),
    ]

    def analyze_risk(self) -> Data:
        """Analyze risk metrics and generate warnings."""
        try:
            price_info = self.price_data.data
            portfolio_info = self.portfolio_data.data
            current_price = price_info.get("current_price", self.entry_price)

            # Get account balance
            account_balance = self._extract_account_balance(portfolio_info)

            if account_balance == 0:
                raise ValueError("Invalid account balance")

            # Calculate risk per trade
            risk_per_share = abs(self.entry_price - self.stop_loss_price)
            quantity = self.position_size / self.entry_price
            total_risk = risk_per_share * quantity
            risk_percent = (total_risk / account_balance) * 100

            # Calculate position size as % of account
            position_value = self.position_size * self.leverage
            position_percent = (position_value / account_balance) * 100

            # Calculate margin required
            margin_required = position_value / self.leverage if self.leverage > 0 else position_value
            margin_percent = (margin_required / account_balance) * 100

            # Risk/Reward ratio
            reward_per_share = abs(
                self.entry_price * 1.05 - self.entry_price
            )  # Assume 5% target for calculation
            risk_reward_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0

            # Volatility analysis
            volatility_score = 0
            volatility_warning = False
            if self.check_volatility and "candles" in price_info:
                volatility_score = self._calculate_volatility(price_info["candles"])
                volatility_warning = volatility_score > 5.0  # High volatility threshold

            # Generate warnings
            warnings = []
            risk_level = "LOW"

            if risk_percent > self.max_risk_per_trade_percent:
                warnings.append(
                    f"⚠️ Risk per trade ({risk_percent:.2f}%) exceeds maximum ({self.max_risk_per_trade_percent}%)"
                )
                risk_level = "HIGH"

            if self.leverage > self.max_leverage:
                warnings.append(
                    f"⚠️ Leverage ({self.leverage}x) exceeds maximum ({self.max_leverage}x)"
                )
                risk_level = "HIGH"

            if position_percent > 50:
                warnings.append(
                    f"⚠️ Position size ({position_percent:.1f}%) is too large relative to account"
                )
                risk_level = "HIGH"

            if margin_percent > 80:
                warnings.append(f"⚠️ High margin usage ({margin_percent:.1f}%) - risk of liquidation")
                risk_level = "HIGH"

            if risk_reward_ratio < 1.5:
                warnings.append(
                    f"⚠️ Poor risk/reward ratio ({risk_reward_ratio:.2f}) - should be at least 1.5"
                )

            if volatility_warning:
                warnings.append(
                    f"⚠️ High volatility detected ({volatility_score:.2f}%) - increased risk"
                )

            # Calculate liquidation price for leveraged positions
            liquidation_price = None
            if self.leverage > 1:
                # Simplified liquidation calculation
                liquidation_percent = 1 / self.leverage * 0.9  # 90% of initial margin
                liquidation_price = self.entry_price * (1 - liquidation_percent)

            # Determine overall risk level
            if len(warnings) == 0:
                risk_level = "LOW"
            elif len(warnings) <= 2:
                risk_level = "MEDIUM" if risk_level != "HIGH" else "HIGH"

            # Calculate optimal position size based on risk
            optimal_position_size = (
                (account_balance * self.max_risk_per_trade_percent / 100) / risk_per_share
                if risk_per_share > 0
                else 0
            )

            result = {
                "status": "success",
                "risk_level": risk_level,
                "account_balance": account_balance,
                "position_size": self.position_size,
                "position_value": position_value,
                "position_percent": position_percent,
                "quantity": quantity,
                "entry_price": self.entry_price,
                "stop_loss_price": self.stop_loss_price,
                "leverage": self.leverage,
                "margin_required": margin_required,
                "margin_percent": margin_percent,
                "risk_per_trade": total_risk,
                "risk_percent": risk_percent,
                "risk_reward_ratio": risk_reward_ratio,
                "volatility_score": volatility_score,
                "liquidation_price": liquidation_price,
                "optimal_position_size": optimal_position_size,
                "warnings": warnings,
                "is_safe_to_trade": len([w for w in warnings if "⚠️" in w]) == 0,
                "timestamp": int(time.time() * 1000),
            }

            # Log warnings
            if warnings:
                self.log(f"Risk Analysis - {risk_level} RISK:")
                for warning in warnings:
                    self.log(warning)
            else:
                self.log(
                    f"Risk Analysis - {risk_level} RISK: All checks passed. Risk per trade: {risk_percent:.2f}%"
                )

            return Data(data=result)

        except Exception as e:
            self.log(f"Error analyzing risk: {e}")
            return Data(
                data={
                    "status": "error",
                    "error": str(e),
                    "risk_level": "UNKNOWN",
                    "warnings": [f"Error analyzing risk: {e}"],
                    "is_safe_to_trade": False,
                    "timestamp": int(time.time() * 1000),
                }
            )

    def _extract_account_balance(self, portfolio_info: dict) -> float:
        """Extract account balance from portfolio data."""
        # Handle different exchange formats
        if "total_balance" in portfolio_info:
            return float(portfolio_info["total_balance"])
        elif "balances" in portfolio_info:
            # Binance format - sum USDT or other quote currency
            balances = portfolio_info["balances"]
            for balance in balances:
                if isinstance(balance, dict) and balance.get("asset") in ["USDT", "USD", "BUSD"]:
                    return float(balance.get("free", 0)) + float(balance.get("locked", 0))
        elif "account_info" in portfolio_info:
            # Bybit format
            wallet_balance = portfolio_info["account_info"].get("list", [{}])[0]
            return float(wallet_balance.get("totalEquity", 0))

        # Default fallback
        return 10000.0  # Default for testing

    def _calculate_volatility(self, candles: list, period: int = 20) -> float:
        """Calculate price volatility (standard deviation of returns)."""
        if len(candles) < period:
            return 0

        recent_candles = candles[-period:]
        returns = []

        for i in range(1, len(recent_candles)):
            ret = (
                (recent_candles[i]["close"] - recent_candles[i - 1]["close"])
                / recent_candles[i - 1]["close"]
                * 100
            )
            returns.append(ret)

        if not returns:
            return 0

        # Calculate standard deviation
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        std_dev = variance**0.5

        return std_dev

    def build(self):
        return self.analyze_risk
