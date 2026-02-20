# Simplified Trading Bot

A professional Python CLI application that places and manages orders on the **Binance Futures Testnet (USDT-M)**.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup Instructions](#setup-instructions)
3. [Configuration](#configuration)
4. [Usage Examples](#usage-examples)
5. [Project Structure](#project-structure)
6. [Logging](#logging)
7. [Error Handling](#error-handling)
8. [Assumptions](#assumptions)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10 or higher |
| pip | 22+ recommended |

You also need a **Binance Futures Testnet** account with an API key/secret pair:

1. Go to <https://testnet.binancefuture.com>
2. Register or log in.
3. Navigate to **API Management** and create a new API key.
4. Save the **API Key** and **Secret Key** — you will not be able to view the secret again.

---

## Setup Instructions

```bash
# 1. Clone the repository
git clone https://github.com/KunalParkhade/simplified-trading-bot.git
cd simplified-trading-bot/trading_bot

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API credentials
cp .env.example .env
# Open .env in your editor and fill in your testnet API key and secret
```

---

## Configuration

Edit the `.env` file you created above:

```env
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_BASE_URL=https://testnet.binancefuture.com
```

> **Security note:** `.env` is listed in `.gitignore` and will never be committed to version control.

---

## Usage Examples

All commands are run from the `trading_bot/` directory.

### Market Order – Buy

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

**Output:**

```
========================================
ORDER REQUEST SUMMARY
========================================
Symbol:       BTCUSDT
Side:         BUY
Type:         MARKET
Quantity:     0.001
========================================

Placing order...

========================================
ORDER RESPONSE
========================================
Order ID:     12345678
Status:       FILLED
Executed Qty: 0.001
Avg Price:    50000.00 USDT
Time:         2026-02-20 10:30:45
========================================
✓ Order placed successfully!
```

### Limit Order – Sell

```bash
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3500.50
```

### All CLI Arguments

| Argument | Required | Description |
|---|---|---|
| `--symbol` | Yes | Trading pair, e.g. `BTCUSDT` |
| `--side` | Yes | `BUY` or `SELL` |
| `--type` | Yes | `MARKET` or `LIMIT` |
| `--quantity` | Yes | Positive number |
| `--price` | Only for LIMIT | Positive number |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package init; re-exports key symbols
│   ├── client.py            # BinanceClient – HTTP + request signing
│   ├── orders.py            # execute_market_order / execute_limit_order
│   ├── validators.py        # validate_order_inputs and helpers
│   └── logging_config.py   # setup_logging() – console + rotating file
├── logs/                    # Created automatically at runtime
│   └── trading_bot.log
├── cli.py                   # CLI entry point (argparse)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `bot/client.py` | Low-level Binance REST API calls, HMAC signing, response parsing |
| `bot/orders.py` | Business logic, response normalisation, `OrderResult` dataclass |
| `bot/validators.py` | Input validation with clear error messages |
| `bot/logging_config.py` | One-shot logging setup: console (INFO) + rotating file (DEBUG) |
| `cli.py` | Argument parsing, user-facing I/O, orchestration |

---

## Logging

Logs are written to two destinations:

| Destination | Level | Location |
|---|---|---|
| Console | INFO | stdout |
| File | DEBUG | `logs/trading_bot.log` |

The log file rotates at **5 MB** and keeps up to **5** backup files (`trading_bot.log.1` … `.5`).

Log format:

```
[2026-02-20 10:30:45] INFO - bot.orders - Executing MARKET order | symbol=BTCUSDT side=BUY quantity=0.001
```

> API secrets are **never** written to logs. The request signature is always redacted.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Invalid CLI input | Validation error printed; non-zero exit |
| Missing credentials | Clear message with setup hint |
| Binance API error | Friendly message mapped from error code |
| Insufficient balance | User-friendly balance error |
| Rate limit hit | Retry hint printed |
| Network timeout | Exception logged; user informed |
| Unknown error | Stack trace in log file; brief message on console |

---

## Assumptions

1. **Testnet only** – the default base URL points to `testnet.binancefuture.com`. For live trading you would change `BINANCE_BASE_URL` in `.env` and ensure your key has the appropriate permissions.
2. **LIMIT orders use GTC** (Good Till Cancel) time-in-force; this can be changed in `bot/client.py`.
3. **No minimum notional enforcement** – Binance may reject very small orders; the bot passes through the API error as-is.
4. **Quantity precision** – the bot sends the quantity exactly as provided. Ensure it matches the symbol's step size or Binance will return error `-1111`.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `BINANCE_API_KEY … must be set` | Copy `.env.example` → `.env` and fill in credentials |
| `Invalid symbol` (error -1121) | Verify the symbol exists on the testnet (e.g. `BTCUSDT`, `ETHUSDT`) |
| `Insufficient balance` (error -2010) | Add funds to your testnet account at <https://testnet.binancefuture.com> |
| `Timestamp … outside of the recvWindow` | Check your system clock is synchronised (NTP) |
| `ModuleNotFoundError` | Activate your virtual environment and run `pip install -r requirements.txt` |
| Rate limit errors | Wait 1 minute and retry |
