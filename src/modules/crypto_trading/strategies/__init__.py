from collections.abc import Callable

import pandas as pd

from src.modules.crypto_trading.strategies.adx import adx_signal
from src.modules.crypto_trading.strategies.base import Signal as Signal
from src.modules.crypto_trading.strategies.base import TradeSignal
from src.modules.crypto_trading.strategies.bollinger import bollinger_signal
from src.modules.crypto_trading.strategies.macd import macd_signal
from src.modules.crypto_trading.strategies.rsi import rsi_signal
from src.modules.crypto_trading.strategies.sma_crossover import sma_crossover_signal
from src.modules.crypto_trading.strategies.stochastic import stochastic_signal

STRATEGY_REGISTRY: dict[str, Callable[[pd.DataFrame], TradeSignal]] = {
    "sma_crossover": sma_crossover_signal,
    "rsi": rsi_signal,
    "macd": macd_signal,
    "bollinger": bollinger_signal,
    "stochastic": stochastic_signal,
    "adx": adx_signal,
}


def get_strategy(name: str) -> Callable[[pd.DataFrame], TradeSignal]:
    """Get strategy function by name."""
    if name not in STRATEGY_REGISTRY:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy: {name}. Available: {available}")
    return STRATEGY_REGISTRY[name]


def list_strategies() -> list[str]:
    """List all available strategy names."""
    return list(STRATEGY_REGISTRY.keys())
