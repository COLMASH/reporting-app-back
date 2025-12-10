# Crypto Trading Module

Automated crypto trading system using Alpaca API. Includes backtesting and live paper trading.

## Quick Start

### 1. Setup Alpaca Account

1. Create account at [alpaca.markets](https://alpaca.markets)
2. Go to **Paper Trading** section
3. Generate API keys

### 2. Configure Environment

Add to your `.env` file:

```bash
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
```

### 3. Run Backtest

```bash
uv run python -m src.modules.crypto_trading.scripts.run_backtest \
    --strategy bollinger \
    --timeframe 4h \
    --start 2024-01-01 \
    --position-size 0.99
```

### 4. Run Live Bot (Paper Trading)

```bash
uv run python -m src.modules.crypto_trading.scripts.run_bot \
    --strategy bollinger \
    --timeframe 4h \
    --position-size 0.99
```

---

## Available Strategies

| Strategy | Description | Key Parameters |
|----------|-------------|----------------|
| `sma_crossover` | SMA/EMA crossover | `fast_period`, `slow_period` |
| `rsi` | RSI overbought/oversold | `period`, `oversold`, `overbought` |
| `macd` | MACD signal line crossover | `fast_period`, `slow_period`, `signal_period` |
| `bollinger` | Bollinger Bands breakout | `period`, `std_dev` |
| `stochastic` | Stochastic oscillator | `k_period`, `d_period` |
| `adx` | ADX trend strength + DI crossover | `period`, `adx_threshold` |

---

## Backtesting

Test strategies on historical data before risking real money.

### Basic Usage

```bash
uv run python -m src.modules.crypto_trading.scripts.run_backtest \
    --strategy <strategy_name> \
    --start <YYYY-MM-DD> \
    [options]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--strategy` | required | Strategy to test |
| `--start` | required | Start date (YYYY-MM-DD) |
| `--end` | today | End date |
| `--symbol` | BTC/USD | Trading pair |
| `--timeframe` | 1h | Candle size: 1m, 5m, 15m, 30m, 1h, 4h, 8h, 12h, 1d |
| `--capital` | 10000 | Initial capital in USD |
| `--position-size` | 0.1 | Position size as % of capital (0.1 = 10%) |
| `--params` | - | Strategy params: `"fast_period=10,slow_period=20"` |
| `--bidirectional` | off | Enable LONG + SHORT trading |
| `--fee` | 0.25 | Trading fee % (Alpaca taker fee) |
| `--no-fees` | off | Disable fees for comparison |
| `--no-chart` | off | Skip chart generation |

### Examples

```bash
# RSI with custom parameters
uv run python -m src.modules.crypto_trading.scripts.run_backtest \
    --strategy rsi \
    --start 2024-06-01 \
    --params "period=14,oversold=25,overbought=75"

# Bidirectional trading (LONG + SHORT)
uv run python -m src.modules.crypto_trading.scripts.run_backtest \
    --strategy macd \
    --start 2024-01-01 \
    --bidirectional \
    --capital 50000

# Compare with/without fees
uv run python -m src.modules.crypto_trading.scripts.run_backtest \
    --strategy bollinger --start 2024-01-01 --no-fees
```

### Output

Results saved to `data/crypto_trading/`:
- `backtests/*.json` - Full results
- `trades/*.csv` - Trade history
- `charts/*.png` - Visual chart with entry/exit points

---

## Live Bot (Paper Trading)

Run automated trading on Alpaca paper trading account.

### Basic Usage

```bash
uv run python -m src.modules.crypto_trading.scripts.run_bot \
    --strategy <strategy_name> \
    [options]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--strategy` | required | Strategy to use |
| `--symbol` | BTC/USD | Trading pair |
| `--timeframe` | 1h | Candle size |
| `--size` | 100 | Fixed USD per trade |
| `--position-size` | - | Position as % of equity (0.99 = 99%) |
| `--params` | - | Strategy params |
| `--bidirectional` | off | Enable LONG + SHORT |
| `--interval` | 60 | Seconds between checks |
| `--verbose` | off | Show detailed output |
| `--dry-run` | off | Simulate without placing orders |

**Note:** `--size` and `--position-size` are mutually exclusive.

### Examples

```bash
# 99% of account equity per trade
uv run python -m src.modules.crypto_trading.scripts.run_bot \
    --strategy bollinger \
    --timeframe 4h \
    --position-size 0.99 \
    --verbose

# Fixed $500 per trade, check every 5 minutes
uv run python -m src.modules.crypto_trading.scripts.run_bot \
    --strategy rsi \
    --size 500 \
    --interval 300

# Dry run (no real orders)
uv run python -m src.modules.crypto_trading.scripts.run_bot \
    --strategy macd \
    --dry-run \
    --verbose
```

---

## Running on Server

### Option 1: nohup (Simple)

```bash
# SSH into server
ssh proyecto_ai_ilv@<server-ip>

# Navigate to project
cd /home/proyecto_ai_ilv/reporting-app-back

# Run in background
nohup uv run python -m src.modules.crypto_trading.scripts.run_bot \
    --strategy bollinger \
    --timeframe 4h \
    --position-size 0.99 \
    > /tmp/trading_bot.log 2>&1 &

# Check if running
ps aux | grep run_bot

# View logs
tail -f /tmp/trading_bot.log

# Stop the bot
pkill -f "run_bot"
```

### Option 2: systemd (Recommended)

Create service file `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=proyecto_ai_ilv
WorkingDirectory=/home/proyecto_ai_ilv/reporting-app-back
Environment="PATH=/home/proyecto_ai_ilv/.local/bin:/usr/bin"
ExecStart=/home/proyecto_ai_ilv/.local/bin/uv run python -m src.modules.crypto_trading.scripts.run_bot --strategy bollinger --timeframe 4h --position-size 0.99
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot

# View logs
sudo journalctl -u trading-bot -f

# Stop
sudo systemctl stop trading-bot
```

---

## Architecture

```
crypto_trading/
├── config.py           # Configuration (BotConfig, BacktestConfig)
├── scripts/
│   ├── run_backtest.py # Backtest CLI
│   └── run_bot.py      # Live trading CLI
├── services/
│   ├── alpaca_client.py    # Alpaca API wrapper
│   ├── backtest.py         # Backtesting engine
│   ├── indicators.py       # Technical indicators (SMA, EMA, RSI, etc.)
│   ├── trading.py          # Live trading loop
│   └── visualization.py    # Chart generation
├── strategies/
│   ├── base.py         # TradeSignal type
│   ├── sma_crossover.py
│   ├── rsi.py
│   ├── macd.py
│   ├── bollinger.py
│   ├── stochastic.py
│   └── adx.py
└── storage/
    └── file_storage.py # Save results to JSON/CSV
```

---

## Fees

Alpaca crypto trading fees (volume < $100K/month):
- **Taker** (market orders): 0.25%
- **Maker** (limit orders): 0.15%

Backtests use taker fee by default since they simulate market orders.
