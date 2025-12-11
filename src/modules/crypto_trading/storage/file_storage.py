"""File storage functions for crypto trading results."""

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

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


# =============================================================================
# Single Backtest Run Storage Functions
# =============================================================================


def get_single_run_dir(strategy_name: str, timeframe: str, timestamp: str | None = None) -> Path:
    """
    Get or create directory for a single backtest run.

    Each individual run gets its own folder containing result.json, trades.csv, and chart.png.

    Args:
        strategy_name: Name of strategy
        timeframe: Timeframe used
        timestamp: Optional timestamp string, defaults to now

    Returns:
        Path to run directory
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    run_id = f"{strategy_name}_{timeframe}_{timestamp}"
    run_dir = DATA_DIR / "single_results" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Update "latest" symlink
    latest = DATA_DIR / "single_results" / "latest"
    if latest.is_symlink():
        latest.unlink()
    elif latest.exists():
        latest.unlink()
    latest.symlink_to(run_id)

    return run_dir


def save_backtest_result(result: Any, strategy_name: str, timeframe: str, run_dir: Path | None = None) -> str:
    """
    Save backtest result to JSON.

    Args:
        result: BacktestResult dataclass
        strategy_name: Name of strategy used
        timeframe: Timeframe used
        run_dir: Optional run directory (creates new one if not provided)

    Returns:
        Path to saved file
    """
    if run_dir is None:
        run_dir = get_single_run_dir(strategy_name, timeframe)

    filepath = run_dir / "result.json"

    # Convert dataclass to dict
    data = asdict(result) if hasattr(result, "__dataclass_fields__") else result

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=_json_serializer)

    return str(filepath)


def save_trades_csv(trades: list[dict], strategy_name: str, timeframe: str, run_dir: Path | None = None) -> str:
    """
    Save trades to CSV for easy analysis.

    Args:
        trades: List of trade dicts
        strategy_name: Name of strategy
        timeframe: Timeframe used
        run_dir: Optional run directory (creates new one if not provided)

    Returns:
        Path to saved file
    """
    if run_dir is None:
        run_dir = get_single_run_dir(strategy_name, timeframe)

    filepath = run_dir / "trades.csv"

    if trades:
        df = pd.DataFrame(trades)
        df.to_csv(filepath, index=False)
    else:
        # Create empty file with headers
        with open(filepath, "w") as f:
            f.write("entry_time,exit_time,entry_price,exit_price,pnl,pnl_pct,signal_reason\n")

    return str(filepath)


def get_chart_path(strategy_name: str, timeframe: str, run_dir: Path | None = None) -> str:
    """
    Get path for saving chart.

    Args:
        strategy_name: Name of strategy
        timeframe: Timeframe used
        run_dir: Optional run directory (creates new one if not provided)

    Returns:
        Full path for chart file
    """
    if run_dir is None:
        run_dir = get_single_run_dir(strategy_name, timeframe)

    return str(run_dir / "chart.png")


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
    """List all saved backtest run directories."""
    path = DATA_DIR / "single_results"
    if not path.exists():
        return []

    return sorted([d.name for d in path.iterdir() if d.is_dir() and d.name != "latest"])


def list_trade_files() -> list[str]:
    """List all run directories that have trades.csv."""
    path = DATA_DIR / "single_results"
    if not path.exists():
        return []

    return sorted([d.name for d in path.iterdir() if d.is_dir() and d.name != "latest" and (d / "trades.csv").exists()])


def list_charts() -> list[str]:
    """List all run directories that have chart.png."""
    path = DATA_DIR / "single_results"
    if not path.exists():
        return []

    return sorted([d.name for d in path.iterdir() if d.is_dir() and d.name != "latest" and (d / "chart.png").exists()])


def load_backtest_result(run_id: str) -> dict:
    """
    Load a saved backtest result by run ID.

    Args:
        run_id: Name of the run directory (e.g., "bollinger_4h_2025-12-10_17-27-38")

    Returns:
        Backtest result dict
    """
    filepath = DATA_DIR / "single_results" / run_id / "result.json"

    with open(filepath) as f:
        result: dict = json.load(f)
        return result


# =============================================================================
# Batch Backtest Storage Functions
# =============================================================================


def get_batch_run_dir(timestamp: str | None = None) -> Path:
    """
    Get or create batch run directory.

    Args:
        timestamp: Optional timestamp string, defaults to now

    Returns:
        Path to batch run directory
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    batch_dir = DATA_DIR / "batch_results" / f"batch_{timestamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    # Create/update symlink to latest
    latest = DATA_DIR / "batch_results" / "latest"
    if latest.is_symlink():
        latest.unlink()
    elif latest.exists():
        # If it's a regular file/dir, remove it
        if latest.is_dir():
            os.rmdir(latest)
        else:
            latest.unlink()

    # Create relative symlink
    latest.symlink_to(batch_dir.name)

    return batch_dir


def load_batch_config(config_path: str) -> dict:
    """
    Load batch backtest configuration from YAML file.

    Args:
        config_path: Path to config YAML file

    Returns:
        Configuration dict
    """
    with open(config_path) as f:
        config: dict = yaml.safe_load(f)
        return config


def save_batch_config_copy(config: dict, batch_dir: Path) -> str:
    """
    Save a copy of the batch config to the batch run directory.

    Args:
        config: Configuration dict
        batch_dir: Batch run directory

    Returns:
        Path to saved file
    """
    filepath = batch_dir / "config.yaml"

    with open(filepath, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    return str(filepath)


def save_batch_results_csv(df: "pd.DataFrame", batch_dir: Path) -> str:
    """
    Save aggregated batch results to CSV.

    Args:
        df: DataFrame with all backtest results
        batch_dir: Batch run directory

    Returns:
        Path to saved file
    """
    filepath = batch_dir / "results_summary.csv"
    df.to_csv(filepath, index=False)
    return str(filepath)


def save_batch_result_json(result: dict, batch_dir: Path) -> str:
    """
    Save individual batch backtest result to JSON.

    Args:
        result: Result dict with job metadata + BacktestResult
        batch_dir: Batch run directory

    Returns:
        Path to saved file
    """
    job_id = result.get("job_id", "unknown")
    filepath = batch_dir / "individual_results" / f"{job_id}.json"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w") as f:
        json.dump(result, f, indent=2, default=_json_serializer)

    return str(filepath)


def save_batch_errors_log(errors: list[dict], batch_dir: Path) -> str:
    """
    Save error log for failed jobs.

    Args:
        errors: List of error dicts with job info and error message
        batch_dir: Batch run directory

    Returns:
        Path to saved file
    """
    filepath = batch_dir / "errors.log"

    with open(filepath, "w") as f:
        for error in errors:
            f.write(f"[{error.get('job_id', 'unknown')}] {error.get('error', 'Unknown error')}\n")
            if "traceback" in error:
                f.write(f"  Traceback: {error['traceback']}\n")
            f.write("\n")

    return str(filepath)
