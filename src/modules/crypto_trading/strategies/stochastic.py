"""Stochastic Oscillator Strategy.

Buy when %K crosses above %D in oversold zone.
Sell when %K crosses below %D in overbought zone.
"""

import pandas as pd

from src.modules.crypto_trading.services.indicators import calculate_stochastic
from src.modules.crypto_trading.strategies.base import TradeSignal


def stochastic_signal(
    df: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
    oversold: float = 20.0,
    overbought: float = 80.0,
) -> TradeSignal:
    """
    Generate signal based on Stochastic Oscillator.

    Args:
        df: OHLCV DataFrame with 'high', 'low', 'close' columns
        k_period: %K period
        d_period: %D smoothing period
        oversold: Oversold threshold
        overbought: Overbought threshold

    Returns:
        TradeSignal with signal, reason, and confidence
    """
    min_periods = k_period + d_period + 2

    if len(df) < min_periods:
        return TradeSignal(
            signal="hold",
            reason=f"Insufficient data (need {min_periods} bars)",
            confidence=0.0,
        )

    k, d = calculate_stochastic(df["high"], df["low"], df["close"], k_period, d_period)

    current_k = k.iloc[-1]
    prev_k = k.iloc[-2]
    current_d = d.iloc[-1]
    prev_d = d.iloc[-2]

    # Buy signal: %K crosses above %D in oversold zone
    if current_k > current_d and prev_k <= prev_d and current_k < oversold + 10:
        # Stronger signal if deeper in oversold
        confidence = min(0.5 + (oversold - min(current_k, prev_k)) * 0.02, 0.85)

        return TradeSignal(
            signal="buy",
            reason=f"Stochastic bullish crossover in oversold zone: %K({current_k:.1f}) > %D({current_d:.1f})",
            confidence=confidence,
        )

    # Sell signal: %K crosses below %D in overbought zone
    if current_k < current_d and prev_k >= prev_d and current_k > overbought - 10:
        confidence = min(0.5 + (max(current_k, prev_k) - overbought) * 0.02, 0.85)

        return TradeSignal(
            signal="sell",
            reason=f"Stochastic bearish crossover in overbought zone: %K({current_k:.1f}) < %D({current_d:.1f})",
            confidence=confidence,
        )

    # Determine current state
    if current_k < oversold:
        state = f"oversold (%K={current_k:.1f})"
    elif current_k > overbought:
        state = f"overbought (%K={current_k:.1f})"
    else:
        state = f"neutral (%K={current_k:.1f})"

    return TradeSignal(
        signal="hold",
        reason=f"Stochastic is {state}, waiting for crossover in extreme zone",
        confidence=0.5,
    )
