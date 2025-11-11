"""Performance reporting components for analyzing trading results and profitability."""

import time
from datetime import datetime, timedelta
from typing import Any, List

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, FloatInput, IntInput, Output
from lfx.schema.data import Data


class PerformanceReporter(Component):
    """Generate comprehensive performance reports with profitability metrics and analytics."""

    display_name = "Performance Reporter"
    description = "Generate detailed performance reports with profit/loss metrics and analytics"
    icon = "TrendingUp"
    name = "PerformanceReporter"

    inputs = [
        DataInput(
            name="portfolio_data",
            display_name="Portfolio Data",
            required=True,
            info="Current portfolio information",
        ),
        DataInput(
            name="trade_history",
            display_name="Trade History",
            required=False,
            info="Historical trade data (if available)",
        ),
        FloatInput(
            name="initial_balance",
            display_name="Initial Balance",
            required=True,
            info="Starting account balance for performance calculation",
        ),
        DropdownInput(
            name="report_period",
            display_name="Report Period",
            options=["daily", "weekly", "monthly", "all_time"],
            value="all_time",
            info="Time period for performance report",
        ),
        BoolInput(
            name="include_metrics",
            display_name="Include Detailed Metrics",
            value=True,
            info="Include advanced performance metrics",
        ),
        BoolInput(
            name="include_charts",
            display_name="Include Chart Data",
            value=True,
            info="Include data for performance charts",
        ),
        IntInput(
            name="risk_free_rate",
            display_name="Risk-Free Rate %",
            value=4,
            info="Annual risk-free rate for Sharpe ratio calculation",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Performance Report",
            name="performance_report",
            method="generate_report",
        ),
    ]

    def generate_report(self) -> Data:
        """Generate comprehensive performance report."""
        try:
            portfolio_info = self.portfolio_data.data
            trade_history = self.trade_history.data if self.trade_history else None

            # Extract current portfolio metrics
            current_balance = portfolio_info.get("total_balance", 0)
            available_balance = portfolio_info.get("available_balance", 0)
            positions = portfolio_info.get("positions", [])
            total_pnl = portfolio_info.get("total_pnl", 0)

            # Calculate basic performance metrics
            total_return = current_balance - self.initial_balance
            total_return_percent = (
                (total_return / self.initial_balance * 100) if self.initial_balance > 0 else 0
            )

            # Position analysis
            open_positions = len(positions)
            total_position_value = sum(
                p.get("eval_amount", p.get("size", 0) * p.get("mark_price", 0)) for p in positions
            )

            winning_positions = [p for p in positions if p.get("pnl", p.get("unrealized_pnl", 0)) > 0]
            losing_positions = [p for p in positions if p.get("pnl", p.get("unrealized_pnl", 0)) < 0]

            win_rate = (
                (len(winning_positions) / len(positions) * 100) if positions else 0
            )

            # Calculate detailed metrics
            detailed_metrics = {}
            if self.include_metrics:
                detailed_metrics = self._calculate_detailed_metrics(
                    portfolio_info, trade_history, self.initial_balance
                )

            # Generate chart data
            chart_data = {}
            if self.include_charts:
                chart_data = self._generate_chart_data(
                    portfolio_info, trade_history, self.initial_balance
                )

            # Risk metrics
            risk_metrics = self._calculate_risk_metrics(
                portfolio_info, current_balance, self.initial_balance
            )

            # Generate summary
            summary = self._generate_summary(
                current_balance,
                self.initial_balance,
                total_return_percent,
                win_rate,
                open_positions,
            )

            result = {
                "status": "success",
                "report_period": self.report_period,
                "generated_at": int(time.time() * 1000),
                # Balance Information
                "initial_balance": self.initial_balance,
                "current_balance": current_balance,
                "available_balance": available_balance,
                "locked_balance": current_balance - available_balance,
                # Performance Metrics
                "total_return": total_return,
                "total_return_percent": total_return_percent,
                "total_pnl": total_pnl,
                "realized_pnl": detailed_metrics.get("realized_pnl", 0),
                "unrealized_pnl": total_pnl,
                # Position Metrics
                "open_positions": open_positions,
                "total_position_value": total_position_value,
                "winning_positions": len(winning_positions),
                "losing_positions": len(losing_positions),
                "win_rate": win_rate,
                # Risk Metrics
                "risk_metrics": risk_metrics,
                # Detailed Metrics
                "detailed_metrics": detailed_metrics,
                # Chart Data
                "chart_data": chart_data,
                # Summary
                "summary": summary,
                # Position Details
                "position_details": self._format_position_details(positions),
            }

            # Log summary
            self.log(f"Performance Report Generated:")
            self.log(f"  Total Return: {total_return_percent:+.2f}%")
            self.log(f"  Current Balance: {current_balance:,.2f}")
            self.log(f"  Open Positions: {open_positions}")
            self.log(f"  Win Rate: {win_rate:.1f}%")

            return Data(data=result)

        except Exception as e:
            self.log(f"Error generating performance report: {e}")
            return Data(
                data={
                    "status": "error",
                    "error": str(e),
                    "timestamp": int(time.time() * 1000),
                }
            )

    def _calculate_detailed_metrics(
        self, portfolio_info: dict, trade_history: dict | None, initial_balance: float
    ) -> dict:
        """Calculate detailed performance metrics."""
        metrics = {}

        current_balance = portfolio_info.get("total_balance", 0)
        positions = portfolio_info.get("positions", [])

        # Average win/loss
        if positions:
            winning_pnls = [
                p.get("pnl", p.get("unrealized_pnl", 0))
                for p in positions
                if p.get("pnl", p.get("unrealized_pnl", 0)) > 0
            ]
            losing_pnls = [
                p.get("pnl", p.get("unrealized_pnl", 0))
                for p in positions
                if p.get("pnl", p.get("unrealized_pnl", 0)) < 0
            ]

            metrics["average_win"] = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
            metrics["average_loss"] = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
            metrics["profit_factor"] = (
                abs(sum(winning_pnls) / sum(losing_pnls)) if sum(losing_pnls) != 0 else 0
            )

        # Return on Investment
        metrics["roi"] = ((current_balance - initial_balance) / initial_balance * 100) if initial_balance > 0 else 0

        # Max drawdown (simplified - would need historical data for accurate calculation)
        metrics["max_drawdown_percent"] = self._estimate_max_drawdown(positions, initial_balance)

        # Sharpe Ratio (simplified)
        metrics["sharpe_ratio"] = self._calculate_sharpe_ratio(
            current_balance, initial_balance, self.risk_free_rate
        )

        # Trade statistics from history if available
        if trade_history and isinstance(trade_history, dict):
            trades = trade_history.get("trades", [])
            if trades:
                metrics["total_trades"] = len(trades)
                metrics["winning_trades"] = len([t for t in trades if t.get("pnl", 0) > 0])
                metrics["losing_trades"] = len([t for t in trades if t.get("pnl", 0) < 0])
                metrics["trade_win_rate"] = (
                    (metrics["winning_trades"] / metrics["total_trades"] * 100)
                    if metrics["total_trades"] > 0
                    else 0
                )

        return metrics

    def _calculate_risk_metrics(
        self, portfolio_info: dict, current_balance: float, initial_balance: float
    ) -> dict:
        """Calculate risk-related metrics."""
        positions = portfolio_info.get("positions", [])

        # Portfolio exposure
        total_position_value = sum(
            p.get("eval_amount", p.get("size", 0) * p.get("mark_price", 0)) for p in positions
        )
        exposure_percent = (
            (total_position_value / current_balance * 100) if current_balance > 0 else 0
        )

        # Leverage usage
        avg_leverage = (
            sum(p.get("leverage", 1) for p in positions) / len(positions) if positions else 1
        )

        # Position concentration
        if positions and total_position_value > 0:
            position_values = [
                p.get("eval_amount", p.get("size", 0) * p.get("mark_price", 0)) for p in positions
            ]
            largest_position_percent = (
                max(position_values) / total_position_value * 100 if position_values else 0
            )
        else:
            largest_position_percent = 0

        # Risk of ruin (simplified)
        risk_per_trade = 2.0  # Assumed 2% risk per trade
        win_rate = self._calculate_current_win_rate(positions)
        risk_of_ruin = self._calculate_risk_of_ruin(win_rate, risk_per_trade)

        return {
            "portfolio_exposure_percent": exposure_percent,
            "average_leverage": avg_leverage,
            "largest_position_percent": largest_position_percent,
            "risk_of_ruin_percent": risk_of_ruin,
            "capital_preservation_rate": (
                (current_balance / initial_balance * 100) if initial_balance > 0 else 100
            ),
        }

    def _estimate_max_drawdown(self, positions: list, initial_balance: float) -> float:
        """Estimate maximum drawdown (simplified without historical data)."""
        if not positions:
            return 0

        # Use current losing positions as proxy
        total_losses = sum(
            abs(p.get("pnl", p.get("unrealized_pnl", 0)))
            for p in positions
            if p.get("pnl", p.get("unrealized_pnl", 0)) < 0
        )

        return (total_losses / initial_balance * 100) if initial_balance > 0 else 0

    def _calculate_sharpe_ratio(
        self, current_balance: float, initial_balance: float, risk_free_rate: float
    ) -> float:
        """Calculate Sharpe ratio (simplified)."""
        if initial_balance == 0:
            return 0

        # Return
        total_return = (current_balance - initial_balance) / initial_balance

        # Excess return (annualized)
        excess_return = total_return - (risk_free_rate / 100)

        # Without historical volatility data, use a simplified approach
        # Assume 20% annual volatility (typical for crypto)
        volatility = 0.20

        sharpe_ratio = excess_return / volatility if volatility > 0 else 0

        return sharpe_ratio

    def _calculate_current_win_rate(self, positions: list) -> float:
        """Calculate current win rate from positions."""
        if not positions:
            return 0.5

        winning = len([p for p in positions if p.get("pnl", p.get("unrealized_pnl", 0)) > 0])
        return winning / len(positions)

    def _calculate_risk_of_ruin(self, win_rate: float, risk_per_trade: float) -> float:
        """Calculate risk of ruin probability."""
        if win_rate >= 0.5:
            return 0  # Low risk if win rate > 50%

        # Simplified calculation
        loss_rate = 1 - win_rate
        risk_of_ruin = (loss_rate / win_rate) ** (100 / risk_per_trade) if win_rate > 0 else 100

        return min(risk_of_ruin * 100, 100)

    def _generate_chart_data(
        self, portfolio_info: dict, trade_history: dict | None, initial_balance: float
    ) -> dict:
        """Generate data for performance visualization."""
        chart_data = {}

        # Equity curve (simplified - would need historical data)
        current_balance = portfolio_info.get("total_balance", 0)
        chart_data["equity_curve"] = [
            {"timestamp": int(time.time() * 1000) - 86400000 * 7, "balance": initial_balance},
            {"timestamp": int(time.time() * 1000), "balance": current_balance},
        ]

        # Position distribution by PnL
        positions = portfolio_info.get("positions", [])
        if positions:
            pnl_distribution = {
                "winning": len([p for p in positions if p.get("pnl", p.get("unrealized_pnl", 0)) > 0]),
                "losing": len([p for p in positions if p.get("pnl", p.get("unrealized_pnl", 0)) < 0]),
                "breakeven": len([p for p in positions if p.get("pnl", p.get("unrealized_pnl", 0)) == 0]),
            }
            chart_data["pnl_distribution"] = pnl_distribution

        # Asset allocation
        if positions:
            asset_allocation = {}
            for position in positions:
                symbol = position.get("symbol", "UNKNOWN")
                value = position.get("eval_amount", position.get("size", 0) * position.get("mark_price", 0))
                asset_allocation[symbol] = asset_allocation.get(symbol, 0) + value

            chart_data["asset_allocation"] = [
                {"symbol": k, "value": v} for k, v in asset_allocation.items()
            ]

        return chart_data

    def _generate_summary(
        self,
        current_balance: float,
        initial_balance: float,
        return_percent: float,
        win_rate: float,
        open_positions: int,
    ) -> str:
        """Generate human-readable performance summary."""
        performance_level = "EXCELLENT" if return_percent > 20 else (
            "GOOD" if return_percent > 10 else (
                "MODERATE" if return_percent > 0 else "POOR"
            )
        )

        summary = f"""
PERFORMANCE SUMMARY
==================

Overall Performance: {performance_level}
Total Return: {return_percent:+.2f}%
Current Balance: ${current_balance:,.2f}
Starting Balance: ${initial_balance:,.2f}
Profit/Loss: ${(current_balance - initial_balance):+,.2f}

Position Statistics:
- Open Positions: {open_positions}
- Win Rate: {win_rate:.1f}%

{self._get_performance_advice(return_percent, win_rate)}
"""
        return summary.strip()

    def _get_performance_advice(self, return_percent: float, win_rate: float) -> str:
        """Provide performance-based advice."""
        advice = []

        if return_percent < 0:
            advice.append("⚠️ Portfolio is in loss. Consider reviewing your strategy.")
        elif return_percent > 50:
            advice.append("✅ Excellent returns! Consider taking some profits.")

        if win_rate < 40:
            advice.append("⚠️ Win rate is low. Review entry/exit criteria.")
        elif win_rate > 70:
            advice.append("✅ Strong win rate. Keep following your strategy.")

        return "\n".join(advice) if advice else "Continue monitoring performance metrics."

    def _format_position_details(self, positions: list) -> list:
        """Format position details for the report."""
        return [
            {
                "symbol": p.get("symbol", p.get("name", "UNKNOWN")),
                "side": p.get("side", "unknown"),
                "size": p.get("size", p.get("quantity", 0)),
                "entry_price": p.get("entry_price", 0),
                "current_price": p.get("mark_price", p.get("current_price", 0)),
                "pnl": p.get("pnl", p.get("unrealized_pnl", 0)),
                "pnl_percent": p.get("pnl_rate", 0),
            }
            for p in positions
        ]

    def build(self):
        return self.generate_report
