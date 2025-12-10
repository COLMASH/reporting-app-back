"""Visualization functions for backtest results.

Creates charts with candlesticks, buy/sell signals, and performance metrics.
"""


import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

from src.modules.crypto_trading.services.backtest import BacktestResult
from src.modules.crypto_trading.services.indicators import (
    calculate_adx,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_stochastic,
)

# Strategy categories for chart layout
OVERLAY_STRATEGIES = {"sma_crossover", "bollinger"}
PANEL_STRATEGIES = {"rsi", "macd", "stochastic", "adx"}


def _get_chart_layout(strategy_name: str) -> tuple[int, list[float]]:
    """
    Get dynamic chart layout based on strategy type.

    Overlay strategies (sma_crossover, bollinger): 3 rows [price, equity, returns]
    Panel strategies (rsi, macd, stochastic, adx): 4 rows [price, indicator, equity, returns]

    Args:
        strategy_name: Name of the trading strategy

    Returns:
        Tuple of (num_rows, height_ratios)
    """
    if strategy_name in OVERLAY_STRATEGIES:
        return 3, [3, 1, 1]
    elif strategy_name in PANEL_STRATEGIES:
        return 4, [3, 1.2, 1, 1]
    else:
        return 3, [3, 1, 1]  # default for unknown strategies


def _plot_sma_indicators(ax: plt.Axes, df: pd.DataFrame, params: dict) -> None:
    """Plot Fast/Slow MA lines on price chart."""
    close = df["close"]
    fast_period = params.get("fast_period", 10)
    slow_period = params.get("slow_period", 20)
    use_ema = params.get("use_ema", False)

    if use_ema:
        fast_ma = calculate_ema(close, fast_period)
        slow_ma = calculate_ema(close, slow_period)
        ma_type = "EMA"
    else:
        fast_ma = calculate_sma(close, fast_period)
        slow_ma = calculate_sma(close, slow_period)
        ma_type = "SMA"

    ax.plot(
        df.index, fast_ma, color="#FF9800", linewidth=1.5,
        label=f"Fast {ma_type}({fast_period})", alpha=0.9
    )
    ax.plot(
        df.index, slow_ma, color="#9C27B0", linewidth=1.5,
        label=f"Slow {ma_type}({slow_period})", alpha=0.9
    )


def _plot_bollinger_indicators(ax: plt.Axes, df: pd.DataFrame, params: dict) -> None:
    """Plot Bollinger Bands on price chart."""
    close = df["close"]
    period = params.get("period", 20)
    std_dev = params.get("std_dev", 2.0)

    upper, middle, lower = calculate_bollinger_bands(close, period, std_dev)

    # Plot bands
    ax.plot(
        df.index, upper, color="#78909C", linewidth=1, linestyle="--",
        label=f"Upper Band ({std_dev}σ)", alpha=0.7
    )
    ax.plot(
        df.index, middle, color="#78909C", linewidth=1.5,
        label=f"SMA({period})", alpha=0.9
    )
    ax.plot(
        df.index, lower, color="#78909C", linewidth=1, linestyle="--",
        label=f"Lower Band ({std_dev}σ)", alpha=0.7
    )

    # Fill between bands
    ax.fill_between(df.index, lower, upper, color="#90CAF9", alpha=0.15)


def _plot_rsi_panel(ax: plt.Axes, df: pd.DataFrame, params: dict) -> None:
    """Plot RSI indicator in separate panel."""
    close = df["close"]
    period = params.get("period", 14)
    oversold = params.get("oversold", 30)
    overbought = params.get("overbought", 70)

    rsi = calculate_rsi(close, period)

    # Plot RSI line
    ax.plot(df.index, rsi, color="#673AB7", linewidth=1.5, label=f"RSI({period})")

    # Plot threshold lines
    ax.axhline(y=overbought, color="#F44336", linestyle="--", linewidth=1, alpha=0.7)
    ax.axhline(y=oversold, color="#4CAF50", linestyle="--", linewidth=1, alpha=0.7)
    ax.axhline(y=50, color="gray", linestyle="-", linewidth=0.5, alpha=0.5)

    # Fill overbought/oversold zones
    ax.fill_between(df.index, overbought, 100, color="#FFCDD2", alpha=0.3)
    ax.fill_between(df.index, 0, oversold, color="#C8E6C9", alpha=0.3)

    ax.set_ylim(0, 100)
    ax.set_ylabel("RSI", fontsize=10)
    ax.set_title(f"RSI({period}) - Overbought: {overbought}, Oversold: {oversold}", fontsize=10)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))


def _plot_macd_panel(ax: plt.Axes, df: pd.DataFrame, params: dict) -> None:
    """Plot MACD indicator in separate panel."""
    close = df["close"]
    fast = params.get("fast_period", 12)
    slow = params.get("slow_period", 26)
    signal = params.get("signal_period", 9)

    macd_line, signal_line, histogram = calculate_macd(close, fast, slow, signal)

    # Plot histogram as bars - need to handle bar width for datetime index
    bar_width = (df.index[1] - df.index[0]) * 0.8 if len(df) > 1 else 1
    colors = ["#4CAF50" if h >= 0 else "#F44336" for h in histogram]
    ax.bar(df.index, histogram, color=colors, alpha=0.6, width=bar_width, label="Histogram")

    # Plot MACD and Signal lines
    ax.plot(df.index, macd_line, color="#2196F3", linewidth=1.5, label=f"MACD({fast},{slow})")
    ax.plot(df.index, signal_line, color="#FF9800", linewidth=1.5, label=f"Signal({signal})")

    # Zero line
    ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)

    ax.set_ylabel("MACD", fontsize=10)
    ax.set_title(f"MACD({fast},{slow},{signal})", fontsize=10)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))


def _plot_stochastic_panel(ax: plt.Axes, df: pd.DataFrame, params: dict) -> None:
    """Plot Stochastic Oscillator in separate panel."""
    k_period = params.get("k_period", 14)
    d_period = params.get("d_period", 3)
    oversold = params.get("oversold", 20)
    overbought = params.get("overbought", 80)

    k, d = calculate_stochastic(df["high"], df["low"], df["close"], k_period, d_period)

    # Plot %K and %D
    ax.plot(df.index, k, color="#2196F3", linewidth=1.5, label=f"%K({k_period})")
    ax.plot(df.index, d, color="#FF5722", linewidth=1.5, label=f"%D({d_period})")

    # Threshold lines
    ax.axhline(y=overbought, color="#F44336", linestyle="--", linewidth=1, alpha=0.7)
    ax.axhline(y=oversold, color="#4CAF50", linestyle="--", linewidth=1, alpha=0.7)

    # Fill zones
    ax.fill_between(df.index, overbought, 100, color="#FFCDD2", alpha=0.3)
    ax.fill_between(df.index, 0, oversold, color="#C8E6C9", alpha=0.3)

    ax.set_ylim(0, 100)
    ax.set_ylabel("Stochastic", fontsize=10)
    ax.set_title(f"Stochastic(%K={k_period}, %D={d_period})", fontsize=10)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))


def _plot_adx_panel(ax: plt.Axes, df: pd.DataFrame, params: dict) -> None:
    """Plot ADX with +DI/-DI in separate panel."""
    period = params.get("period", 14)
    threshold = params.get("adx_threshold", 25)

    adx, plus_di, minus_di = calculate_adx(df["high"], df["low"], df["close"], period)

    # Plot ADX and DI lines
    ax.plot(df.index, adx, color="#673AB7", linewidth=2, label=f"ADX({period})")
    ax.plot(df.index, plus_di, color="#4CAF50", linewidth=1.5, label="+DI", alpha=0.8)
    ax.plot(df.index, minus_di, color="#F44336", linewidth=1.5, label="-DI", alpha=0.8)

    # Threshold line
    ax.axhline(
        y=threshold, color="#FF9800", linestyle="--", linewidth=1,
        label=f"Threshold ({threshold})", alpha=0.7
    )

    # Fill weak trend zone
    ax.fill_between(df.index, 0, threshold, color="#FFF3E0", alpha=0.3)

    ax.set_ylim(0, 60)
    ax.set_ylabel("ADX/DI", fontsize=10)
    ax.set_title(f"ADX({period}) with Directional Indicators", fontsize=10)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))


def _plot_strategy_indicators(
    ax_price: plt.Axes,
    ax_indicator: plt.Axes | None,
    df: pd.DataFrame,
    strategy_name: str,
    params: dict,
) -> None:
    """
    Plot indicators based on strategy type.

    Args:
        ax_price: Price chart axes (for overlay indicators)
        ax_indicator: Separate indicator panel axes (None for overlay strategies)
        df: OHLCV DataFrame
        strategy_name: Name of strategy
        params: Strategy parameters
    """
    if strategy_name == "sma_crossover":
        _plot_sma_indicators(ax_price, df, params)
    elif strategy_name == "bollinger":
        _plot_bollinger_indicators(ax_price, df, params)
    elif strategy_name == "rsi" and ax_indicator is not None:
        _plot_rsi_panel(ax_indicator, df, params)
    elif strategy_name == "macd" and ax_indicator is not None:
        _plot_macd_panel(ax_indicator, df, params)
    elif strategy_name == "stochastic" and ax_indicator is not None:
        _plot_stochastic_panel(ax_indicator, df, params)
    elif strategy_name == "adx" and ax_indicator is not None:
        _plot_adx_panel(ax_indicator, df, params)


def create_backtest_chart(
    df: pd.DataFrame,
    result: BacktestResult,
    strategy_name: str,
    output_path: str,
    strategy_params: dict | None = None,
    show_indicators: bool = True,
) -> str:
    """
    Create comprehensive backtest visualization.

    Shows:
    - Price chart with buy/sell signals
    - Strategy indicators (overlay or separate panel)
    - Entry/exit arrows with return annotations
    - Equity curve
    - Performance summary

    Args:
        df: OHLCV DataFrame with datetime index
        result: BacktestResult from backtest
        strategy_name: Name of strategy for title
        output_path: Where to save the chart
        strategy_params: Strategy parameters for indicator plotting
        show_indicators: Whether to show strategy indicators

    Returns:
        Path to saved chart
    """
    # Get dynamic layout based on strategy
    num_rows, height_ratios = _get_chart_layout(strategy_name)
    needs_indicator_panel = num_rows == 4

    # Create figure with dynamic subplots
    fig_height = 14 if needs_indicator_panel else 12
    fig, axes = plt.subplots(num_rows, 1, figsize=(16, fig_height), height_ratios=height_ratios)
    fig.suptitle(f"Backtest Results: {strategy_name.upper()}", fontsize=14, fontweight="bold")

    # Assign axes based on layout
    ax_price = axes[0]
    if needs_indicator_panel:
        ax_indicator = axes[1]
        ax_equity = axes[2]
        ax_returns = axes[3]
    else:
        ax_indicator = None
        ax_equity = axes[1]
        ax_returns = axes[2]

    # Plot price chart with signals
    _plot_price_with_signals(ax_price, df, result.trades)

    # Plot strategy indicators
    if show_indicators and strategy_params is not None:
        _plot_strategy_indicators(ax_price, ax_indicator, df, strategy_name, strategy_params)

    # Update price chart legend after indicators are added
    ax_price.legend(loc="upper left", fontsize=8)

    # Plot equity curve
    _plot_equity_curve(ax_equity, result.equity_curve, result.initial_capital)

    # Plot trade returns
    _plot_trade_returns(ax_returns, result.trades)

    # Add performance summary text
    _add_summary_box(fig, result, strategy_name)

    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(top=0.92, right=0.85)

    # Save figure
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return output_path


def _plot_price_with_signals(ax: plt.Axes, df: pd.DataFrame, trades: list[dict]) -> None:
    """Plot price chart with buy/sell signals."""
    # Plot price as line chart (simpler than candlesticks for clarity)
    ax.plot(df.index, df["close"], color="#2196F3", linewidth=1, label="Price", alpha=0.8)

    # Fill between high and low for visual range
    ax.fill_between(df.index, df["low"], df["high"], alpha=0.1, color="#2196F3")

    # Check if we have any short trades
    has_short_trades = any(t.get("direction") == "short" for t in trades)

    # Plot entry signals (differentiate LONG vs SHORT)
    for trade in trades:
        entry_time = trade["entry_time"]
        entry_price = trade["entry_price"]
        direction = trade.get("direction", "long")

        if isinstance(entry_time, str):
            entry_time = pd.Timestamp(entry_time)

        # LONG entry: green up arrow, SHORT entry: orange down arrow
        if direction == "long":
            entry_color = "#4CAF50"  # Green
            entry_marker = "^"
            arrow_offset = entry_price * 0.98
        else:
            entry_color = "#FF9800"  # Orange for short
            entry_marker = "v"
            arrow_offset = entry_price * 1.02

        ax.annotate(
            "",
            xy=(entry_time, entry_price),
            xytext=(entry_time, arrow_offset),
            arrowprops={"arrowstyle": "->", "color": entry_color, "lw": 2},
        )
        ax.scatter([entry_time], [entry_price], color=entry_color, s=100, marker=entry_marker, zorder=5, label="_nolegend_")

    # Plot exit signals (red for all exits)
    for trade in trades:
        exit_time = trade["exit_time"]
        exit_price = trade["exit_price"]
        pnl_pct = trade["pnl_pct"]
        direction = trade.get("direction", "long")

        if isinstance(exit_time, str):
            exit_time = pd.Timestamp(exit_time)

        # Exit marker: opposite of entry direction
        if direction == "long":
            exit_marker = "v"
            arrow_offset = exit_price * 1.02
        else:
            exit_marker = "^"
            arrow_offset = exit_price * 0.98

        ax.annotate(
            "",
            xy=(exit_time, exit_price),
            xytext=(exit_time, arrow_offset),
            arrowprops={"arrowstyle": "->", "color": "#F44336", "lw": 2},
        )
        ax.scatter([exit_time], [exit_price], color="#F44336", s=100, marker=exit_marker, zorder=5, label="_nolegend_")

        # Add return annotation
        color = "#4CAF50" if pnl_pct > 0 else "#F44336"
        ax.annotate(
            f"{pnl_pct:+.1f}%",
            xy=(exit_time, exit_price),
            xytext=(5, 10),
            textcoords="offset points",
            fontsize=8,
            color=color,
            fontweight="bold",
        )

    # Connect entry to exit with dashed lines
    for trade in trades:
        entry_time = trade["entry_time"]
        exit_time = trade["exit_time"]
        entry_price = trade["entry_price"]
        exit_price = trade["exit_price"]

        if isinstance(entry_time, str):
            entry_time = pd.Timestamp(entry_time)
        if isinstance(exit_time, str):
            exit_time = pd.Timestamp(exit_time)

        color = "#4CAF50" if trade["pnl"] > 0 else "#F44336"
        ax.plot([entry_time, exit_time], [entry_price, exit_price], color=color, linestyle="--", alpha=0.5, linewidth=1)

    ax.set_ylabel("Price (USD)", fontsize=10)
    ax.set_title("Price Chart with Trade Signals", fontsize=11)
    ax.grid(True, alpha=0.3)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    # Legend - include short entry if applicable
    long_patch = mpatches.Patch(color="#4CAF50", label="Long Entry")
    exit_patch = mpatches.Patch(color="#F44336", label="Exit")
    if has_short_trades:
        short_patch = mpatches.Patch(color="#FF9800", label="Short Entry")
        ax.legend(handles=[long_patch, short_patch, exit_patch], loc="upper left")
    else:
        ax.legend(handles=[long_patch, exit_patch], loc="upper left")


def _plot_equity_curve(ax: plt.Axes, equity_curve: list[dict], initial_capital: float) -> None:
    """Plot equity curve over time."""
    if not equity_curve:
        ax.text(0.5, 0.5, "No equity data", ha="center", va="center", transform=ax.transAxes)
        return

    times = [p["time"] for p in equity_curve]
    equities = [p["equity"] for p in equity_curve]

    # Plot equity
    ax.plot(times, equities, color="#673AB7", linewidth=1.5, label="Portfolio Value")

    # Add initial capital reference line
    ax.axhline(y=initial_capital, color="gray", linestyle="--", alpha=0.5, label="Initial Capital")

    # Fill green/red based on profit/loss
    ax.fill_between(
        times,
        initial_capital,
        equities,
        where=[e >= initial_capital for e in equities],
        color="#4CAF50",
        alpha=0.3,
    )
    ax.fill_between(
        times,
        initial_capital,
        equities,
        where=[e < initial_capital for e in equities],
        color="#F44336",
        alpha=0.3,
    )

    ax.set_ylabel("Portfolio Value (USD)", fontsize=10)
    ax.set_title("Equity Curve", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))


def _plot_trade_returns(ax: plt.Axes, trades: list[dict]) -> None:
    """Plot individual trade returns as bar chart."""
    if not trades:
        ax.text(0.5, 0.5, "No trades", ha="center", va="center", transform=ax.transAxes)
        return

    trade_nums = list(range(1, len(trades) + 1))
    returns = [t["pnl_pct"] for t in trades]
    colors = ["#4CAF50" if r > 0 else "#F44336" for r in returns]

    ax.bar(trade_nums, returns, color=colors, alpha=0.7, edgecolor="black", linewidth=0.5)

    # Add zero line
    ax.axhline(y=0, color="black", linewidth=0.5)

    ax.set_xlabel("Trade Number", fontsize=10)
    ax.set_ylabel("Return (%)", fontsize=10)
    ax.set_title("Individual Trade Returns", fontsize=11)
    ax.grid(True, alpha=0.3, axis="y")


def _add_summary_box(fig: plt.Figure, result: BacktestResult, strategy_name: str) -> None:
    """Add performance summary text box."""
    # Build trade breakdown string
    trade_breakdown = f"Total Trades: {result.total_trades}"
    if result.trading_mode == "bidirectional":
        trade_breakdown += f"\nLong: {result.long_trades} | Short: {result.short_trades}"

    # Build mode string
    mode_str = "Long+Short" if result.trading_mode == "bidirectional" else "Long Only"

    summary_text = f"""Performance Summary
─────────────────
Strategy: {strategy_name}
Mode: {mode_str}
Initial Capital: ${result.initial_capital:,.0f}
Final Capital: ${result.final_capital:,.0f}

Total Return: {result.total_return_pct:+.2f}%
Max Drawdown: {result.max_drawdown:.2f}%
Sharpe Ratio: {result.sharpe_ratio:.2f}

{trade_breakdown}
Win Rate: {result.win_rate:.1f}%
Winners: {result.winning_trades}
Losers: {result.losing_trades}

Avg Win: {result.avg_win_pct:+.2f}%
Avg Loss: {result.avg_loss_pct:.2f}%
Profit Factor: {result.profit_factor:.2f}"""

    # Add text box on right side
    fig.text(
        0.88,
        0.5,
        summary_text,
        transform=fig.transFigure,
        fontsize=9,
        verticalalignment="center",
        fontfamily="monospace",
        bbox={"boxstyle": "round", "facecolor": "white", "edgecolor": "gray", "alpha": 0.9},
    )


def create_simple_chart(
    df: pd.DataFrame,
    trades: list[dict],
    strategy_name: str,
    output_path: str,
) -> str:
    """
    Create a simple price chart with trade markers.

    Lighter version without equity curve and detailed metrics.

    Args:
        df: OHLCV DataFrame
        trades: List of trade dicts
        strategy_name: Strategy name for title
        output_path: Where to save

    Returns:
        Path to saved chart
    """
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot price
    ax.plot(df.index, df["close"], color="#2196F3", linewidth=1.2, label="BTC/USD")

    # Plot trades
    for trade in trades:
        entry_time = trade["entry_time"]
        exit_time = trade["exit_time"]
        entry_price = trade["entry_price"]
        exit_price = trade["exit_price"]
        pnl_pct = trade["pnl_pct"]

        if isinstance(entry_time, str):
            entry_time = pd.Timestamp(entry_time)
        if isinstance(exit_time, str):
            exit_time = pd.Timestamp(exit_time)

        # Buy marker
        ax.scatter([entry_time], [entry_price], color="#4CAF50", s=150, marker="^", zorder=5)

        # Sell marker
        ax.scatter([exit_time], [exit_price], color="#F44336", s=150, marker="v", zorder=5)

        # Return label
        color = "#4CAF50" if pnl_pct > 0 else "#F44336"
        ax.annotate(
            f"{pnl_pct:+.1f}%",
            xy=(exit_time, exit_price),
            xytext=(5, -15),
            textcoords="offset points",
            fontsize=9,
            color=color,
            fontweight="bold",
        )

    ax.set_title(f"BTC/USD - {strategy_name} Strategy", fontsize=12, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price (USD)")
    ax.grid(True, alpha=0.3)

    # Legend
    buy_marker = plt.scatter([], [], color="#4CAF50", marker="^", s=100, label="Buy")
    sell_marker = plt.scatter([], [], color="#F44336", marker="v", s=100, label="Sell")
    ax.legend(handles=[buy_marker, sell_marker], loc="upper left")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return output_path
