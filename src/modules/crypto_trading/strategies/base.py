"""Base types for trading strategies."""

from typing import Literal, TypedDict

# Signal type
Signal = Literal["buy", "sell", "hold"]


class TradeSignal(TypedDict):
    """Signal returned by strategy functions."""

    signal: Signal
    reason: str
    confidence: float  # 0.0 to 1.0
