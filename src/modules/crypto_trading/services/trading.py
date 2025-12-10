"""Live/paper trading functions.

Handles the polling loop and trade execution for live trading.
"""

import os
import time
from datetime import datetime

from src.modules.crypto_trading.config import AlpacaConfig, BotConfig, timeframe_to_seconds
from src.modules.crypto_trading.services.alpaca_client import (
    close_position,
    create_trading_client,
    get_account,
    get_current_position,
    get_recent_bars,
    place_market_order,
)
from src.modules.crypto_trading.storage.file_storage import log_trade
from src.modules.crypto_trading.strategies import get_strategy


def get_alpaca_config_from_env(paper: bool = True) -> AlpacaConfig:
    """
    Create AlpacaConfig from environment variables.

    Args:
        paper: Use paper trading (default True)

    Returns:
        AlpacaConfig instance

    Raises:
        ValueError: If required env vars not set
    """
    api_key = os.environ.get("ALPACA_API_KEY")
    secret_key = os.environ.get("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables must be set")

    return AlpacaConfig(
        api_key=api_key,
        secret_key=secret_key,
        paper=paper,
    )


def run_trading_loop(
    config: BotConfig,
    paper: bool = True,
    verbose: bool = True,
    max_iterations: int | None = None,
) -> None:
    """
    Run the main trading loop.

    Polls at configured interval, checks strategy signals, and executes trades.

    Args:
        config: Bot configuration
        paper: Use paper trading (default True)
        verbose: Print status messages (default True)
        max_iterations: Stop after N iterations (None = run forever)
    """
    # Setup
    alpaca_config = get_alpaca_config_from_env(paper)
    client = create_trading_client(alpaca_config)
    strategy_fn = get_strategy(config.strategy.name)
    interval = timeframe_to_seconds(config.timeframe)

    # Get account info
    account = get_account(client)
    mode = "PAPER" if paper else "LIVE"

    if verbose:
        print(f"\n{'='*60}")
        print(f"  TRADING BOT - {mode} MODE")
        print(f"{'='*60}")
        print(f"  Symbol: {config.symbol}")
        print(f"  Strategy: {config.strategy.name}")
        print(f"  Timeframe: {config.timeframe}")
        if config.position_size_pct is not None:
            print(f"  Position Size: {config.position_size_pct * 100:.0f}% of equity")
        else:
            print(f"  Position Size: ${config.position_size_usd:.2f}")
        print(f"  Poll Interval: {interval}s")
        print(f"\n  Account Equity: ${account['equity']:,.2f}")
        print(f"{'='*60}")
        print("\n  Press Ctrl+C to stop\n")

    iteration = 0

    while True:
        try:
            iteration += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Check iteration limit
            if max_iterations is not None and iteration > max_iterations:
                if verbose:
                    print(f"\n[{timestamp}] Max iterations ({max_iterations}) reached. Stopping.")
                break

            # Fetch recent bars
            df = get_recent_bars(config.symbol, config.timeframe, lookback=100)

            if len(df) < 50:
                if verbose:
                    print(f"[{timestamp}] Insufficient data ({len(df)} bars). Waiting...")
                time.sleep(interval)
                continue

            current_price = df["close"].iloc[-1]

            # Get strategy signal
            signal = strategy_fn(df, **config.strategy.params)

            # Get current position
            position = get_current_position(client, config.symbol)

            # Execute based on signal
            if signal["signal"] == "buy" and position is None:
                # Calculate position size
                if config.position_size_pct is not None:
                    current_account = get_account(client)
                    position_size_usd = current_account['equity'] * config.position_size_pct
                else:
                    position_size_usd = config.position_size_usd

                # Open position
                if verbose:
                    print(f"[{timestamp}] BUY SIGNAL: {signal['reason']}")
                    print(f"             Price: ${current_price:,.2f}")
                    if config.position_size_pct is not None:
                        print(f"             Size: ${position_size_usd:.2f} ({config.position_size_pct*100:.0f}% of equity)")
                    else:
                        print(f"             Size: ${position_size_usd:.2f}")

                try:
                    order = place_market_order(
                        client=client,
                        symbol=config.symbol,
                        side="buy",
                        notional=position_size_usd,
                    )

                    if verbose:
                        print(f"             Order ID: {order['id']}")
                        print(f"             Status: {order['status']}")

                    # Log trade
                    log_trade(
                        {
                            "timestamp": timestamp,
                            "action": "BUY",
                            "symbol": config.symbol,
                            "price": current_price,
                            "notional": position_size_usd,
                            "order_id": order["id"],
                            "status": order["status"],
                            "reason": signal["reason"],
                            "strategy": config.strategy.name,
                        },
                        bot_name=config.strategy.name,
                    )

                except Exception as e:
                    print(f"[{timestamp}] ORDER ERROR: {e}")

            elif signal["signal"] == "sell" and position is not None:
                # Close position
                if verbose:
                    print(f"[{timestamp}] SELL SIGNAL: {signal['reason']}")
                    print(f"             Price: ${current_price:,.2f}")
                    print(f"             Position: {position['qty']:.6f} {config.symbol}")
                    print(f"             Unrealized P/L: ${position['unrealized_pl']:.2f}")

                try:
                    order = close_position(client, config.symbol)

                    if verbose:
                        print(f"             Order ID: {order['id']}")
                        print(f"             Status: {order['status']}")

                    # Log trade
                    log_trade(
                        {
                            "timestamp": timestamp,
                            "action": "SELL",
                            "symbol": config.symbol,
                            "price": current_price,
                            "qty": position["qty"],
                            "entry_price": position["avg_entry_price"],
                            "unrealized_pl": position["unrealized_pl"],
                            "order_id": order["id"],
                            "status": order["status"],
                            "reason": signal["reason"],
                            "strategy": config.strategy.name,
                        },
                        bot_name=config.strategy.name,
                    )

                except Exception as e:
                    print(f"[{timestamp}] ORDER ERROR: {e}")

            else:
                # Hold
                if verbose:
                    position_str = "No position"
                    if position:
                        position_str = f"Position: {position['qty']:.6f} @ ${position['avg_entry_price']:.2f}"
                    print(f"[{timestamp}] HOLD - {signal['reason']}")
                    print(f"             Price: ${current_price:,.2f} | {position_str}")

            # Wait for next interval
            time.sleep(interval)

        except KeyboardInterrupt:
            if verbose:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Bot stopped by user")
            break

        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {e}")
            # Wait before retry
            time.sleep(60)


def check_and_close_position(config: BotConfig, paper: bool = True) -> dict | None:
    """
    Check if there's an open position and close it.

    Useful for emergency exits or bot cleanup.

    Args:
        config: Bot configuration
        paper: Use paper trading

    Returns:
        Order dict if position was closed, None if no position
    """
    alpaca_config = get_alpaca_config_from_env(paper)
    client = create_trading_client(alpaca_config)

    position = get_current_position(client, config.symbol)

    if position is None:
        return None

    print(f"Closing position: {position['qty']:.6f} {config.symbol}")
    print(f"  Entry: ${position['avg_entry_price']:.2f}")
    print(f"  Current: ${position['current_price']:.2f}")
    print(f"  Unrealized P/L: ${position['unrealized_pl']:.2f}")

    order = close_position(client, config.symbol)
    print(f"  Order: {order['id']} - {order['status']}")

    return order


def get_bot_status(config: BotConfig, paper: bool = True) -> dict:
    """
    Get current bot/account status.

    Args:
        config: Bot configuration
        paper: Use paper trading

    Returns:
        Status dict with account and position info
    """
    alpaca_config = get_alpaca_config_from_env(paper)
    client = create_trading_client(alpaca_config)

    account = get_account(client)
    position = get_current_position(client, config.symbol)

    return {
        "mode": "paper" if paper else "live",
        "symbol": config.symbol,
        "strategy": config.strategy.name,
        "account": account,
        "position": position,
    }
