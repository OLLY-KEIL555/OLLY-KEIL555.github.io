# Deriv Advanced Trading Bot

A fully automated trading bot for the Deriv platform that uses technical indicators to place trades and manage risk.

## Features

- **Technical Analysis**: Uses RSI, EMA, and Bollinger Bands to identify trading opportunities
- **Real-time Trading**: Connects to Deriv via WebSocket API for real-time data and trading
- **Risk Management**: Automatically calculates stake sizes based on account balance and risk percentage
- **Trade Tracking**: Logs all trades to CSV for performance analysis
- **Customizable**: Easily configure settings via the config.ini file
- **Paper Trading Mode**: Test strategies without risking real money
- **Interactive Console**: Monitor performance and control the bot in real-time

## Installation

1. Make sure you have Python 3.7+ installed
2. Clone or download this repository
3. Install dependencies:

```bash
pip install websocket-client pandas numpy
```

## Configuration

Before running the bot:

1. Create a configuration file with:

```bash
python trading_bot.py --setup
```

2. Edit the `config.ini` file with your Deriv API token (get it from [Deriv API Token page](https://app.deriv.com/account/api-token))
3. Adjust trading parameters like symbol, risk percentage, and trading hours

## Usage

### Start the bot with real trading:

```bash
python trading_bot.py
```

### Start in paper trading mode (no real trades):

```bash
python trading_bot.py --paper
```

### Commands during runtime:

- `status` - Display current bot status, balance, and performance
- `toggle` - Toggle between live trading and paper trading
- `quit` - Safely exit the bot

## Trading Strategy

The bot uses a combination of technical indicators:

1. **RSI (Relative Strength Index)**: Identifies overbought and oversold conditions
2. **EMA (Exponential Moving Average)**: Detects trend changes using 10 and 20 period EMAs
3. **Bollinger Bands**: Identifies price volatility and potential reversal points

### Buy (CALL) Conditions:
- RSI below 30 (oversold)
- EMA fast crosses above EMA slow
- Price at or below lower Bollinger Band

### Sell (PUT) Conditions:
- RSI above 70 (overbought)
- EMA fast crosses below EMA slow
- Price at or above upper Bollinger Band

## Risk Management

- Each trade risks only the specified percentage of your account balance
- Enforces a cooldown period between trades
- Limits trading to specific hours to avoid low-liquidity periods

## Trade Logging

All trades are logged to a CSV file with:
- Timestamp
- Direction (CALL/PUT)
- Stake amount
- Result (WIN/LOSS)
- Profit/Loss amount

## Disclaimer

Trading involves significant risk of loss. This bot is provided for educational purposes only and should not be used without understanding the risks involved. Use at your own risk.
