"""ADX (Average Directional Index) Strategy.

Uses ADX for trend strength and +DI/-DI for direction.
Buy when +DI crosses above -DI with strong ADX.
Sell when -DI crosses above +DI with strong ADX.
"""

import pandas as pd

from src.modules.crypto_trading.services.indicators import calculate_adx
from src.modules.crypto_trading.strategies.base import TradeSignal


def adx_signal(
    df: pd.DataFrame,
    period: int = 14,
    adx_threshold: float = 25.0,
) -> TradeSignal:
    """
    Generate signal based on ADX and directional indicators.

    Args:
        df: OHLCV DataFrame with 'high', 'low', 'close' columns
        period: ADX calculation period
        adx_threshold: Minimum ADX for valid signals (trend strength)

    Returns:
        TradeSignal with signal, reason, and confidence
    """
    min_periods = period * 2 + 2

    if len(df) < min_periods:
        return TradeSignal(
            signal="hold",
            reason=f"Insufficient data (need {min_periods} bars)",
            confidence=0.0,
        )

    adx, plus_di, minus_di = calculate_adx(df["high"], df["low"], df["close"], period)

    current_adx = adx.iloc[-1]
    current_plus = plus_di.iloc[-1]
    prev_plus = plus_di.iloc[-2]
    current_minus = minus_di.iloc[-1]
    prev_minus = minus_di.iloc[-2]

    # Check if trend is strong enough
    if current_adx < adx_threshold:
        return TradeSignal(
            signal="hold",
            reason=f"Weak trend: ADX({current_adx:.1f}) < {adx_threshold}",
            confidence=0.3,
        )

    # Buy signal: +DI crosses above -DI with strong trend
    if current_plus > current_minus and prev_plus <= prev_minus:
        # Confidence based on ADX strength
        confidence = min(0.5 + (current_adx - adx_threshold) * 0.01, 0.9)

        return TradeSignal(
            signal="buy",
            reason=f"Bullish DI crossover: +DI({current_plus:.1f}) > -DI({current_minus:.1f}), ADX={current_adx:.1f}",
            confidence=confidence,
        )

    # Sell signal: -DI crosses above +DI with strong trend
    if current_minus > current_plus and prev_minus <= prev_plus:
        confidence = min(0.5 + (current_adx - adx_threshold) * 0.01, 0.9)

        return TradeSignal(
            signal="sell",
            reason=f"Bearish DI crossover: -DI({current_minus:.1f}) > +DI({current_plus:.1f}), ADX={current_adx:.1f}",
            confidence=confidence,
        )

    # Determine current trend direction
    if current_plus > current_minus:
        direction = "bullish"
    else:
        direction = "bearish"

    return TradeSignal(
        signal="hold",
        reason=f"Strong {direction} trend (ADX={current_adx:.1f}), no DI crossover",
        confidence=0.5,
    )
