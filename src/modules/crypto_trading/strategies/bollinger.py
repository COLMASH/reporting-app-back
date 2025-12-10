"""Bollinger Bands Strategy.

Buy when price touches/breaks below lower band (potential reversal).
Sell when price touches/breaks above upper band (potential reversal).
"""

import pandas as pd

from src.modules.crypto_trading.services.indicators import calculate_bollinger_bands
from src.modules.crypto_trading.strategies.base import TradeSignal


def bollinger_signal(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
) -> TradeSignal:
    """
    Generate signal based on Bollinger Bands.

    Args:
        df: OHLCV DataFrame with 'close' column
        period: SMA period for middle band
        std_dev: Standard deviation multiplier for bands

    Returns:
        TradeSignal with signal, reason, and confidence
    """
    if len(df) < period + 2:
        return TradeSignal(
            signal="hold",
            reason=f"Insufficient data (need {period + 2} bars)",
            confidence=0.0,
        )

    close = df["close"]
    upper, middle, lower = calculate_bollinger_bands(close, period, std_dev)

    current_price = close.iloc[-1]
    prev_price = close.iloc[-2]
    current_upper = upper.iloc[-1]
    current_lower = lower.iloc[-1]
    prev_lower = lower.iloc[-2]
    prev_upper = upper.iloc[-2]

    # Calculate bandwidth percentage (volatility)
    bandwidth = (current_upper - current_lower) / middle.iloc[-1] * 100

    # Buy signal: Price bounces from lower band
    # Price was at/below lower band and now moving up
    if prev_price <= prev_lower and current_price > current_lower:
        # Confidence based on how far below band we went
        overshoot = (prev_lower - prev_price) / prev_lower * 100
        confidence = min(0.5 + overshoot * 0.5, 0.85)

        return TradeSignal(
            signal="buy",
            reason=f"Price bounced from lower band ({current_lower:.2f}), bandwidth: {bandwidth:.1f}%",
            confidence=confidence,
        )

    # Sell signal: Price bounces from upper band
    # Price was at/above upper band and now moving down
    if prev_price >= prev_upper and current_price < current_upper:
        overshoot = (prev_price - prev_upper) / prev_upper * 100
        confidence = min(0.5 + overshoot * 0.5, 0.85)

        return TradeSignal(
            signal="sell",
            reason=f"Price bounced from upper band ({current_upper:.2f}), bandwidth: {bandwidth:.1f}%",
            confidence=confidence,
        )

    # Determine position relative to bands
    if current_price < current_lower:
        position = "below lower band (oversold)"
    elif current_price > current_upper:
        position = "above upper band (overbought)"
    elif current_price > middle.iloc[-1]:
        position = "above middle band"
    else:
        position = "below middle band"

    return TradeSignal(
        signal="hold",
        reason=f"Price is {position}, bandwidth: {bandwidth:.1f}%",
        confidence=0.5,
    )
