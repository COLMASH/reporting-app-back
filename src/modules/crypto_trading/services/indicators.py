"""Technical indicator calculations for trading strategies.

All functions are pure - they take data and return calculated values.
"""

import pandas as pd


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """
    Calculate Simple Moving Average.

    Args:
        prices: Price series (typically close prices)
        period: Number of periods for averaging

    Returns:
        SMA values series
    """
    return prices.rolling(window=period).mean()


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average.

    Args:
        prices: Price series (typically close prices)
        period: Number of periods for EMA span

    Returns:
        EMA values series
    """
    return prices.ewm(span=period, adjust=False).mean()


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index.

    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss

    Args:
        prices: Price series (typically close prices)
        period: RSI period (default 14)

    Returns:
        RSI values series (0-100)
    """
    # Calculate price changes
    delta = prices.diff()

    # Separate gains and losses
    gains = delta.where(delta > 0, 0.0)  # type: ignore[operator]
    losses = (-delta).where(delta < 0, 0.0)  # type: ignore[operator]

    # Calculate average gains and losses using EMA
    avg_gains = gains.ewm(span=period, adjust=False).mean()
    avg_losses = losses.ewm(span=period, adjust=False).mean()

    # Calculate RS and RSI
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(
    prices: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    MACD Line = Fast EMA - Slow EMA
    Signal Line = EMA of MACD Line
    Histogram = MACD Line - Signal Line

    Args:
        prices: Price series (typically close prices)
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line EMA period (default 9)

    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)

    macd_line = fast_ema - slow_ema
    signal_line = calculate_ema(macd_line, signal_period)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.

    Middle Band = SMA
    Upper Band = SMA + (std_dev * Standard Deviation)
    Lower Band = SMA - (std_dev * Standard Deviation)

    Args:
        prices: Price series (typically close prices)
        period: SMA period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)

    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    middle_band = calculate_sma(prices, period)
    rolling_std = prices.rolling(window=period).std()

    upper_band = middle_band + (std_dev * rolling_std)
    lower_band = middle_band - (std_dev * rolling_std)

    return upper_band, middle_band, lower_band


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic Oscillator.

    %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
    %D = SMA of %K

    Args:
        high: High price series
        low: Low price series
        close: Close price series
        k_period: %K period (default 14)
        d_period: %D smoothing period (default 3)

    Returns:
        Tuple of (%K, %D)
    """
    # Calculate highest high and lowest low
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    # Calculate %K
    k = ((close - lowest_low) / (highest_high - lowest_low)) * 100

    # Calculate %D (SMA of %K)
    d = k.rolling(window=d_period).mean()

    return k, d


def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Average Directional Index (ADX).

    ADX measures trend strength (not direction).
    +DI and -DI measure directional movement.

    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: ADX period (default 14)

    Returns:
        Tuple of (adx, plus_di, minus_di)
    """
    # Calculate True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Calculate directional movement
    plus_dm = high.diff()
    minus_dm = -low.diff()

    # Only positive values, and zero if other is larger
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)  # type: ignore[operator]
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)  # type: ignore[operator]

    # Smooth with EMA
    atr = true_range.ewm(span=period, adjust=False).mean()
    plus_dm_smooth = plus_dm.ewm(span=period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(span=period, adjust=False).mean()

    # Calculate +DI and -DI
    plus_di = (plus_dm_smooth / atr) * 100
    minus_di = (minus_dm_smooth / atr) * 100

    # Calculate DX
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100

    # Calculate ADX (smoothed DX)
    adx = dx.ewm(span=period, adjust=False).mean()

    return adx, plus_di, minus_di


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Calculate Average True Range (ATR).

    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: ATR period (default 14)

    Returns:
        ATR values series
    """
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    return true_range.ewm(span=period, adjust=False).mean()
