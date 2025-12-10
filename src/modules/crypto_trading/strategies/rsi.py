"""RSI (Relative Strength Index) Strategy.

Buy when RSI crosses above oversold level (bullish reversal).
Sell when RSI crosses below overbought level (bearish reversal).
"""

import pandas as pd

from src.modules.crypto_trading.services.indicators import calculate_rsi
from src.modules.crypto_trading.strategies.base import TradeSignal


def rsi_signal(
    df: pd.DataFrame,
    period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> TradeSignal:
    """
    Generate signal based on RSI levels.

    Args:
        df: OHLCV DataFrame with 'close' column
        period: RSI calculation period
        oversold: Oversold threshold (default 30)
        overbought: Overbought threshold (default 70)

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
    rsi = calculate_rsi(close, period)

    current_rsi = rsi.iloc[-1]
    prev_rsi = rsi.iloc[-2]

    # Buy signal: RSI crosses above oversold level
    if current_rsi > oversold and prev_rsi <= oversold:
        # Confidence based on how deep into oversold we were
        confidence = min(0.5 + (oversold - prev_rsi) * 0.02, 0.9)

        return TradeSignal(
            signal="buy",
            reason=f"RSI({period}) crossed above {oversold} (oversold exit): {current_rsi:.1f}",
            confidence=confidence,
        )

    # Sell signal: RSI crosses below overbought level
    if current_rsi < overbought and prev_rsi >= overbought:
        confidence = min(0.5 + (prev_rsi - overbought) * 0.02, 0.9)

        return TradeSignal(
            signal="sell",
            reason=f"RSI({period}) crossed below {overbought} (overbought exit): {current_rsi:.1f}",
            confidence=confidence,
        )

    # Determine current state
    if current_rsi < oversold:
        state = f"oversold ({current_rsi:.1f})"
    elif current_rsi > overbought:
        state = f"overbought ({current_rsi:.1f})"
    else:
        state = f"neutral ({current_rsi:.1f})"

    return TradeSignal(
        signal="hold",
        reason=f"RSI is {state}, waiting for crossover",
        confidence=0.5,
    )
