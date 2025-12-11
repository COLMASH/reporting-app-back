"""Batch backtest analysis functions.

Aggregates results and generates visualizations for batch backtests.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def aggregate_results(results: list[dict]) -> pd.DataFrame:
    """
    Aggregate all backtest results into a DataFrame.

    Args:
        results: List of result dicts from batch execution

    Returns:
        DataFrame with key metrics for analysis
    """
    rows = []
    for result in results:
        # Get open position info
        open_position = result.get("open_position")
        has_open = open_position is not None

        row = {
            "job_id": result.get("job_id"),
            "strategy_name": result.get("strategy_name"),
            "timeframe": result.get("timeframe"),
            "year": result.get("year"),
            # Realized return (closed trades only)
            "total_return_pct": result.get("total_return_pct", 0.0),
            "sharpe_ratio": result.get("sharpe_ratio", 0.0),
            "max_drawdown": result.get("max_drawdown", 0.0),
            "win_rate": result.get("win_rate", 0.0),
            "total_trades": result.get("total_trades", 0),
            "profit_factor": result.get("profit_factor", 0.0),
            "final_capital": result.get("final_capital", 0.0),
            "initial_capital": result.get("initial_capital", 0.0),
            "total_fees": result.get("total_fees", 0.0),
            "winning_trades": result.get("winning_trades", 0),
            "losing_trades": result.get("losing_trades", 0),
            "avg_win_pct": result.get("avg_win_pct", 0.0),
            "avg_loss_pct": result.get("avg_loss_pct", 0.0),
            # Total equity (including unrealized from open position)
            "has_open_position": has_open,
            "total_equity": result.get("total_equity", result.get("final_capital", 0.0)),
            "total_equity_return_pct": result.get("total_equity_return_pct", result.get("total_return_pct", 0.0)),
            "unrealized_pnl": result.get("unrealized_pnl", 0.0),
            # Open position details (empty strings if no position)
            "open_position_direction": open_position.get("direction", "") if open_position else "",
            "open_position_entry_price": open_position.get("entry_price", 0.0) if open_position else 0.0,
            "open_position_unrealized_pct": open_position.get("unrealized_pnl_pct", 0.0) if open_position else 0.0,
            # Risk management
            "stop_loss_pct": result.get("stop_loss_pct"),  # None if disabled
            "stop_loss_exits": result.get("stop_loss_exits", 0),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Calculate additional metrics
    if len(df) > 0:
        # Risk-adjusted return (return / max_drawdown)
        df["risk_adjusted_return"] = df.apply(
            lambda x: x["total_return_pct"] / x["max_drawdown"] if x["max_drawdown"] > 0 else 0,
            axis=1,
        )

    return df


def find_best_strategy_per_year(df: pd.DataFrame) -> pd.DataFrame:
    """
    Find best performing strategy for each year.

    Args:
        df: Aggregated results DataFrame

    Returns:
        DataFrame with best strategy per year
    """
    idx = df.groupby("year")["total_return_pct"].idxmax()
    return df.loc[idx].sort_values("year")


def find_best_strategy_per_timeframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Find best performing strategy for each timeframe (averaged across years).

    Args:
        df: Aggregated results DataFrame

    Returns:
        DataFrame with best strategy per timeframe
    """
    # Group by strategy and timeframe, calculate mean metrics
    grouped = (
        df.groupby(["strategy_name", "timeframe"])
        .agg(
            {
                "total_return_pct": "mean",
                "sharpe_ratio": "mean",
                "max_drawdown": "mean",
                "win_rate": "mean",
                "total_trades": "sum",
            }
        )
        .reset_index()
    )

    # Find best strategy per timeframe
    idx = grouped.groupby("timeframe")["total_return_pct"].idxmax()
    return grouped.loc[idx].sort_values("timeframe")


def find_best_timeframe_per_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Find best timeframe for each strategy (averaged across years).

    Args:
        df: Aggregated results DataFrame

    Returns:
        DataFrame with best timeframe per strategy
    """
    # Group by strategy and timeframe, calculate mean metrics
    grouped = (
        df.groupby(["strategy_name", "timeframe"])
        .agg(
            {
                "total_return_pct": "mean",
                "sharpe_ratio": "mean",
                "max_drawdown": "mean",
                "win_rate": "mean",
                "total_trades": "sum",
            }
        )
        .reset_index()
    )

    # Find best timeframe per strategy
    idx = grouped.groupby("strategy_name")["total_return_pct"].idxmax()
    return grouped.loc[idx].sort_values("strategy_name")


def calculate_consistency_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate consistency score for each strategy+timeframe combination.

    Consistency = (number of profitable years) / (total years tested)

    Args:
        df: Aggregated results DataFrame

    Returns:
        DataFrame with consistency scores
    """

    def calc_consistency(group: pd.DataFrame) -> pd.Series:
        profitable_years = (group["total_return_pct"] > 0).sum()
        return pd.Series(
            {
                "profitable_years": profitable_years,
                "total_years": len(group),
                "consistency_score": profitable_years / len(group) if len(group) > 0 else 0,
                "avg_return": group["total_return_pct"].mean(),
                "std_return": group["total_return_pct"].std(),
                "avg_sharpe": group["sharpe_ratio"].mean(),
                "avg_max_drawdown": group["max_drawdown"].mean(),
            }
        )

    consistency = df.groupby(["strategy_name", "timeframe"]).apply(calc_consistency, include_groups=False).reset_index()

    return consistency.sort_values(["consistency_score", "avg_return"], ascending=[False, False])


def create_return_heatmap(df: pd.DataFrame, output_path: Path) -> None:
    """
    Create heatmap showing average return by strategy and timeframe.

    Args:
        df: Aggregated results DataFrame
        output_path: Path to save the PNG
    """
    # Pivot table: strategies vs timeframes
    pivot = df.pivot_table(
        values="total_return_pct",
        index="strategy_name",
        columns="timeframe",
        aggfunc="mean",
    )

    # Order columns by timeframe
    timeframe_order = ["1h", "4h", "8h", "12h", "1d"]
    available_cols = [t for t in timeframe_order if t in pivot.columns]
    pivot = pivot[available_cols]

    # Create figure
    plt.figure(figsize=(10, 6))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".1f",
        cmap="RdYlGn",
        center=0,
        linewidths=0.5,
        cbar_kws={"label": "Avg Return (%)"},
    )

    plt.title("Average Return (%) by Strategy and Timeframe", fontsize=14, fontweight="bold")
    plt.xlabel("Timeframe", fontsize=12)
    plt.ylabel("Strategy", fontsize=12)
    plt.tight_layout()

    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def create_sharpe_heatmap(df: pd.DataFrame, output_path: Path) -> None:
    """
    Create heatmap showing average Sharpe ratio by strategy and timeframe.

    Args:
        df: Aggregated results DataFrame
        output_path: Path to save the PNG
    """
    # Pivot table: strategies vs timeframes
    pivot = df.pivot_table(
        values="sharpe_ratio",
        index="strategy_name",
        columns="timeframe",
        aggfunc="mean",
    )

    # Order columns by timeframe
    timeframe_order = ["1h", "4h", "8h", "12h", "1d"]
    available_cols = [t for t in timeframe_order if t in pivot.columns]
    pivot = pivot[available_cols]

    # Create figure
    plt.figure(figsize=(10, 6))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".2f",
        cmap="RdYlGn",
        center=0,
        linewidths=0.5,
        cbar_kws={"label": "Avg Sharpe Ratio"},
    )

    plt.title("Average Sharpe Ratio by Strategy and Timeframe", fontsize=14, fontweight="bold")
    plt.xlabel("Timeframe", fontsize=12)
    plt.ylabel("Strategy", fontsize=12)
    plt.tight_layout()

    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def create_consistency_heatmap(df: pd.DataFrame, output_path: Path) -> None:
    """
    Create heatmap showing consistency (% profitable years) by strategy and timeframe.

    Args:
        df: Aggregated results DataFrame
        output_path: Path to save the PNG
    """
    # Calculate consistency per strategy+timeframe
    consistency = (
        df.groupby(["strategy_name", "timeframe"]).apply(lambda x: (x["total_return_pct"] > 0).sum() / len(x) * 100, include_groups=False).reset_index(name="consistency_pct")
    )

    # Pivot table
    pivot = consistency.pivot_table(
        values="consistency_pct",
        index="strategy_name",
        columns="timeframe",
    )

    # Order columns by timeframe
    timeframe_order = ["1h", "4h", "8h", "12h", "1d"]
    available_cols = [t for t in timeframe_order if t in pivot.columns]
    pivot = pivot[available_cols]

    # Create figure
    plt.figure(figsize=(10, 6))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".0f",
        cmap="RdYlGn",
        vmin=0,
        vmax=100,
        linewidths=0.5,
        cbar_kws={"label": "% Profitable Years"},
    )

    plt.title("Consistency (% Profitable Years) by Strategy and Timeframe", fontsize=14, fontweight="bold")
    plt.xlabel("Timeframe", fontsize=12)
    plt.ylabel("Strategy", fontsize=12)
    plt.tight_layout()

    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def create_yearly_comparison_chart(df: pd.DataFrame, output_path: Path) -> None:
    """
    Create bar chart comparing all strategies across years.

    Args:
        df: Aggregated results DataFrame
        output_path: Path to save the PNG
    """
    # Group by strategy and year, averaging across timeframes
    grouped = df.groupby(["strategy_name", "year"])["total_return_pct"].mean().reset_index()

    # Create figure
    plt.figure(figsize=(14, 6))

    # Create grouped bar chart
    strategies = sorted(grouped["strategy_name"].unique())
    years = sorted(grouped["year"].unique())
    x = range(len(years))
    width = 0.12

    colors = plt.cm.tab10(range(len(strategies)))

    for i, strategy in enumerate(strategies):
        strategy_data = grouped[grouped["strategy_name"] == strategy]
        values = [strategy_data[strategy_data["year"] == y]["total_return_pct"].values[0] if y in strategy_data["year"].values else 0 for y in years]
        offset = (i - len(strategies) / 2 + 0.5) * width
        bars = plt.bar([xi + offset for xi in x], values, width, label=strategy, color=colors[i])

        # Add value labels on bars
        for bar, val in zip(bars, values, strict=True):
            height = bar.get_height()
            if abs(height) > 1:  # Only show label if significant
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{val:.0f}",
                    ha="center",
                    va="bottom" if height > 0 else "top",
                    fontsize=7,
                )

    plt.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
    plt.xlabel("Year", fontsize=12)
    plt.ylabel("Average Return (%)", fontsize=12)
    plt.title("Strategy Performance by Year (Averaged Across Timeframes)", fontsize=14, fontweight="bold")
    plt.xticks(x, [str(int(y)) for y in years])
    plt.legend(loc="upper left", bbox_to_anchor=(1, 1))
    plt.tight_layout()

    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def create_performance_heatmaps(df: pd.DataFrame, batch_dir: Path) -> list[str]:
    """
    Generate all performance heatmaps and summary dashboard.

    Args:
        df: Aggregated results DataFrame
        batch_dir: Batch run directory

    Returns:
        List of paths to generated files
    """
    paths = []

    # Create executive summary dashboard (most important!)
    dashboard_path = batch_dir / "dashboard_summary.png"
    create_summary_dashboard(df, dashboard_path)
    paths.append(str(dashboard_path))

    # Create return heatmap (realized)
    return_path = batch_dir / "heatmap_return.png"
    create_return_heatmap(df, return_path)
    paths.append(str(return_path))

    # Create total equity return heatmap (realized + unrealized)
    total_equity_path = batch_dir / "heatmap_total_equity.png"
    create_total_equity_heatmap(df, total_equity_path)
    paths.append(str(total_equity_path))

    # Create Sharpe heatmap
    sharpe_path = batch_dir / "heatmap_sharpe.png"
    create_sharpe_heatmap(df, sharpe_path)
    paths.append(str(sharpe_path))

    # Create consistency heatmap
    consistency_path = batch_dir / "heatmap_consistency.png"
    create_consistency_heatmap(df, consistency_path)
    paths.append(str(consistency_path))

    # Create yearly comparison
    yearly_path = batch_dir / "chart_yearly_comparison.png"
    create_yearly_comparison_chart(df, yearly_path)
    paths.append(str(yearly_path))

    return paths


def rank_strategies(df: pd.DataFrame, metric: str = "total_return_pct") -> pd.DataFrame:
    """
    Rank strategies by a specific metric (averaged across all runs).

    Args:
        df: Aggregated results DataFrame
        metric: Metric to rank by

    Returns:
        DataFrame with rankings
    """
    # Group by strategy, average the metric
    rankings = (
        df.groupby("strategy_name")
        .agg(
            {
                metric: "mean",
                "sharpe_ratio": "mean",
                "max_drawdown": "mean",
                "win_rate": "mean",
                "total_trades": "sum",
            }
        )
        .reset_index()
    )

    # Sort and add rank
    rankings = rankings.sort_values(metric, ascending=False).reset_index(drop=True)
    rankings["rank"] = range(1, len(rankings) + 1)

    return rankings


def create_total_equity_heatmap(df: pd.DataFrame, output_path: Path) -> None:
    """
    Create heatmap showing total equity return (realized + unrealized) by strategy and timeframe.

    Args:
        df: Aggregated results DataFrame
        output_path: Path to save the PNG
    """
    # Pivot table: strategies vs timeframes
    pivot = df.pivot_table(
        values="total_equity_return_pct",
        index="strategy_name",
        columns="timeframe",
        aggfunc="mean",
    )

    # Order columns by timeframe
    timeframe_order = ["1h", "4h", "8h", "12h", "1d"]
    available_cols = [t for t in timeframe_order if t in pivot.columns]
    pivot = pivot[available_cols]

    # Create figure
    plt.figure(figsize=(10, 6))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".1f",
        cmap="RdYlGn",
        center=0,
        linewidths=0.5,
        cbar_kws={"label": "Total Equity Return (%)"},
    )

    plt.title("Total Equity Return (%) by Strategy and Timeframe\n(Including Unrealized from Open Positions)", fontsize=14, fontweight="bold")
    plt.xlabel("Timeframe", fontsize=12)
    plt.ylabel("Strategy", fontsize=12)
    plt.tight_layout()

    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def create_summary_dashboard(df: pd.DataFrame, output_path: Path) -> None:
    """
    Create professional executive summary dashboard.

    Single chart with:
    - Key statistics panel
    - Top 5 performers
    - Strategy rankings bar chart
    - Return vs Sharpe scatter plot
    - Mini heatmap

    Args:
        df: Aggregated results DataFrame
        output_path: Path to save the PNG
    """
    from matplotlib.gridspec import GridSpec

    fig = plt.figure(figsize=(16, 14))
    fig.patch.set_facecolor("white")

    # Use GridSpec for flexible layout
    gs = GridSpec(3, 2, figure=fig, height_ratios=[0.8, 1.2, 1.2], hspace=0.35, wspace=0.25)

    # Row 1: Stats + Top Performers (spanning both columns as text)
    ax_header = fig.add_subplot(gs[0, :])
    _draw_stats_and_top_performers(ax_header, df)

    # Row 2 Left: Strategy Rankings Bar Chart
    ax_rankings = fig.add_subplot(gs[1, 0])
    _draw_strategy_rankings(ax_rankings, df)

    # Row 2 Right: Return vs Sharpe Scatter
    ax_scatter = fig.add_subplot(gs[1, 1])
    _draw_return_vs_sharpe(ax_scatter, df)

    # Row 3: Mini Heatmap (spanning both columns)
    ax_heatmap = fig.add_subplot(gs[2, :])
    _draw_mini_heatmap(ax_heatmap, df)

    # Subtitle with batch info
    strategies = df["strategy_name"].nunique()
    timeframes = df["timeframe"].nunique()
    years = df["year"].nunique()

    plt.suptitle(
        "BATCH BACKTEST EXECUTIVE SUMMARY\n" f"{len(df)} backtests  •  {strategies} strategies  •  {timeframes} timeframes  •  {years} years",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )

    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _draw_stats_and_top_performers(ax: plt.Axes, df: pd.DataFrame) -> None:
    """Draw key stats on left, top 5 on right."""
    ax.axis("off")

    # Calculate stats
    total_runs = len(df)
    profitable_runs = (df["total_return_pct"] > 0).sum()
    profitable_pct = profitable_runs / total_runs * 100 if total_runs > 0 else 0
    avg_return = df["total_return_pct"].mean()
    avg_total_return = df["total_equity_return_pct"].mean()
    avg_sharpe = df["sharpe_ratio"].mean()
    open_positions = df["has_open_position"].sum() if "has_open_position" in df.columns else 0

    # Key stats text (left side)
    stats_text = f"""KEY STATISTICS
─────────────────────
Total Backtests:    {total_runs}
Profitable Runs:    {profitable_runs} ({profitable_pct:.0f}%)

Avg Realized Return:  {avg_return:+.1f}%
Avg Total Return:     {avg_total_return:+.1f}%
Avg Sharpe Ratio:     {avg_sharpe:.2f}

Open Positions:     {open_positions}"""

    # Top 5 (right side)
    top5 = df.nlargest(5, "total_return_pct")
    top5_text = "TOP 5 PERFORMERS (Realized Return)\n─────────────────────────────────────\n"
    for i, row in enumerate(top5.itertuples(), 1):
        open_marker = " *" if row.has_open_position else ""
        top5_text += f"{i}. {row.strategy_name} @ {row.timeframe} ({int(row.year)}): {row.total_return_pct:+.1f}%{open_marker}\n"

    if open_positions > 0:
        top5_text += "\n* Has open position at end of period"

    ax.text(0.02, 0.5, stats_text, transform=ax.transAxes, fontfamily="monospace", fontsize=11, va="center", ha="left")
    ax.text(0.52, 0.5, top5_text, transform=ax.transAxes, fontfamily="monospace", fontsize=11, va="center", ha="left")

    # Add separator line
    ax.axhline(y=0.05, xmin=0.02, xmax=0.98, color="gray", linewidth=1, alpha=0.3)


def _draw_strategy_rankings(ax: plt.Axes, df: pd.DataFrame) -> None:
    """Horizontal bar chart of avg return by strategy."""
    rankings = df.groupby("strategy_name")["total_return_pct"].mean().sort_values()
    colors = ["#4CAF50" if v > 0 else "#F44336" for v in rankings.values]

    bars = ax.barh(rankings.index, rankings.values, color=colors, edgecolor="black", linewidth=0.5)

    # Add value labels
    for bar, val in zip(bars, rankings.values, strict=True):
        x_pos = val + (1 if val >= 0 else -1)
        ha = "left" if val >= 0 else "right"
        ax.text(x_pos, bar.get_y() + bar.get_height() / 2, f"{val:+.1f}%", va="center", ha=ha, fontsize=9, fontweight="bold")

    ax.set_title("Average Realized Return by Strategy", fontweight="bold", fontsize=12)
    ax.set_xlabel("Average Return (%)", fontsize=10)
    ax.axvline(x=0, color="black", linewidth=0.8)
    ax.grid(axis="x", alpha=0.3)


def _draw_return_vs_sharpe(ax: plt.Axes, df: pd.DataFrame) -> None:
    """Scatter plot: return vs sharpe, colored by strategy."""
    # Color map for strategies
    strategies = sorted(df["strategy_name"].unique())
    colors = plt.cm.tab10(range(len(strategies)))
    color_map = dict(zip(strategies, colors, strict=True))

    for strategy in strategies:
        data = df[df["strategy_name"] == strategy]
        ax.scatter(
            data["sharpe_ratio"],
            data["total_return_pct"],
            label=strategy,
            color=color_map[strategy],
            alpha=0.7,
            s=60,
            edgecolors="black",
            linewidths=0.5,
        )

    ax.set_xlabel("Sharpe Ratio", fontsize=10)
    ax.set_ylabel("Return (%)", fontsize=10)
    ax.set_title("Return vs Risk-Adjusted Return", fontweight="bold", fontsize=12)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(x=0, color="gray", linestyle="--", alpha=0.5)
    ax.grid(alpha=0.3)


def _draw_mini_heatmap(ax: plt.Axes, df: pd.DataFrame) -> None:
    """Compact heatmap of returns."""
    pivot = df.pivot_table(values="total_return_pct", index="strategy_name", columns="timeframe", aggfunc="mean")

    # Order columns by timeframe
    timeframe_order = ["1h", "4h", "8h", "12h", "1d"]
    available = [t for t in timeframe_order if t in pivot.columns]
    if available:
        pivot = pivot[available]

    sns.heatmap(
        pivot,
        annot=True,
        fmt=".0f",
        cmap="RdYlGn",
        center=0,
        ax=ax,
        cbar_kws={"shrink": 0.6, "label": "Avg Return (%)"},
        linewidths=0.5,
        annot_kws={"fontsize": 10, "fontweight": "bold"},
    )
    ax.set_title("Average Realized Return (%) by Strategy × Timeframe", fontweight="bold", fontsize=12)
    ax.set_xlabel("Timeframe", fontsize=10)
    ax.set_ylabel("Strategy", fontsize=10)
