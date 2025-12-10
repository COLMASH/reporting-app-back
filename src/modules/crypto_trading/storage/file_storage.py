"""File storage functions for crypto trading results."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.modules.crypto_trading.config import BacktestConfig, BotConfig

# Base data directory for crypto trading
DATA_DIR = Path("data/crypto_trading")


def _ensure_dir(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for datetime and other types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def save_backtest_result(result: Any, strategy_name: str, timeframe: str) -> str:
    """
    Save backtest result to JSON.

    Args:
        result: BacktestResult dataclass
        strategy_name: Name of strategy used
        timeframe: Timeframe used

    Returns:
        Path to saved file
    """
    path = DATA_DIR / "backtests"
    _ensure_dir(path)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{strategy_name}_{timeframe}_{timestamp}.json"
    filepath = path / filename

    # Convert dataclass to dict
    data = asdict(result) if hasattr(result, "__dataclass_fields__") else result

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=_json_serializer)

    return str(filepath)


def save_trades_csv(trades: list[dict], strategy_name: str, timeframe: str) -> str:
    """
    Save trades to CSV for easy analysis.

    Args:
        trades: List of trade dicts
        strategy_name: Name of strategy
        timeframe: Timeframe used

    Returns:
        Path to saved file
    """
    path = DATA_DIR / "trades"
    _ensure_dir(path)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{strategy_name}_{timeframe}_{timestamp}.csv"
    filepath = path / filename

    if trades:
        df = pd.DataFrame(trades)
        df.to_csv(filepath, index=False)
    else:
        # Create empty file with headers
        with open(filepath, "w") as f:
            f.write("entry_time,exit_time,entry_price,exit_price,pnl,pnl_pct,signal_reason\n")

    return str(filepath)


def save_chart(figure_path: str, strategy_name: str, timeframe: str) -> str:
    """
    Get chart save path.

    Args:
        figure_path: Temporary figure path (not used, just for interface)
        strategy_name: Name of strategy
        timeframe: Timeframe used

    Returns:
        Path where chart should be saved
    """
    path = DATA_DIR / "charts"
    _ensure_dir(path)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{strategy_name}_{timeframe}_{timestamp}.png"

    return str(path / filename)


def get_chart_path(strategy_name: str, timeframe: str) -> str:
    """
    Get path for saving chart.

    Args:
        strategy_name: Name of strategy
        timeframe: Timeframe used

    Returns:
        Full path for chart file
    """
    path = DATA_DIR / "charts"
    _ensure_dir(path)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{strategy_name}_{timeframe}_{timestamp}.png"

    return str(path / filename)


def load_bot_config(config_file: str) -> BotConfig:
    """
    Load bot configuration from JSON file.

    Args:
        config_file: Path to config JSON file

    Returns:
        BotConfig instance
    """
    with open(config_file) as f:
        data = json.load(f)

    return BotConfig(**data)


def load_backtest_config(config_file: str) -> BacktestConfig:
    """
    Load backtest configuration from JSON file.

    Args:
        config_file: Path to config JSON file

    Returns:
        BacktestConfig instance
    """
    with open(config_file) as f:
        data = json.load(f)

    return BacktestConfig(**data)


def save_bot_config(config: BotConfig, filename: str) -> str:
    """
    Save bot configuration to JSON file.

    Args:
        config: BotConfig instance
        filename: Name for config file

    Returns:
        Path to saved file
    """
    path = DATA_DIR / "configs"
    _ensure_dir(path)

    if not filename.endswith(".json"):
        filename = f"{filename}.json"

    filepath = path / filename

    with open(filepath, "w") as f:
        json.dump(config.model_dump(), f, indent=2)

    return str(filepath)


def log_trade(trade: dict, bot_name: str = "default") -> str:
    """
    Append trade to running trade log CSV.

    Args:
        trade: Trade details dict
        bot_name: Name/identifier for the bot

    Returns:
        Path to log file
    """
    path = DATA_DIR / "trades"
    _ensure_dir(path)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"live_trades_{bot_name}_{date_str}.csv"
    filepath = path / filename

    # Add timestamp if not present
    if "timestamp" not in trade:
        trade["timestamp"] = datetime.now().isoformat()

    df = pd.DataFrame([trade])

    # Append to existing or create new
    if filepath.exists():
        df.to_csv(filepath, mode="a", header=False, index=False)
    else:
        df.to_csv(filepath, index=False)

    return str(filepath)


def list_backtest_results() -> list[str]:
    """List all saved backtest result files."""
    path = DATA_DIR / "backtests"
    if not path.exists():
        return []

    return sorted([f.name for f in path.glob("*.json")])


def list_trade_files() -> list[str]:
    """List all saved trade CSV files."""
    path = DATA_DIR / "trades"
    if not path.exists():
        return []

    return sorted([f.name for f in path.glob("*.csv")])


def list_charts() -> list[str]:
    """List all saved chart files."""
    path = DATA_DIR / "charts"
    if not path.exists():
        return []

    return sorted([f.name for f in path.glob("*.png")])


def load_backtest_result(filename: str) -> dict:
    """
    Load a saved backtest result.

    Args:
        filename: Name of the file (in backtests directory)

    Returns:
        Backtest result dict
    """
    filepath = DATA_DIR / "backtests" / filename

    with open(filepath) as f:
        result: dict = json.load(f)
        return result
