#!/usr/bin/env python3
"""
Run batch backtests for multiple strategies, timeframes, and years.

Usage:
    python -m src.modules.crypto_trading.scripts.run_batch_backtest \
        --config data/crypto_trading/configs/batch_backtest_config.yaml

This script will:
1. Load configuration from YAML file
2. Generate all combinations of strategy x timeframe x year
3. Execute each backtest with progress tracking
4. Aggregate results and generate summary report
"""

import argparse
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from src.modules.crypto_trading.services.alpaca_client import get_historical_bars
from src.modules.crypto_trading.services.backtest import DEFAULT_TRADING_FEE_PCT, BacktestResult, run_backtest
from src.modules.crypto_trading.services.batch_analysis import aggregate_results, create_performance_heatmaps
from src.modules.crypto_trading.services.batch_report import generate_summary_report
from src.modules.crypto_trading.services.visualization import create_backtest_chart
from src.modules.crypto_trading.storage.file_storage import (
    get_batch_run_dir,
    load_batch_config,
    save_batch_config_copy,
    save_batch_errors_log,
    save_batch_result_json,
    save_batch_results_csv,
)
from src.modules.crypto_trading.strategies import get_strategy, list_strategies


def _dict_to_backtest_result(d: dict) -> BacktestResult:
    """Convert result dict back to BacktestResult for visualization."""
    return BacktestResult(
        trades=d.get("trades", []),
        total_return_pct=d.get("total_return_pct", 0.0),
        sharpe_ratio=d.get("sharpe_ratio", 0.0),
        max_drawdown=d.get("max_drawdown", 0.0),
        win_rate=d.get("win_rate", 0.0),
        total_trades=d.get("total_trades", 0),
        profit_factor=d.get("profit_factor", 0.0),
        final_capital=d.get("final_capital", 0.0),
        initial_capital=d.get("initial_capital", 0.0),
        total_fees=d.get("total_fees", 0.0),
        winning_trades=d.get("winning_trades", 0),
        losing_trades=d.get("losing_trades", 0),
        avg_win_pct=d.get("avg_win_pct", 0.0),
        avg_loss_pct=d.get("avg_loss_pct", 0.0),
        equity_curve=d.get("equity_curve", []),
        open_position=d.get("open_position"),
        unrealized_pnl=d.get("unrealized_pnl", 0.0),
        total_equity=d.get("total_equity", 0.0),
        total_equity_return_pct=d.get("total_equity_return_pct", 0.0),
    )


def calculate_warmup_start(start_date: str, timeframe: str, lookback_bars: int = 50) -> str:
    """
    Calculate the actual start date for data fetching, including warmup period.

    Args:
        start_date: User-requested start date (YYYY-MM-DD)
        timeframe: Candle timeframe (1h, 4h, 1d, etc.)
        lookback_bars: Number of bars needed for warmup

    Returns:
        Adjusted start date string (YYYY-MM-DD) that includes warmup period
    """
    from datetime import timedelta

    timeframe_hours = {
        "1m": 1 / 60,
        "5m": 5 / 60,
        "15m": 15 / 60,
        "30m": 30 / 60,
        "1h": 1,
        "4h": 4,
        "8h": 8,
        "12h": 12,
        "1d": 24,
    }

    hours_per_bar = timeframe_hours.get(timeframe, 1)
    warmup_hours = lookback_bars * hours_per_bar * 1.2  # 20% buffer

    start = datetime.strptime(start_date, "%Y-%m-%d")
    warmup_start = start - timedelta(hours=warmup_hours)

    return warmup_start.strftime("%Y-%m-%d")


def generate_date_ranges(years: list[int]) -> list[tuple[str, str, int]]:
    """
    Generate date ranges for each year.

    Args:
        years: List of years to test

    Returns:
        List of (start_date, end_date, year) tuples
    """
    today = datetime.now()
    ranges = []

    for year in years:
        start_date = f"{year}-01-01"

        if year == today.year:
            # Current year: end at today
            end_date = today.strftime("%Y-%m-%d")
        else:
            # Historical year: full year
            end_date = f"{year}-12-31"

        ranges.append((start_date, end_date, year))

    return ranges


def generate_batch_jobs(config: dict) -> list[dict]:
    """
    Generate list of backtest jobs from configuration.

    Args:
        config: Batch configuration dict

    Returns:
        List of job dicts with all parameters needed for backtest
    """
    strategies = config.get("strategies", [])
    timeframes = config.get("timeframes", ["1h"])
    years = config.get("years", [datetime.now().year])
    common = config.get("common", {})

    date_ranges = generate_date_ranges(years)
    jobs = []

    for strategy in strategies:
        strategy_name = strategy.get("name")
        strategy_params = strategy.get("params", {})

        # Validate strategy exists
        available = list_strategies()
        if strategy_name not in available:
            print(f"WARNING: Unknown strategy '{strategy_name}'. Skipping.")
            continue

        for timeframe in timeframes:
            for start_date, end_date, year in date_ranges:
                job = {
                    "job_id": f"{strategy_name}_{timeframe}_{year}",
                    "strategy_name": strategy_name,
                    "strategy_params": strategy_params,
                    "timeframe": timeframe,
                    "start_date": start_date,
                    "end_date": end_date,
                    "year": year,
                    # Common settings
                    "symbol": common.get("symbol", "BTC/USD"),
                    "initial_capital": common.get("initial_capital", 10000.0),
                    "position_size_pct": common.get("position_size_pct", 0.1),
                    "trading_fee_pct": common.get("trading_fee_pct", DEFAULT_TRADING_FEE_PCT),
                    "trading_mode": common.get("trading_mode", "long_only"),
                    "lookback_bars": common.get("lookback_bars", 50),
                    "stop_loss_pct": common.get("stop_loss_pct"),  # Risk management (disabled by default)
                }
                jobs.append(job)

    return jobs


def execute_backtest_job(job: dict, include_df: bool = False) -> dict | None:
    """
    Execute a single backtest job.

    Args:
        job: Job dict with all parameters
        include_df: If True, include DataFrame in result for chart generation

    Returns:
        Result dict with job metadata + BacktestResult, or None on failure
    """
    try:
        # Calculate warmup start date
        warmup_start = calculate_warmup_start(
            job["start_date"],
            job["timeframe"],
            job["lookback_bars"],
        )

        # Fetch historical data
        df = get_historical_bars(
            symbol=job["symbol"],
            timeframe=job["timeframe"],
            start=warmup_start,
            end=job["end_date"],
        )

        if len(df) < job["lookback_bars"] + 10:
            raise ValueError(f"Insufficient data: only {len(df)} bars loaded")

        # Get strategy function
        strategy_fn = get_strategy(job["strategy_name"])

        # Determine if bidirectional
        allow_short = job["trading_mode"] == "bidirectional"

        # Run backtest
        result = run_backtest(
            df=df,
            strategy_fn=strategy_fn,
            strategy_params=job["strategy_params"],
            initial_capital=job["initial_capital"],
            position_size_pct=job["position_size_pct"],
            trading_fee_pct=job["trading_fee_pct"],
            allow_short=allow_short,
            lookback_period=job["lookback_bars"],
            stop_loss_pct=job.get("stop_loss_pct"),
        )

        # Combine job metadata with result
        result_dict = asdict(result)
        result_dict["job_id"] = job["job_id"]
        result_dict["strategy_name"] = job["strategy_name"]
        result_dict["timeframe"] = job["timeframe"]
        result_dict["year"] = job["year"]
        result_dict["start_date"] = job["start_date"]
        result_dict["end_date"] = job["end_date"]
        result_dict["data_bars"] = len(df)

        # Optionally include DataFrame for chart generation
        if include_df:
            result_dict["_df"] = df

        return result_dict

    except Exception as e:
        # Return error info
        return {
            "job_id": job["job_id"],
            "strategy_name": job["strategy_name"],
            "timeframe": job["timeframe"],
            "year": job["year"],
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


def print_summary(results: list[dict], failed: list[dict], duration: float, batch_dir: Path) -> None:
    """Print summary to console."""
    print(f"\n{'='*60}")
    print("  BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"  Success: {len(results)}/{len(results) + len(failed)}")
    print(f"  Failed: {len(failed)}")
    print(f"  Duration: {duration/60:.1f}m {duration%60:.0f}s")
    print(f"{'='*60}")

    if not results:
        print("\n  No successful results to analyze.")
        return

    # Find best overall
    df = aggregate_results(results)
    best_idx = df["total_return_pct"].idxmax()
    best = df.loc[best_idx]

    print("\n=== TOP PERFORMERS ===\n")
    print("Best Overall:")
    print(f"  {best['strategy_name']} @ {best['timeframe']} ({int(best['year'])}): ", end="")
    print(f"{best['total_return_pct']:+.1f}% | Sharpe: {best['sharpe_ratio']:.2f}")

    # Best by year
    print("\nBest by Year:")
    years = sorted(df["year"].unique())
    for year in years:
        year_df = df[df["year"] == year]
        if len(year_df) > 0:
            best_year_idx = year_df["total_return_pct"].idxmax()
            best_year = year_df.loc[best_year_idx]
            print(f"  {int(year)}: {best_year['strategy_name']} @ {best_year['timeframe']} ({best_year['total_return_pct']:+.1f}%)")

    # Most consistent
    print("\nMost Consistent (profitable years):")
    consistency = df.groupby(["strategy_name", "timeframe"]).apply(lambda x: (x["total_return_pct"] > 0).sum() / len(x), include_groups=False).reset_index(name="consistency")
    consistency["avg_return"] = df.groupby(["strategy_name", "timeframe"])["total_return_pct"].mean().values
    consistency = consistency.sort_values(["consistency", "avg_return"], ascending=[False, False])

    for i, row in consistency.head(3).iterrows():
        profitable_years = int(row["consistency"] * len(years))
        print(f"  {i+1}. {row['strategy_name']} @ {row['timeframe']}: ", end="")
        print(f"{profitable_years}/{len(years)} years, avg {row['avg_return']:+.1f}%")

    print(f"\nResults saved to: {batch_dir}/")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run batch backtests for multiple strategies, timeframes, and years",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Path to batch config YAML file",
    )
    parser.add_argument(
        "--skip-charts",
        action="store_true",
        help="Skip generating heatmap charts",
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="Skip generating summary report",
    )

    args = parser.parse_args()

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        return 1

    config = load_batch_config(str(config_path))

    # Generate jobs
    jobs = generate_batch_jobs(config)

    if not jobs:
        print("ERROR: No valid jobs generated from config")
        return 1

    # Get counts for display
    strategies = {j["strategy_name"] for j in jobs}
    timeframes = {j["timeframe"] for j in jobs}
    years = {j["year"] for j in jobs}

    print(f"\n{'='*60}")
    print("  BATCH BACKTEST RUNNER")
    print(f"{'='*60}")
    print(f"  Config: {config_path.name}")
    print(f"  Total Jobs: {len(jobs)}")
    print(f"  Strategies: {len(strategies)}")
    print(f"  Timeframes: {len(timeframes)}")
    print(f"  Years: {len(years)}")
    print(f"{'='*60}\n")

    # Create batch run directory
    batch_dir = get_batch_run_dir()
    save_batch_config_copy(config, batch_dir)

    # Execute jobs with progress tracking
    results: list[dict] = []
    errors: list[dict] = []
    start_time = time.time()

    output_config = config.get("output", {})
    save_individual = output_config.get("save_individual_results", True)
    save_individual_charts = output_config.get("save_individual_charts", False)

    # Create charts directory if needed
    if save_individual_charts:
        charts_dir = batch_dir / "charts"
        charts_dir.mkdir(exist_ok=True)

    for job in tqdm(jobs, desc="Running backtests", unit="job"):
        result = execute_backtest_job(job, include_df=save_individual_charts)

        if result is None:
            errors.append({"job_id": job["job_id"], "error": "Unknown error"})
        elif "error" in result:
            errors.append(result)
            tqdm.write(f"  FAILED: {job['job_id']} - {result['error'][:50]}...")
        else:
            # Extract DataFrame if present (before appending to results)
            df_for_chart = result.pop("_df", None) if save_individual_charts else None

            results.append(result)

            # Save individual result if configured
            if save_individual:
                save_batch_result_json(result, batch_dir)

            # Save individual chart if configured
            if save_individual_charts and df_for_chart is not None and result.get("trades"):
                chart_path = batch_dir / "charts" / f"{result['job_id']}.png"
                bt_result = _dict_to_backtest_result(result)
                create_backtest_chart(
                    df_for_chart,
                    bt_result,
                    result["strategy_name"],
                    chart_path,
                    strategy_params=job["strategy_params"],
                    timeframe=result["timeframe"],
                    year=result["year"],
                )

            # Show progress
            tqdm.write(f"  {result['job_id']}: {result['total_return_pct']:+.1f}% | " f"Sharpe: {result['sharpe_ratio']:.2f}")

    duration = time.time() - start_time

    # Save errors if any
    if errors:
        save_batch_errors_log(errors, batch_dir)

    # Aggregate and save results
    if results:
        df = aggregate_results(results)
        save_batch_results_csv(df, batch_dir)

        # Generate heatmaps
        if not args.skip_charts:
            print("\nGenerating heatmaps...")
            create_performance_heatmaps(df, batch_dir)

        # Generate summary report
        if not args.skip_report and output_config.get("generate_summary_report", True):
            print("Generating summary report...")
            generate_summary_report(results, batch_dir)

    # Print summary
    print_summary(results, errors, duration, batch_dir)

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
