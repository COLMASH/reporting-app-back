"""SMA/EMA Crossover Strategy.

Buy when fast MA crosses above slow MA (bullish crossover).
Sell when fast MA crosses below slow MA (bearish crossover).
"""

import pandas as pd

from src.modules.crypto_trading.services.indicators import calculate_ema, calculate_sma
from src.modules.crypto_trading.strategies.base import TradeSignal


def sma_crossover_signal(
    df: pd.DataFrame,
    fast_period: int = 10,
    slow_period: int = 20,
    use_ema: bool = False,
) -> TradeSignal:
    """
    Generate signal based on moving average crossover.

    Args:
        df: OHLCV DataFrame with 'close' column
        fast_period: Period for fast moving average
        slow_period: Period for slow moving average
        use_ema: Use EMA instead of SMA

    Returns:
        TradeSignal with signal, reason, and confidence
    """
    if len(df) < slow_period + 2:
        return TradeSignal(
            signal="hold",
            reason=f"Insufficient data (need {slow_period + 2} bars)",
            confidence=0.0,
        )

    close = df["close"]

    # Calculate moving averages
    if use_ema:
        fast_ma = calculate_ema(close, fast_period)
        slow_ma = calculate_ema(close, slow_period)
        ma_type = "EMA"
    else:
        fast_ma = calculate_sma(close, fast_period)
        slow_ma = calculate_sma(close, slow_period)
        ma_type = "SMA"

    # Current and previous values
    fast_current = fast_ma.iloc[-1]
    fast_prev = fast_ma.iloc[-2]
    slow_current = slow_ma.iloc[-1]
    slow_prev = slow_ma.iloc[-2]

    # Check for crossover
    # Bullish: fast crosses above slow
    if fast_current > slow_current and fast_prev <= slow_prev:
        # Calculate confidence based on crossover strength
        spread_pct = abs(fast_current - slow_current) / slow_current * 100
        confidence = min(0.5 + spread_pct * 0.1, 0.9)

        return TradeSignal(
            signal="buy",
            reason=f"Bullish crossover: {ma_type}({fast_period}) crossed above {ma_type}({slow_period})",
            confidence=confidence,
        )

    # Bearish: fast crosses below slow
    if fast_current < slow_current and fast_prev >= slow_prev:
        spread_pct = abs(slow_current - fast_current) / slow_current * 100
        confidence = min(0.5 + spread_pct * 0.1, 0.9)

        return TradeSignal(
            signal="sell",
            reason=f"Bearish crossover: {ma_type}({fast_period}) crossed below {ma_type}({slow_period})",
            confidence=confidence,
        )

    # No crossover - determine trend
    if fast_current > slow_current:
        trend = "bullish"
    else:
        trend = "bearish"

    return TradeSignal(
        signal="hold",
        reason=f"No crossover, trend is {trend}",
        confidence=0.5,
    )
