"""Backtesting engine for trading strategies.

Simulates strategy execution on historical data.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from src.modules.crypto_trading.strategies.base import TradeSignal


@dataclass
class Trade:
    """Represents a completed trade."""

    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float
    entry_reason: str
    exit_reason: str


# Alpaca crypto trading fees
# See: https://docs.alpaca.markets/docs/crypto-trading
#
# Fee tiers (30-day volume < $100K):
#   - Taker fee (market orders): 25 bps = 0.25%
#   - Maker fee (limit orders): 15 bps = 0.15%
#
# Fees are charged on the asset you receive from the trade.
# We use taker fee as default since backtest simulates market orders.
DEFAULT_TAKER_FEE_PCT = 0.25  # 25 bps - for market orders
DEFAULT_MAKER_FEE_PCT = 0.15  # 15 bps - for limit orders
DEFAULT_TRADING_FEE_PCT = DEFAULT_TAKER_FEE_PCT  # Default to taker (market orders)


@dataclass
class BacktestResult:
    """Results from a backtest run."""

    trades: list[dict] = field(default_factory=list)
    total_return_pct: float = 0.0  # Return from closed trades only (realized)
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    profit_factor: float = 0.0
    initial_capital: float = 0.0
    final_capital: float = 0.0  # Capital after closed trades (realized)
    equity_curve: list[dict] = field(default_factory=list)
    total_fees: float = 0.0
    fee_pct_used: float = DEFAULT_TRADING_FEE_PCT
    trading_mode: str = "long_only"  # "long_only" or "bidirectional"
    long_trades: int = 0
    short_trades: int = 0

    # Total metrics (including open position)
    total_equity: float = 0.0  # final_capital + unrealized_pnl
    total_equity_return_pct: float = 0.0  # Return if we closed everything now

    # Open position tracking (position still open at end of backtest)
    open_position: dict | None = None
    unrealized_pnl: float = 0.0

    # Risk management settings
    stop_loss_pct: float | None = None  # Stop-loss % used (None if disabled)
    stop_loss_exits: int = 0  # Count of trades exited via stop-loss


def run_backtest(
    df: pd.DataFrame,
    strategy_fn: Callable[[pd.DataFrame, Any], TradeSignal],
    strategy_params: dict[str, Any],
    initial_capital: float = 10000.0,
    position_size_pct: float = 0.1,
    lookback_period: int = 50,
    trading_fee_pct: float = DEFAULT_TRADING_FEE_PCT,
    allow_short: bool = False,
    stop_loss_pct: float | None = None,
) -> BacktestResult:
    """
    Run a backtest simulation.

    Args:
        df: OHLCV DataFrame with datetime index
        strategy_fn: Strategy function that returns TradeSignal
        strategy_params: Parameters to pass to strategy function
        initial_capital: Starting capital in USD
        position_size_pct: Position size as fraction of capital (0.1 = 10%)
        lookback_period: Bars needed before starting trades
        trading_fee_pct: Trading fee percentage per trade (default 0.25% for Alpaca crypto)
        allow_short: Enable bidirectional trading (LONG + SHORT). Default: LONG only
        stop_loss_pct: Stop-loss percentage (e.g., 7.0 for 7% below entry). None = disabled

    Returns:
        BacktestResult with trades and performance metrics
    """
    trades: list[dict] = []
    equity_curve: list[dict] = []

    capital = initial_capital
    position: dict | None = None  # None = flat, {"direction": "long"|"short", ...}
    peak_capital = initial_capital
    total_fees = 0.0
    trading_mode = "bidirectional" if allow_short else "long_only"

    # Fee multiplier (e.g., 0.25% = 0.0025)
    fee_rate = trading_fee_pct / 100

    def _open_position(direction: str, price: float, reason: str) -> dict:
        """Helper to open a new position."""
        nonlocal capital, total_fees
        trade_capital = capital * position_size_pct
        entry_fee = trade_capital * fee_rate
        trade_capital_after_fee = trade_capital - entry_fee
        size = trade_capital_after_fee / price
        total_fees += entry_fee
        return {
            "direction": direction,
            "entry_time": current_time,
            "entry_price": price,
            "size": size,
            "entry_reason": reason,
            "entry_fee": entry_fee,
        }

    def _close_position(pos: dict, price: float, reason: str, exit_type: str = "signal") -> None:
        """Helper to close a position and record the trade.

        Args:
            pos: Position dict
            price: Exit price
            reason: Exit reason description
            exit_type: "signal" for strategy exit, "stop_loss" for SL exit
        """
        nonlocal capital, total_fees
        exit_value = price * pos["size"]
        exit_fee = exit_value * fee_rate
        total_fees += exit_fee

        # PnL calculation depends on direction
        if pos["direction"] == "long":
            gross_pnl = (price - pos["entry_price"]) * pos["size"]
        else:  # short
            gross_pnl = (pos["entry_price"] - price) * pos["size"]

        net_pnl = gross_pnl - pos["entry_fee"] - exit_fee
        pnl_pct = (net_pnl / (pos["entry_price"] * pos["size"])) * 100

        trades.append(
            {
                "direction": pos["direction"],
                "entry_time": pos["entry_time"],
                "exit_time": current_time,
                "entry_price": pos["entry_price"],
                "exit_price": price,
                "size": pos["size"],
                "gross_pnl": gross_pnl,
                "entry_fee": pos["entry_fee"],
                "exit_fee": exit_fee,
                "total_fees": pos["entry_fee"] + exit_fee,
                "pnl": net_pnl,
                "pnl_pct": pnl_pct,
                "entry_reason": pos["entry_reason"],
                "exit_reason": reason,
                "exit_type": exit_type,  # "signal" or "stop_loss"
            }
        )
        capital += net_pnl

    # Iterate through bars
    for i in range(lookback_period, len(df)):
        # Get data window up to current bar
        window = df.iloc[: i + 1]
        current_bar = df.iloc[i]
        current_time = df.index[i]
        current_price = current_bar["close"]

        # Check stop-loss BEFORE strategy signals (takes priority)
        if position is not None and stop_loss_pct is not None:
            entry_price = position["entry_price"]

            if position["direction"] == "long":
                stop_price = entry_price * (1 - stop_loss_pct / 100)
                # Check if bar's low touched stop price (realistic fill)
                if current_bar["low"] <= stop_price:
                    _close_position(position, stop_price, f"Stop-loss hit at {stop_loss_pct}%", exit_type="stop_loss")
                    position = None
                    # Skip strategy signal for this bar - we're now flat
                    # Continue to equity tracking below

            else:  # short position
                stop_price = entry_price * (1 + stop_loss_pct / 100)
                # Check if bar's high touched stop price
                if current_bar["high"] >= stop_price:
                    _close_position(position, stop_price, f"Stop-loss hit at {stop_loss_pct}%", exit_type="stop_loss")
                    position = None
                    # Skip strategy signal for this bar

        # Get strategy signal
        signal = strategy_fn(window, **strategy_params)  # type: ignore[call-arg]

        # LONG ONLY MODE (default behavior)
        if not allow_short:
            if signal["signal"] == "buy" and position is None:
                position = _open_position("long", current_price, signal["reason"])

            elif signal["signal"] == "sell" and position is not None:
                _close_position(position, current_price, signal["reason"])
                position = None

        # BIDIRECTIONAL MODE
        else:
            if signal["signal"] == "buy":
                # Close SHORT if exists
                if position is not None and position["direction"] == "short":
                    _close_position(position, current_price, signal["reason"])
                    position = None

                # Open LONG if flat
                if position is None:
                    position = _open_position("long", current_price, signal["reason"])

            elif signal["signal"] == "sell":
                # Close LONG if exists
                if position is not None and position["direction"] == "long":
                    _close_position(position, current_price, signal["reason"])
                    position = None

                # Open SHORT if flat
                if position is None:
                    position = _open_position("short", current_price, signal["reason"])

        # Track equity curve
        unrealized_pnl = 0.0
        if position is not None:
            potential_exit_fee = current_price * position["size"] * fee_rate
            if position["direction"] == "long":
                gross_unrealized = (current_price - position["entry_price"]) * position["size"]
            else:  # short
                gross_unrealized = (position["entry_price"] - current_price) * position["size"]
            unrealized_pnl = gross_unrealized - position["entry_fee"] - potential_exit_fee

        current_equity = capital + unrealized_pnl

        equity_curve.append(
            {
                "time": current_time,
                "equity": current_equity,
                "capital": capital,
                "unrealized_pnl": unrealized_pnl,
            }
        )

        # Track peak for drawdown
        if current_equity > peak_capital:
            peak_capital = current_equity

    # Track open position (don't force close - it would skew statistics)
    open_position_result = None
    final_unrealized_pnl = 0.0

    if position is not None:
        last_bar = df.iloc[-1]
        current_price = last_bar["close"]

        # Calculate unrealized P&L (what we'd get if we closed now)
        potential_exit_fee = current_price * position["size"] * fee_rate
        if position["direction"] == "long":
            gross_unrealized = (current_price - position["entry_price"]) * position["size"]
        else:  # short
            gross_unrealized = (position["entry_price"] - current_price) * position["size"]

        final_unrealized_pnl = gross_unrealized - position["entry_fee"] - potential_exit_fee

        # Store open position details for reporting
        open_position_result = {
            "direction": position["direction"],
            "entry_time": position["entry_time"],
            "entry_price": position["entry_price"],
            "current_price": current_price,
            "size": position["size"],
            "entry_reason": position["entry_reason"],
            "unrealized_pnl": final_unrealized_pnl,
            "unrealized_pnl_pct": (final_unrealized_pnl / (position["entry_price"] * position["size"])) * 100,
        }

    # Calculate metrics (pass open position info)
    result = _calculate_metrics(
        trades,
        equity_curve,
        initial_capital,
        capital,  # Realized capital only
        total_fees,
        trading_fee_pct,
        trading_mode,
        open_position_result,
        final_unrealized_pnl,
        stop_loss_pct,
    )

    return result


def _calculate_metrics(
    trades: list[dict],
    equity_curve: list[dict],
    initial_capital: float,
    final_capital: float,
    total_fees: float = 0.0,
    fee_pct_used: float = DEFAULT_TRADING_FEE_PCT,
    trading_mode: str = "long_only",
    open_position: dict | None = None,
    unrealized_pnl: float = 0.0,
    stop_loss_pct: float | None = None,
) -> BacktestResult:
    """Calculate performance metrics from trades."""
    # Calculate total equity (realized + unrealized)
    total_equity = final_capital + unrealized_pnl
    total_equity_return_pct = ((total_equity / initial_capital) - 1) * 100 if initial_capital > 0 else 0.0

    # Count stop-loss exits
    stop_loss_exits = len([t for t in trades if t.get("exit_type") == "stop_loss"])

    if not trades:
        return BacktestResult(
            trades=[],
            total_return_pct=0.0,
            win_rate=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            avg_win_pct=0.0,
            avg_loss_pct=0.0,
            profit_factor=0.0,
            initial_capital=initial_capital,
            final_capital=final_capital,
            equity_curve=equity_curve,
            total_fees=total_fees,
            fee_pct_used=fee_pct_used,
            trading_mode=trading_mode,
            long_trades=0,
            short_trades=0,
            total_equity=total_equity,
            total_equity_return_pct=total_equity_return_pct,
            open_position=open_position,
            unrealized_pnl=unrealized_pnl,
            stop_loss_pct=stop_loss_pct,
            stop_loss_exits=0,
        )

    # Separate winning and losing trades
    winners = [t for t in trades if t["pnl"] > 0]
    losers = [t for t in trades if t["pnl"] <= 0]

    total_trades = len(trades)
    winning_trades = len(winners)
    losing_trades = len(losers)

    # Count long vs short trades
    long_trades = len([t for t in trades if t.get("direction", "long") == "long"])
    short_trades = len([t for t in trades if t.get("direction") == "short"])

    # Win rate
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    # Average win/loss percentages
    avg_win_pct = sum(t["pnl_pct"] for t in winners) / winning_trades if winners else 0.0
    avg_loss_pct = sum(t["pnl_pct"] for t in losers) / losing_trades if losers else 0.0

    # Profit factor
    total_wins = sum(t["pnl"] for t in winners)
    total_losses = abs(sum(t["pnl"] for t in losers))
    profit_factor = total_wins / total_losses if total_losses > 0 else float("inf")

    # Total return
    total_return_pct = ((final_capital / initial_capital) - 1) * 100

    # Max drawdown
    max_drawdown = _calculate_max_drawdown(equity_curve)

    # Sharpe ratio (simplified - assumes daily returns, 0% risk-free rate)
    sharpe_ratio = _calculate_sharpe_ratio(equity_curve)

    return BacktestResult(
        trades=trades,
        total_return_pct=total_return_pct,
        win_rate=win_rate,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        profit_factor=profit_factor,
        initial_capital=initial_capital,
        final_capital=final_capital,
        equity_curve=equity_curve,
        total_fees=total_fees,
        fee_pct_used=fee_pct_used,
        trading_mode=trading_mode,
        long_trades=long_trades,
        short_trades=short_trades,
        total_equity=total_equity,
        total_equity_return_pct=total_equity_return_pct,
        open_position=open_position,
        unrealized_pnl=unrealized_pnl,
        stop_loss_pct=stop_loss_pct,
        stop_loss_exits=stop_loss_exits,
    )


def _calculate_max_drawdown(equity_curve: list[dict]) -> float:
    """Calculate maximum drawdown percentage."""
    if not equity_curve:
        return 0.0

    peak = equity_curve[0]["equity"]
    max_dd = 0.0

    for point in equity_curve:
        equity = point["equity"]
        if equity > peak:
            peak = equity

        drawdown = (peak - equity) / peak * 100
        if drawdown > max_dd:
            max_dd = drawdown

    return max_dd


def _calculate_sharpe_ratio(equity_curve: list[dict], risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio from equity curve."""
    if len(equity_curve) < 2:
        return 0.0

    # Calculate returns
    equities = [p["equity"] for p in equity_curve]
    returns = []

    for i in range(1, len(equities)):
        ret = (equities[i] / equities[i - 1]) - 1
        returns.append(ret)

    if not returns:
        return 0.0

    # Mean and std of returns
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    std_return = variance**0.5

    if std_return == 0:
        return 0.0

    # Annualized (assuming 252 trading days)
    sharpe = (mean_return - risk_free_rate) / std_return * (252**0.5)

    return float(sharpe)
