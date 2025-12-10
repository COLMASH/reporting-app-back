"""Alpaca API wrapper functions for crypto trading."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import ClosePositionRequest, MarketOrderRequest

from src.modules.crypto_trading.config import AlpacaConfig, timeframe_to_minutes


def create_trading_client(config: AlpacaConfig) -> TradingClient:
    """Create Alpaca trading client."""
    return TradingClient(
        api_key=config.api_key,
        secret_key=config.secret_key,
        paper=config.paper,
    )


def create_data_client() -> CryptoHistoricalDataClient:
    """Create Alpaca crypto data client (no auth needed for crypto)."""
    return CryptoHistoricalDataClient()


def _parse_timeframe(timeframe: str) -> TimeFrame:
    """Convert timeframe string to Alpaca TimeFrame object."""
    minutes = timeframe_to_minutes(timeframe)

    if minutes < 60:
        return TimeFrame(amount=minutes, unit=TimeFrameUnit.Minute)
    elif minutes < 1440:
        return TimeFrame(amount=minutes // 60, unit=TimeFrameUnit.Hour)
    else:
        return TimeFrame(amount=minutes // 1440, unit=TimeFrameUnit.Day)


def get_historical_bars(
    symbol: str,
    timeframe: str,
    start: datetime | str,
    end: datetime | str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data from Alpaca.

    Args:
        symbol: Trading pair (e.g., "BTC/USD")
        timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
        start: Start datetime or date string (YYYY-MM-DD)
        end: End datetime or date string (None = now)
        limit: Maximum number of bars to fetch

    Returns:
        DataFrame with columns: open, high, low, close, volume, trade_count, vwap
        Index is datetime
    """
    client = create_data_client()

    # Parse dates
    if isinstance(start, str):
        start = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=ZoneInfo("America/New_York"))

    if end is None:
        end = datetime.now(ZoneInfo("America/New_York"))
    elif isinstance(end, str):
        end = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=ZoneInfo("America/New_York"))

    tf = _parse_timeframe(timeframe)

    request = CryptoBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=tf,
        start=start,
        end=end,
        limit=limit,
    )

    bars = client.get_crypto_bars(request)

    # Convert to DataFrame
    df: pd.DataFrame = bars.df  # type: ignore[union-attr]

    # If multi-symbol response, filter to just our symbol
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level="symbol")  # type: ignore[assignment]

    # Ensure proper column names (rename is identity here but ensures consistency)
    df = df.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})

    return df


def get_recent_bars(
    symbol: str,
    timeframe: str,
    lookback: int = 100,
) -> pd.DataFrame:
    """
    Fetch recent historical bars for strategy calculation.

    Args:
        symbol: Trading pair
        timeframe: Candle timeframe
        lookback: Number of bars to fetch

    Returns:
        DataFrame with OHLCV data
    """
    # Calculate how far back to go based on timeframe
    minutes = timeframe_to_minutes(timeframe)
    lookback_minutes = minutes * lookback * 2  # Extra buffer for gaps
    start = datetime.now(ZoneInfo("America/New_York")) - timedelta(minutes=lookback_minutes)

    df = get_historical_bars(symbol, timeframe, start, limit=lookback)

    return df.tail(lookback)


def place_market_order(
    client: TradingClient,
    symbol: str,
    side: str,
    notional: float,
) -> dict:
    """
    Place a market order with USD amount.

    Args:
        client: Alpaca trading client
        symbol: Trading pair (e.g., "BTC/USD")
        side: "buy" or "sell"
        notional: USD amount to trade

    Returns:
        Order details dict
    """
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

    request = MarketOrderRequest(
        symbol=symbol,
        notional=notional,
        side=order_side,
        time_in_force=TimeInForce.GTC,
    )

    order = client.submit_order(request)

    return {
        "id": str(order.id),  # type: ignore[union-attr]
        "symbol": order.symbol,  # type: ignore[union-attr]
        "side": order.side.value if order.side else None,  # type: ignore[union-attr]
        "notional": float(order.notional) if order.notional else None,  # type: ignore[union-attr]
        "qty": float(order.qty) if order.qty else None,  # type: ignore[union-attr]
        "filled_qty": float(order.filled_qty) if order.filled_qty else None,  # type: ignore[union-attr]
        "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,  # type: ignore[union-attr]
        "status": order.status.value if order.status else None,  # type: ignore[union-attr]
        "created_at": str(order.created_at),  # type: ignore[union-attr]
    }


def get_current_position(client: TradingClient, symbol: str) -> dict | None:
    """
    Get current position for a symbol.

    Args:
        client: Alpaca trading client
        symbol: Trading pair (e.g., "BTC/USD" or "BTCUSD")

    Returns:
        Position dict or None if no position
    """
    # Alpaca uses "BTCUSD" format for positions
    symbol_clean = symbol.replace("/", "")

    try:
        position = client.get_open_position(symbol_clean)
        return {
            "symbol": position.symbol,  # type: ignore[union-attr]
            "qty": float(position.qty),  # type: ignore[union-attr, arg-type]
            "avg_entry_price": float(position.avg_entry_price),  # type: ignore[union-attr, arg-type]
            "market_value": float(position.market_value),  # type: ignore[union-attr, arg-type]
            "unrealized_pl": float(position.unrealized_pl),  # type: ignore[union-attr, arg-type]
            "unrealized_plpc": float(position.unrealized_plpc),  # type: ignore[union-attr, arg-type]
            "current_price": float(position.current_price),  # type: ignore[union-attr, arg-type]
        }
    except Exception:
        # No position exists
        return None


def close_position(client: TradingClient, symbol: str, qty: float | None = None) -> dict:
    """
    Close position for a symbol.

    Args:
        client: Alpaca trading client
        symbol: Trading pair
        qty: Quantity to close (None = close all)

    Returns:
        Order details dict
    """
    symbol_clean = symbol.replace("/", "")

    close_options = None
    if qty is not None:
        close_options = ClosePositionRequest(qty=str(qty))

    order = client.close_position(symbol_clean, close_options=close_options)

    return {
        "id": str(order.id),  # type: ignore[union-attr]
        "symbol": order.symbol,  # type: ignore[union-attr]
        "side": order.side.value if order.side else None,  # type: ignore[union-attr]
        "qty": float(order.qty) if order.qty else None,  # type: ignore[union-attr]
        "filled_qty": float(order.filled_qty) if order.filled_qty else None,  # type: ignore[union-attr]
        "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,  # type: ignore[union-attr]
        "status": order.status.value if order.status else None,  # type: ignore[union-attr]
        "created_at": str(order.created_at),  # type: ignore[union-attr]
    }


def get_account(client: TradingClient) -> dict:
    """Get account information."""
    account = client.get_account()

    return {
        "id": str(account.id),  # type: ignore[union-attr]
        "buying_power": float(account.buying_power),  # type: ignore[union-attr, arg-type]
        "cash": float(account.cash),  # type: ignore[union-attr, arg-type]
        "portfolio_value": float(account.portfolio_value),  # type: ignore[union-attr, arg-type]
        "equity": float(account.equity),  # type: ignore[union-attr, arg-type]
        "status": account.status.value if account.status else None,  # type: ignore[union-attr]
    }


def get_all_positions(client: TradingClient) -> list[dict]:
    """Get all open positions."""
    positions = client.get_all_positions()

    return [
        {
            "symbol": p.symbol,  # type: ignore[union-attr]
            "qty": float(p.qty),  # type: ignore[union-attr, arg-type]
            "avg_entry_price": float(p.avg_entry_price),  # type: ignore[union-attr, arg-type]
            "market_value": float(p.market_value),  # type: ignore[union-attr, arg-type]
            "unrealized_pl": float(p.unrealized_pl),  # type: ignore[union-attr, arg-type]
            "current_price": float(p.current_price),  # type: ignore[union-attr, arg-type]
        }
        for p in positions
    ]
