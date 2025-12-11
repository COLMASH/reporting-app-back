#!/usr/bin/env python3
"""
Run backtest for a trading strategy.

Usage:
    python -m src.modules.crypto_trading.scripts.run_backtest \
        --strategy sma_crossover \
        --timeframe 1h \
        --start 2024-01-01 \
        --end 2024-12-01 \
        --capital 10000

Available strategies:
    - sma_crossover: SMA/EMA crossover (fast/slow moving averages)
    - rsi: RSI overbought/oversold
    - macd: MACD signal line crossover
    - bollinger: Bollinger Bands breakout
    - stochastic: Stochastic oscillator crossover
    - adx: ADX trend strength with DI crossover
"""

import argparse
import sys
from datetime import datetime, timedelta

from src.modules.crypto_trading.services.alpaca_client import get_historical_bars
from src.modules.crypto_trading.services.backtest import DEFAULT_TRADING_FEE_PCT, run_backtest
from src.modules.crypto_trading.services.visualization import create_backtest_chart
from src.modules.crypto_trading.storage.file_storage import get_chart_path, get_single_run_dir, save_backtest_result, save_trades_csv
from src.modules.crypto_trading.strategies import get_strategy, list_strategies


def calculate_warmup_start(start_date: str, timeframe: str, lookback_bars: int = 50) -> str:
    """
    Calculate the actual start date for data fetching, including warmup period.

    This ensures indicators have enough historical data to be valid from day 1
    of the requested backtest period.

    Args:
        start_date: User-requested start date (YYYY-MM-DD)
        timeframe: Candle timeframe (1h, 4h, 1d, etc.)
        lookback_bars: Number of bars needed for warmup (default: 50)

    Returns:
        Adjusted start date string (YYYY-MM-DD) that includes warmup period
    """
    # Map timeframe to hours
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
    warmup_hours = lookback_bars * hours_per_bar

    # Add 20% buffer for weekends/gaps
    warmup_hours *= 1.2

    start = datetime.strptime(start_date, "%Y-%m-%d")
    warmup_start = start - timedelta(hours=warmup_hours)

    return warmup_start.strftime("%Y-%m-%d")


def parse_strategy_params(params_str: str | None) -> dict:
    """Parse strategy parameters from string like 'fast_period=10,slow_period=20'."""
    if not params_str:
        return {}

    params = {}
    for pair in params_str.split(","):
        key, value = pair.strip().split("=")
        # Try to convert to number
        try:
            if "." in value:
                params[key.strip()] = float(value)
            else:
                params[key.strip()] = int(value)
        except ValueError:
            params[key.strip()] = value  # type: ignore[assignment]

    return params


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run backtest for a trading strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic SMA crossover backtest
  python -m src.modules.crypto_trading.scripts.run_backtest \\
      --strategy sma_crossover --start 2024-01-01

  # RSI with custom parameters
  python -m src.modules.crypto_trading.scripts.run_backtest \\
      --strategy rsi --start 2024-06-01 --params "period=14,oversold=25,overbought=75"

  # MACD on 4-hour timeframe
  python -m src.modules.crypto_trading.scripts.run_backtest \\
      --strategy macd --timeframe 4h --start 2024-01-01 --capital 50000
        """,
    )

    parser.add_argument(
        "--strategy",
        required=True,
        choices=list_strategies(),
        help="Trading strategy to backtest",
    )
    parser.add_argument(
        "--symbol",
        default="BTC/USD",
        help="Trading pair (default: BTC/USD)",
    )
    parser.add_argument(
        "--timeframe",
        default="1h",
        choices=["1m", "5m", "15m", "30m", "1h", "4h", "8h", "12h", "1d"],
        help="Candle timeframe (default: 1h)",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="End date (YYYY-MM-DD, default: today)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=10000.0,
        help="Initial capital in USD (default: 10000)",
    )
    parser.add_argument(
        "--position-size",
        type=float,
        default=0.1,
        help="Position size as fraction of capital (default: 0.1 = 10%%)",
    )
    parser.add_argument(
        "--params",
        type=str,
        default=None,
        help="Strategy parameters as key=value pairs (e.g., 'fast_period=10,slow_period=20')",
    )
    parser.add_argument(
        "--no-chart",
        action="store_true",
        help="Skip chart generation",
    )
    parser.add_argument(
        "--fee",
        type=float,
        default=DEFAULT_TRADING_FEE_PCT,
        help=f"Trading fee percentage per trade (default: {DEFAULT_TRADING_FEE_PCT}%% - Alpaca crypto taker fee)",
    )
    parser.add_argument(
        "--no-fees",
        action="store_true",
        help="Disable trading fees (for comparison)",
    )
    parser.add_argument(
        "--bidirectional",
        action="store_true",
        help="Enable bidirectional trading (LONG + SHORT). Default: LONG only",
    )
    parser.add_argument(
        "--stop-loss",
        type=float,
        default=None,
        help="Stop-loss percentage (disabled by default). Example: --stop-loss 10 for 10%%",
    )

    args = parser.parse_args()

    # Determine fee
    trading_fee = 0.0 if args.no_fees else args.fee

    # Determine stop-loss (None by default, enabled via --stop-loss X)
    stop_loss = args.stop_loss

    trading_mode_str = "Bidirectional (LONG+SHORT)" if args.bidirectional else "LONG only"
    stop_loss_str = f"{stop_loss}%" if stop_loss else "Disabled"

    print(f"\n{'='*60}")
    print(f"  BACKTEST: {args.strategy.upper()} Strategy")
    print(f"{'='*60}")
    print(f"  Symbol: {args.symbol}")
    print(f"  Timeframe: {args.timeframe}")
    print(f"  Period: {args.start} to {args.end or 'now'}")
    print(f"  Capital: ${args.capital:,.0f}")
    print(f"  Position Size: {args.position_size*100:.0f}%")
    print(f"  Trading Mode: {trading_mode_str}")
    print(f"  Stop-Loss: {stop_loss_str}")
    print(f"  Trading Fee: {trading_fee}% per trade {'(disabled)' if args.no_fees else '(Alpaca taker)'}")
    print(f"{'='*60}\n")

    # Parse strategy parameters
    strategy_params = parse_strategy_params(args.params)
    if strategy_params:
        print(f"Strategy parameters: {strategy_params}\n")

    # Calculate warmup start date (fetch extra data for indicator warmup)
    lookback_bars = 50  # Same as backtest.py default
    warmup_start = calculate_warmup_start(args.start, args.timeframe, lookback_bars)

    # Fetch historical data (including warmup period)
    print("Fetching historical data from Alpaca...")
    try:
        df = get_historical_bars(
            symbol=args.symbol,
            timeframe=args.timeframe,
            start=warmup_start,
            end=args.end,
        )
        print(f"  Fetched {len(df)} bars (including {lookback_bars} warmup bars)")
        print(f"  Data range: {df.index[0]} to {df.index[-1]}\n")
    except Exception as e:
        print(f"ERROR: Failed to fetch data: {e}")
        return 1

    if len(df) < lookback_bars + 50:
        print(f"WARNING: Only {len(df)} bars loaded. Results may be unreliable.")

    # Get strategy function
    strategy_fn = get_strategy(args.strategy)

    # Run backtest (uses full data including warmup for indicator calculation)
    print("Running backtest...")
    result = run_backtest(
        df=df,
        strategy_fn=strategy_fn,  # type: ignore[arg-type]
        strategy_params=strategy_params,
        initial_capital=args.capital,
        position_size_pct=args.position_size,
        trading_fee_pct=trading_fee,
        allow_short=args.bidirectional,
        lookback_period=lookback_bars,
        stop_loss_pct=stop_loss,
    )

    # Trim DataFrame to user-requested period for display/charts
    user_start_str = args.start
    df_display = df[df.index >= user_start_str]

    # Print results
    print(f"\n{'='*60}")
    print("  RESULTS (Realized - Closed Trades Only)")
    print(f"{'='*60}")
    print(f"  Realized Return: {result.total_return_pct:+.2f}%")
    print(f"  Final Capital:   ${result.final_capital:,.2f}")
    print(f"  Max Drawdown:    {result.max_drawdown:.2f}%")
    print(f"  Sharpe Ratio:    {result.sharpe_ratio:.2f}")
    print()
    print(f"  Total Trades:    {result.total_trades}")
    if args.bidirectional:
        print(f"  Long Trades:     {result.long_trades}")
        print(f"  Short Trades:    {result.short_trades}")
    print(f"  Win Rate:        {result.win_rate:.1f}%")
    print(f"  Winning Trades:  {result.winning_trades}")
    print(f"  Losing Trades:   {result.losing_trades}")
    print()
    print(f"  Avg Win:         {result.avg_win_pct:+.2f}%")
    print(f"  Avg Loss:        {result.avg_loss_pct:.2f}%")
    print(f"  Profit Factor:   {result.profit_factor:.2f}")
    print()
    print(f"  Total Fees Paid: ${result.total_fees:,.2f}")
    print(f"  Fee Rate Used:   {result.fee_pct_used}%")

    # Show open position if exists (not included in trade stats)
    if result.open_position:
        print(f"{'='*60}")
        print("  OPEN POSITION (Not Included in Trade Stats)")
        print(f"{'='*60}")
        print(f"  Direction:       {result.open_position['direction'].upper()}")
        print(f"  Entry Price:     ${result.open_position['entry_price']:,.2f}")
        print(f"  Current Price:   ${result.open_position['current_price']:,.2f}")
        print(f"  Unrealized P/L:  ${result.unrealized_pnl:+,.2f} ({result.open_position['unrealized_pnl_pct']:+.2f}%)")
        print(f"  Entry Reason:    {result.open_position['entry_reason']}")
        print()
        print(f"  Total Equity:    ${result.total_equity:,.2f} (if closed now)")
        print(f"  Total Return:    {result.total_equity_return_pct:+.2f}% (if closed now)")

    print(f"{'='*60}\n")

    # Save results
    print("Saving results...")

    # Create run directory ONCE (all files go to same folder)
    run_dir = get_single_run_dir(args.strategy, args.timeframe)
    print(f"  Run folder: {run_dir}")

    # Save JSON
    json_path = save_backtest_result(result, args.strategy, args.timeframe, run_dir=run_dir)
    print(f"  Results: {json_path}")

    # Save trades CSV
    if result.trades:
        csv_path = save_trades_csv(result.trades, args.strategy, args.timeframe, run_dir=run_dir)
        print(f"  Trades CSV: {csv_path}")

    # Generate chart (using trimmed data for cleaner visualization)
    if not args.no_chart and result.trades:
        print("\nGenerating chart...")
        chart_path = get_chart_path(args.strategy, args.timeframe, run_dir=run_dir)
        create_backtest_chart(
            df_display,
            result,
            args.strategy,
            chart_path,
            strategy_params=strategy_params,
            timeframe=args.timeframe,
            year=int(args.start.split("-")[0]),
        )
        print(f"  Chart: {chart_path}")

    print("\nBacktest complete!")

    # Print trade summary
    if result.trades:
        print(f"\n{'='*60}")
        print("  TRADE HISTORY")
        print(f"{'='*60}")
        for i, trade in enumerate(result.trades, 1):
            pnl_color = "\033[92m" if trade["pnl"] > 0 else "\033[91m"
            reset = "\033[0m"
            direction = trade.get("direction", "long").upper()
            print(f"  #{i} [{direction}]: {trade['entry_time']} -> {trade['exit_time']}")
            print(f"      Entry: ${trade['entry_price']:.2f} | Exit: ${trade['exit_price']:.2f}")
            print(f"      {pnl_color}PnL: ${trade['pnl']:.2f} ({trade['pnl_pct']:+.2f}%){reset} | Fees: ${trade.get('total_fees', 0):.2f}")
            print(f"      Reason: {trade['exit_reason']}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
