"""Configuration schemas for crypto trading module."""

from typing import Any

from pydantic import BaseModel, Field


class AlpacaConfig(BaseModel):
    """Alpaca API configuration."""

    api_key: str
    secret_key: str
    paper: bool = Field(default=True, description="Always default to paper trading")


class StrategyParams(BaseModel):
    """Strategy configuration with name and parameters."""

    name: str = Field(description="Strategy name: sma_crossover, rsi, macd, bollinger, stochastic, adx")
    params: dict[str, Any] = Field(default_factory=dict, description="Strategy-specific parameters")


class BotConfig(BaseModel):
    """Trading bot configuration."""

    symbol: str = Field(default="BTC/USD", description="Trading pair")
    timeframe: str = Field(default="1h", description="Candle timeframe: 1m, 5m, 15m, 1h, 4h, 1d")
    strategy: StrategyParams
    position_size_usd: float | None = Field(default=None, description="Fixed USD amount per trade")
    position_size_pct: float | None = Field(default=None, description="Position size as fraction of equity (0.1 = 10%)")


class BacktestConfig(BaseModel):
    """Backtesting configuration."""

    symbol: str = Field(default="BTC/USD", description="Trading pair")
    timeframe: str = Field(default="1h", description="Candle timeframe")
    start_date: str = Field(description="Start date YYYY-MM-DD")
    end_date: str | None = Field(default=None, description="End date YYYY-MM-DD (None = today)")
    initial_capital: float = Field(default=10000.0, description="Starting capital in USD")
    position_size_pct: float = Field(default=0.1, description="Position size as fraction of capital (0.1 = 10%)")
    strategy: StrategyParams


# Timeframe mappings for Alpaca API and polling intervals
TIMEFRAME_MAP = {
    "1m": {"minutes": 1, "seconds": 60},
    "5m": {"minutes": 5, "seconds": 300},
    "15m": {"minutes": 15, "seconds": 900},
    "30m": {"minutes": 30, "seconds": 1800},
    "1h": {"minutes": 60, "seconds": 3600},
    "4h": {"minutes": 240, "seconds": 14400},
    "8h": {"minutes": 480, "seconds": 28800},
    "12h": {"minutes": 720, "seconds": 43200},
    "1d": {"minutes": 1440, "seconds": 86400},
}


def timeframe_to_seconds(timeframe: str) -> int:
    """Convert timeframe string to seconds for polling interval."""
    if timeframe not in TIMEFRAME_MAP:
        available = ", ".join(TIMEFRAME_MAP.keys())
        raise ValueError(f"Invalid timeframe: {timeframe}. Available: {available}")
    return TIMEFRAME_MAP[timeframe]["seconds"]


def timeframe_to_minutes(timeframe: str) -> int:
    """Convert timeframe string to minutes for Alpaca API."""
    if timeframe not in TIMEFRAME_MAP:
        available = ", ".join(TIMEFRAME_MAP.keys())
        raise ValueError(f"Invalid timeframe: {timeframe}. Available: {available}")
    return TIMEFRAME_MAP[timeframe]["minutes"]
