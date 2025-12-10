#!/usr/bin/env python3
"""
Run trading bot for live/paper trading.

Usage:
    # Paper trading (default, safe)
    python -m src.modules.crypto_trading.scripts.run_bot --config data/crypto_trading/configs/my_bot.json

    # Live trading (REAL MONEY - requires confirmation)
    python -m src.modules.crypto_trading.scripts.run_bot --config my_bot.json --live

Environment variables required:
    ALPACA_API_KEY: Your Alpaca API key
    ALPACA_SECRET_KEY: Your Alpaca secret key

The bot will:
    1. Load configuration from JSON file
    2. Connect to Alpaca API
    3. Poll at the configured timeframe interval
    4. Execute buy/sell signals from the strategy
    5. Log all trades to CSV files
"""

import argparse
import sys

from dotenv import load_dotenv

from src.modules.crypto_trading.config import BotConfig, StrategyParams
from src.modules.crypto_trading.services.trading import (
    check_and_close_position,
    get_bot_status,
    run_trading_loop,
)
from src.modules.crypto_trading.storage.file_storage import load_bot_config
from src.modules.crypto_trading.strategies import list_strategies


def main() -> int:
    """Main entry point."""
    load_dotenv()  # Load .env file

    parser = argparse.ArgumentParser(
        description="Run trading bot for live/paper trading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with config file (paper trading)
  python -m src.modules.crypto_trading.scripts.run_bot \\
      --config data/crypto_trading/configs/sma_bot.json

  # Quick start without config file
  python -m src.modules.crypto_trading.scripts.run_bot \\
      --strategy sma_crossover --timeframe 1h --size 100

  # Check status
  python -m src.modules.crypto_trading.scripts.run_bot --status

  # Close any open position
  python -m src.modules.crypto_trading.scripts.run_bot --close-position

WARNING: Using --live will trade with REAL MONEY!
        """,
    )

    # Config options
    parser.add_argument(
        "--config",
        type=str,
        help="Path to bot configuration JSON file",
    )

    # Quick start options (alternative to config file)
    parser.add_argument(
        "--strategy",
        choices=list_strategies(),
        help="Strategy to use (if not using --config)",
    )
    parser.add_argument(
        "--symbol",
        default="BTC/USD",
        help="Trading pair (default: BTC/USD)",
    )
    parser.add_argument(
        "--timeframe",
        default="1h",
        choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
        help="Candle timeframe (default: 1h)",
    )
    parser.add_argument(
        "--size",
        type=float,
        default=100.0,
        help="Position size in USD (default: 100)",
    )
    parser.add_argument(
        "--params",
        type=str,
        default=None,
        help="Strategy parameters as key=value pairs",
    )
    parser.add_argument(
        "--position-size",
        type=float,
        default=None,
        help="Position size as fraction of equity (0.99 = 99%%). Mutually exclusive with --size",
    )

    # Mode
    parser.add_argument(
        "--live",
        action="store_true",
        help="USE REAL MONEY - requires confirmation",
    )

    # Utility commands
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current bot/account status and exit",
    )
    parser.add_argument(
        "--close-position",
        action="store_true",
        help="Close any open position and exit",
    )

    # Other options
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Stop after N iterations (for testing)",
    )

    args = parser.parse_args()

    # Build config
    if args.config:
        try:
            config = load_bot_config(args.config)
            print(f"Loaded config from: {args.config}")
        except FileNotFoundError:
            print(f"ERROR: Config file not found: {args.config}")
            return 1
        except Exception as e:
            print(f"ERROR: Failed to load config: {e}")
            return 1
    elif args.strategy:
        # Build config from command line args
        strategy_params: dict = {}
        if args.params:
            for pair in args.params.split(","):
                key, value = pair.strip().split("=")
                try:
                    if "." in value:
                        strategy_params[key.strip()] = float(value)
                    else:
                        strategy_params[key.strip()] = int(value)
                except ValueError:
                    strategy_params[key.strip()] = value

        # Validate mutually exclusive options
        if args.size != 100.0 and args.position_size is not None:
            print("ERROR: --size and --position-size are mutually exclusive")
            return 1

        config = BotConfig(
            symbol=args.symbol,
            timeframe=args.timeframe,
            strategy=StrategyParams(name=args.strategy, params=strategy_params),
            position_size_usd=args.size if args.position_size is None else None,
            position_size_pct=args.position_size,
        )
    else:
        print("ERROR: Either --config or --strategy is required")
        parser.print_help()
        return 1

    # Paper mode by default
    paper = not args.live

    # Handle utility commands
    if args.status:
        status = get_bot_status(config, paper=paper)
        print(f"\n{'='*50}")
        print(f"  BOT STATUS ({'PAPER' if paper else 'LIVE'} MODE)")
        print(f"{'='*50}")
        print(f"  Symbol: {status['symbol']}")
        print(f"  Strategy: {status['strategy']}")
        print("\n  Account:")
        print(f"    Buying Power: ${status['account']['buying_power']:,.2f}")
        print(f"    Portfolio Value: ${status['account']['portfolio_value']:,.2f}")
        if status["position"]:
            pos = status["position"]
            print("\n  Open Position:")
            print(f"    Qty: {pos['qty']:.6f}")
            print(f"    Entry: ${pos['avg_entry_price']:.2f}")
            print(f"    Current: ${pos['current_price']:.2f}")
            print(f"    Unrealized P/L: ${pos['unrealized_pl']:.2f}")
        else:
            print("\n  No open position")
        print(f"{'='*50}\n")
        return 0

    if args.close_position:
        print("Checking for open position...")
        result = check_and_close_position(config, paper=paper)
        if result:
            print("Position closed successfully")
        else:
            print("No open position to close")
        return 0

    # Live trading confirmation
    if args.live:
        print("\n" + "=" * 60)
        print("  WARNING: LIVE TRADING MODE")
        print("  This will trade with REAL MONEY!")
        print("=" * 60)
        print(f"\n  Symbol: {config.symbol}")
        print(f"  Strategy: {config.strategy.name}")
        if config.position_size_pct is not None:
            print(f"  Position Size: {config.position_size_pct * 100:.0f}% of equity")
        else:
            print(f"  Position Size: ${config.position_size_usd:.2f}")
        print()

        confirm = input("Type 'YES I UNDERSTAND' to confirm: ")
        if confirm != "YES I UNDERSTAND":
            print("\nAborted. Use paper trading to test safely.")
            return 0

        print("\nStarting LIVE trading...\n")

    # Run the trading loop
    try:
        run_trading_loop(
            config=config,
            paper=paper,
            verbose=not args.quiet,
            max_iterations=args.max_iterations,
        )
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nMake sure ALPACA_API_KEY and ALPACA_SECRET_KEY are set:")
        print("  export ALPACA_API_KEY=your_key")
        print("  export ALPACA_SECRET_KEY=your_secret")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
