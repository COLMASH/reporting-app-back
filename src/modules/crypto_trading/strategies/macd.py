"""MACD (Moving Average Convergence Divergence) Strategy.

Buy when MACD line crosses above signal line (bullish).
Sell when MACD line crosses below signal line (bearish).
"""

import pandas as pd

from src.modules.crypto_trading.services.indicators import calculate_macd
from src.modules.crypto_trading.strategies.base import TradeSignal


def macd_signal(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> TradeSignal:
    """
    Generate signal based on MACD crossover.

    Args:
        df: OHLCV DataFrame with 'close' column
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line period (default 9)

    Returns:
        TradeSignal with signal, reason, and confidence
    """
    min_periods = slow_period + signal_period + 2

    if len(df) < min_periods:
        return TradeSignal(
            signal="hold",
            reason=f"Insufficient data (need {min_periods} bars)",
            confidence=0.0,
        )

    close = df["close"]
    macd_line, signal_line, histogram = calculate_macd(close, fast_period, slow_period, signal_period)

    current_macd = macd_line.iloc[-1]
    prev_macd = macd_line.iloc[-2]
    current_signal = signal_line.iloc[-1]
    prev_signal = signal_line.iloc[-2]
    current_hist = histogram.iloc[-1]

    # Bullish crossover: MACD crosses above signal
    if current_macd > current_signal and prev_macd <= prev_signal:
        # Confidence based on histogram strength
        confidence = min(0.5 + abs(current_hist) * 0.001, 0.9)

        return TradeSignal(
            signal="buy",
            reason=f"MACD bullish crossover: MACD({current_macd:.2f}) > Signal({current_signal:.2f})",
            confidence=confidence,
        )

    # Bearish crossover: MACD crosses below signal
    if current_macd < current_signal and prev_macd >= prev_signal:
        confidence = min(0.5 + abs(current_hist) * 0.001, 0.9)

        return TradeSignal(
            signal="sell",
            reason=f"MACD bearish crossover: MACD({current_macd:.2f}) < Signal({current_signal:.2f})",
            confidence=confidence,
        )

    # Determine trend from histogram
    if current_hist > 0:
        trend = "bullish"
    else:
        trend = "bearish"

    return TradeSignal(
        signal="hold",
        reason=f"No MACD crossover, histogram is {trend} ({current_hist:.2f})",
        confidence=0.5,
    )
