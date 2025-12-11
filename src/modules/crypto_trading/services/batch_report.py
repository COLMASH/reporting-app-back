"""Batch backtest report generation.

Generates markdown summary reports for batch backtests.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.modules.crypto_trading.services.batch_analysis import (
    aggregate_results,
    calculate_consistency_score,
    find_best_strategy_per_timeframe,
    find_best_strategy_per_year,
    find_best_timeframe_per_strategy,
)


def generate_summary_report(results: list[dict], batch_dir: Path) -> str:
    """
    Generate comprehensive markdown summary report.

    Args:
        results: List of backtest results
        batch_dir: Batch run directory

    Returns:
        Path to saved report file
    """
    df = aggregate_results(results)

    sections = [
        _generate_header(),
        _generate_executive_summary(df),
        _generate_best_per_year_section(df),
        _generate_best_per_timeframe_section(df),
        _generate_best_timeframe_per_strategy_section(df),
        _generate_consistency_section(df),
        _generate_risk_adjusted_section(df),
        _generate_open_positions_section(df),
        _generate_full_results_section(df),
        _generate_heatmap_section(),
    ]

    report = "\n\n".join(sections)

    filepath = batch_dir / "report.md"
    with open(filepath, "w") as f:
        f.write(report)

    return str(filepath)


def _generate_header() -> str:
    """Generate report header."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""# Batch Backtest Summary Report

**Generated:** {timestamp}

---"""


def _generate_executive_summary(df: pd.DataFrame) -> str:
    """Generate executive summary section."""
    total_jobs = len(df)
    strategies = df["strategy_name"].nunique()
    timeframes = df["timeframe"].nunique()
    years = df["year"].nunique()

    # Overall statistics
    avg_return = df["total_return_pct"].mean()
    avg_total_return = df["total_equity_return_pct"].mean() if "total_equity_return_pct" in df.columns else avg_return
    profitable_runs = (df["total_return_pct"] > 0).sum()
    profitable_pct = profitable_runs / total_jobs * 100
    open_positions = df["has_open_position"].sum() if "has_open_position" in df.columns else 0

    # Stop-loss info
    stop_loss_pct = df["stop_loss_pct"].iloc[0] if "stop_loss_pct" in df.columns and pd.notna(df["stop_loss_pct"].iloc[0]) else None
    total_sl_exits = int(df["stop_loss_exits"].sum()) if "stop_loss_exits" in df.columns else 0
    sl_str = f"{stop_loss_pct}%" if stop_loss_pct is not None else "Disabled"

    # Find overall best
    best_idx = df["total_return_pct"].idxmax()
    best = df.loc[best_idx]
    best_total = best.get("total_equity_return_pct", best["total_return_pct"])
    best_has_open = best.get("has_open_position", False)

    # Find overall worst
    worst_idx = df["total_return_pct"].idxmin()
    worst = df.loc[worst_idx]

    open_marker = " ⚠️" if best_has_open else ""

    return f"""## Executive Summary

| Metric | Value |
|--------|-------|
| Total Backtests | {total_jobs} |
| Strategies Tested | {strategies} |
| Timeframes Tested | {timeframes} |
| Years Tested | {years} |
| Profitable Runs | {profitable_runs} ({profitable_pct:.1f}%) |
| Avg Realized Return | {avg_return:+.2f}% |
| Avg Total Return | {avg_total_return:+.2f}% |
| Open Positions | {open_positions} runs |
| Stop-Loss | {sl_str} ({total_sl_exits} total exits) |

### Best Overall Performance{open_marker}

| Metric | Value |
|--------|-------|
| **Strategy** | {best['strategy_name']} |
| **Timeframe** | {best['timeframe']} |
| **Year** | {int(best['year'])} |
| **Realized Return** | {best['total_return_pct']:+.2f}% |
| **Total Return** | {best_total:+.2f}% |
| **Sharpe Ratio** | {best['sharpe_ratio']:.2f} |
| **Max Drawdown** | {best['max_drawdown']:.2f}% |
| **Win Rate** | {best['win_rate']:.1f}% |

### Worst Overall Performance

| Metric | Value |
|--------|-------|
| **Strategy** | {worst['strategy_name']} |
| **Timeframe** | {worst['timeframe']} |
| **Year** | {int(worst['year'])} |
| **Return** | {worst['total_return_pct']:+.2f}% |"""


def _generate_best_per_year_section(df: pd.DataFrame) -> str:
    """Generate best strategy per year section."""
    best_per_year = find_best_strategy_per_year(df)

    table = """## Best Strategy Per Year

| Year | Strategy | Timeframe | Return % | Sharpe | Max DD % | Win Rate % | Trades |
|------|----------|-----------|----------|--------|----------|------------|--------|
"""

    for _, row in best_per_year.iterrows():
        table += f"| {int(row['year'])} "
        table += f"| {row['strategy_name']} "
        table += f"| {row['timeframe']} "
        table += f"| {row['total_return_pct']:+.2f} "
        table += f"| {row['sharpe_ratio']:.2f} "
        table += f"| {row['max_drawdown']:.2f} "
        table += f"| {row['win_rate']:.1f} "
        table += f"| {int(row['total_trades'])} |\n"

    return table


def _generate_best_per_timeframe_section(df: pd.DataFrame) -> str:
    """Generate best strategy per timeframe section."""
    best_per_tf = find_best_strategy_per_timeframe(df)

    table = """## Best Strategy Per Timeframe (Averaged Across Years)

| Timeframe | Strategy | Avg Return % | Avg Sharpe | Avg Max DD % | Avg Win Rate % |
|-----------|----------|--------------|------------|--------------|----------------|
"""

    for _, row in best_per_tf.iterrows():
        table += f"| {row['timeframe']} "
        table += f"| {row['strategy_name']} "
        table += f"| {row['total_return_pct']:+.2f} "
        table += f"| {row['sharpe_ratio']:.2f} "
        table += f"| {row['max_drawdown']:.2f} "
        table += f"| {row['win_rate']:.1f} |\n"

    return table


def _generate_best_timeframe_per_strategy_section(df: pd.DataFrame) -> str:
    """Generate best timeframe per strategy section."""
    best_tf_per_strat = find_best_timeframe_per_strategy(df)

    table = """## Best Timeframe Per Strategy (Averaged Across Years)

| Strategy | Best Timeframe | Avg Return % | Avg Sharpe | Avg Max DD % |
|----------|----------------|--------------|------------|--------------|
"""

    for _, row in best_tf_per_strat.iterrows():
        table += f"| {row['strategy_name']} "
        table += f"| {row['timeframe']} "
        table += f"| {row['total_return_pct']:+.2f} "
        table += f"| {row['sharpe_ratio']:.2f} "
        table += f"| {row['max_drawdown']:.2f} |\n"

    return table


def _generate_consistency_section(df: pd.DataFrame) -> str:
    """Generate consistency rankings section."""
    consistency = calculate_consistency_score(df)

    table = """## Consistency Rankings (Profitable Years)

| Rank | Strategy | Timeframe | Profitable Years | Consistency | Avg Return % | Volatility |
|------|----------|-----------|------------------|-------------|--------------|------------|
"""

    for i, (_, row) in enumerate(consistency.head(10).iterrows(), 1):
        profitable = int(row["profitable_years"])
        total = int(row["total_years"])
        volatility = row["std_return"] if pd.notna(row["std_return"]) else 0

        table += f"| {i} "
        table += f"| {row['strategy_name']} "
        table += f"| {row['timeframe']} "
        table += f"| {profitable}/{total} "
        table += f"| {row['consistency_score']*100:.0f}% "
        table += f"| {row['avg_return']:+.2f} "
        table += f"| {volatility:.2f} |\n"

    return table


def _generate_risk_adjusted_section(df: pd.DataFrame) -> str:
    """Generate risk-adjusted rankings section (by Sharpe ratio)."""
    # Group by strategy+timeframe and average
    grouped = (
        df.groupby(["strategy_name", "timeframe"])
        .agg(
            {
                "sharpe_ratio": "mean",
                "total_return_pct": "mean",
                "max_drawdown": "mean",
                "win_rate": "mean",
            }
        )
        .reset_index()
    )

    grouped = grouped.sort_values("sharpe_ratio", ascending=False)

    table = """## Risk-Adjusted Rankings (Average Sharpe Ratio)

| Rank | Strategy | Timeframe | Avg Sharpe | Avg Return % | Avg Max DD % | Avg Win Rate % |
|------|----------|-----------|------------|--------------|--------------|----------------|
"""

    for i, (_, row) in enumerate(grouped.head(10).iterrows(), 1):
        table += f"| {i} "
        table += f"| {row['strategy_name']} "
        table += f"| {row['timeframe']} "
        table += f"| {row['sharpe_ratio']:.2f} "
        table += f"| {row['total_return_pct']:+.2f} "
        table += f"| {row['max_drawdown']:.2f} "
        table += f"| {row['win_rate']:.1f} |\n"

    return table


def _generate_full_results_section(df: pd.DataFrame) -> str:
    """Generate full results table section."""
    # Sort by return descending
    sorted_df = df.sort_values("total_return_pct", ascending=False)

    has_open_col = "has_open_position" in df.columns
    has_sl_col = "stop_loss_exits" in df.columns

    table = """## All Results (Sorted by Return)

<details>
<summary>Click to expand full results table</summary>

| Rank | Strategy | TF | Year | Realized % | Total % | Sharpe | Max DD % | Trades | SL Exits | Open |
|------|----------|-----|------|------------|---------|--------|----------|--------|----------|------|
"""

    for i, (_, row) in enumerate(sorted_df.iterrows(), 1):
        total_return = row.get("total_equity_return_pct", row["total_return_pct"])
        has_open = row.get("has_open_position", False) if has_open_col else False
        sl_exits = int(row.get("stop_loss_exits", 0)) if has_sl_col else 0
        open_marker = "⚠️" if has_open else ""

        table += f"| {i} "
        table += f"| {row['strategy_name']} "
        table += f"| {row['timeframe']} "
        table += f"| {int(row['year'])} "
        table += f"| {row['total_return_pct']:+.2f} "
        table += f"| {total_return:+.2f} "
        table += f"| {row['sharpe_ratio']:.2f} "
        table += f"| {row['max_drawdown']:.2f} "
        table += f"| {int(row['total_trades'])} "
        table += f"| {sl_exits} "
        table += f"| {open_marker} |\n"

    table += "\n</details>"

    return table


def _generate_open_positions_section(df: pd.DataFrame) -> str:
    """Generate section listing all runs with open positions."""
    if "has_open_position" not in df.columns:
        return ""

    open_df = df[df["has_open_position"] == True].copy()  # noqa: E712

    if len(open_df) == 0:
        return """## Open Positions

No backtests ended with open positions."""

    table = """## Open Positions

The following backtests ended with open positions (unrealized P&L not included in trade statistics):

| Strategy | TF | Year | Direction | Entry Price | Unrealized % | Realized → Total |
|----------|-----|------|-----------|-------------|--------------|------------------|
"""

    for _, row in open_df.iterrows():
        direction = row.get("open_position_direction", "").upper()
        entry_price = row.get("open_position_entry_price", 0.0)
        unrealized_pct = row.get("open_position_unrealized_pct", 0.0)
        realized = row["total_return_pct"]
        total = row.get("total_equity_return_pct", realized)

        table += f"| {row['strategy_name']} "
        table += f"| {row['timeframe']} "
        table += f"| {int(row['year'])} "
        table += f"| {direction} "
        table += f"| ${entry_price:,.2f} "
        table += f"| {unrealized_pct:+.2f}% "
        table += f"| {realized:+.2f}% → {total:+.2f}% |\n"

    return table


def _generate_heatmap_section() -> str:
    """Generate section referencing heatmap images."""
    return """## Executive Summary Dashboard

![Executive Summary Dashboard](dashboard_summary.png)

## Performance Heatmaps

### Average Realized Return by Strategy and Timeframe
![Return Heatmap](heatmap_return.png)

### Average Total Equity Return (Including Open Positions)
![Total Equity Heatmap](heatmap_total_equity.png)

### Average Sharpe Ratio by Strategy and Timeframe
![Sharpe Heatmap](heatmap_sharpe.png)

### Consistency (% Profitable Years) by Strategy and Timeframe
![Consistency Heatmap](heatmap_consistency.png)

### Yearly Performance Comparison
![Yearly Comparison](chart_yearly_comparison.png)"""


def generate_quick_summary(results: list[dict]) -> str:
    """
    Generate a quick text summary for console output.

    Args:
        results: List of backtest results

    Returns:
        Summary text string
    """
    if not results:
        return "No results to summarize."

    df = aggregate_results(results)

    # Best overall
    best_idx = df["total_return_pct"].idxmax()
    best = df.loc[best_idx]

    # Consistency leaders
    consistency = calculate_consistency_score(df)
    top_consistent = consistency.head(3)

    lines = [
        "\n=== BATCH BACKTEST SUMMARY ===",
        f"\nTotal runs: {len(df)}",
        f"Profitable runs: {(df['total_return_pct'] > 0).sum()} ({(df['total_return_pct'] > 0).sum()/len(df)*100:.1f}%)",
        f"\nBest Overall: {best['strategy_name']} @ {best['timeframe']} ({int(best['year'])})",
        f"  Return: {best['total_return_pct']:+.2f}% | Sharpe: {best['sharpe_ratio']:.2f}",
        "\nMost Consistent:",
    ]

    for i, (_, row) in enumerate(top_consistent.iterrows(), 1):
        profitable = int(row["profitable_years"])
        total = int(row["total_years"])
        lines.append(f"  {i}. {row['strategy_name']} @ {row['timeframe']}: " f"{profitable}/{total} profitable years (avg {row['avg_return']:+.1f}%)")

    return "\n".join(lines)
