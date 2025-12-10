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

from src.modules.crypto_trading.services.alpaca_client import get_historical_bars
from src.modules.crypto_trading.services.backtest import DEFAULT_TRADING_FEE_PCT, run_backtest
from src.modules.crypto_trading.services.visualization import create_backtest_chart
from src.modules.crypto_trading.storage.file_storage import get_chart_path, save_backtest_result, save_trades_csv
from src.modules.crypto_trading.strategies import get_strategy, list_strategies


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

    args = parser.parse_args()

    # Determine fee
    trading_fee = 0.0 if args.no_fees else args.fee

    trading_mode_str = "Bidirectional (LONG+SHORT)" if args.bidirectional else "LONG only"

    print(f"\n{'='*60}")
    print(f"  BACKTEST: {args.strategy.upper()} Strategy")
    print(f"{'='*60}")
    print(f"  Symbol: {args.symbol}")
    print(f"  Timeframe: {args.timeframe}")
    print(f"  Period: {args.start} to {args.end or 'now'}")
    print(f"  Capital: ${args.capital:,.0f}")
    print(f"  Position Size: {args.position_size*100:.0f}%")
    print(f"  Trading Mode: {trading_mode_str}")
    print(f"  Trading Fee: {trading_fee}% per trade {'(disabled)' if args.no_fees else '(Alpaca taker)'}")
    print(f"{'='*60}\n")

    # Parse strategy parameters
    strategy_params = parse_strategy_params(args.params)
    if strategy_params:
        print(f"Strategy parameters: {strategy_params}\n")

    # Fetch historical data
    print("Fetching historical data from Alpaca...")
    try:
        df = get_historical_bars(
            symbol=args.symbol,
            timeframe=args.timeframe,
            start=args.start,
            end=args.end,
        )
        print(f"  Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}\n")
    except Exception as e:
        print(f"ERROR: Failed to fetch data: {e}")
        return 1

    if len(df) < 100:
        print(f"WARNING: Only {len(df)} bars loaded. Results may be unreliable.")

    # Get strategy function
    strategy_fn = get_strategy(args.strategy)

    # Run backtest
    print("Running backtest...")
    result = run_backtest(
        df=df,
        strategy_fn=strategy_fn,  # type: ignore[arg-type]
        strategy_params=strategy_params,
        initial_capital=args.capital,
        position_size_pct=args.position_size,
        trading_fee_pct=trading_fee,
        allow_short=args.bidirectional,
    )

    # Print results
    print(f"\n{'='*60}")
    print("  RESULTS")
    print(f"{'='*60}")
    print(f"  Total Return:    {result.total_return_pct:+.2f}%")
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
    print(f"{'='*60}\n")

    # Save results
    print("Saving results...")

    # Save JSON
    json_path = save_backtest_result(result, args.strategy, args.timeframe)
    print(f"  Results: {json_path}")

    # Save trades CSV
    if result.trades:
        csv_path = save_trades_csv(result.trades, args.strategy, args.timeframe)
        print(f"  Trades CSV: {csv_path}")

    # Generate chart
    if not args.no_chart and result.trades:
        print("\nGenerating chart...")
        chart_path = get_chart_path(args.strategy, args.timeframe)
        create_backtest_chart(
            df,
            result,
            args.strategy,
            chart_path,
            strategy_params=strategy_params,
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
