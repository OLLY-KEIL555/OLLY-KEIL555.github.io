import websocket
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import threading
import time
import os
import uuid
import sys
import configparser
import argparse
from deriv_api import DerivAPI

# === CONFIGURATION ===
# Default values - will be overridden by config.ini if available
API_TOKEN = "your_deriv_api_token"  # Replace this
SYMBOL = "R_100,R_10,R_25,R_50,R_75,R_100,R_10_1s,R_25_1s,R_50_1s,R_75_1s,R_100_1s,Boom_1000_Index,Boom_500_Index,Crash_1000_Index,Crash_500_Index,Step_Index,Jump_10_Index,Jump_25_Index,Jump_50_Index,Jump_75_Index,Jump_100_Index"
CANDLE_INTERVAL = 60  # 1-minute candles
MAX_CANDLES = 100
RISK_PERCENT = 2.0  # 2% per trade
TRADE_START_HOUR = 6  # UTC
TRADE_END_HOUR = 20  # UTC
TRADE_DURATION = 1  # in minutes
TRADE_LOG = "trade_log.csv"
ENABLE_TRADING = True  # Set to False for paper trading only

# === STATE VARIABLES ===
candles = []
authorized = False
balance = 0.0
last_trade_time = 0
cooldown_seconds = 120  # Wait 2 mins after a trade
active_trades = {}  # Track currently active trades
trade_count = 0
profit_today = 0.0
win_count = 0
loss_count = 0
bot_running = True

# === CONFIGURATION HANDLING ===


def load_config():
    global API_TOKEN, SYMBOL, CANDLE_INTERVAL, MAX_CANDLES, RISK_PERCENT
    global TRADE_START_HOUR, TRADE_END_HOUR, TRADE_DURATION, TRADE_LOG, ENABLE_TRADING

    # Create default config if not exists
    if not os.path.exists('config.ini'):
        create_default_config()

    config = configparser.ConfigParser()
    config.read('config.ini')

    # Load settings from config.ini
    API_TOKEN = config.get('API', 'token', fallback=API_TOKEN)
    SYMBOL = config.get('Trading', 'symbol', fallback=SYMBOL)
    CANDLE_INTERVAL = config.getint(
        'Trading', 'candle_interval', fallback=CANDLE_INTERVAL)
    MAX_CANDLES = config.getint('Trading', 'max_candles', fallback=MAX_CANDLES)
    RISK_PERCENT = config.getfloat(
        'Risk', 'risk_percent', fallback=RISK_PERCENT)
    TRADE_START_HOUR = config.getint(
        'Schedule', 'start_hour', fallback=TRADE_START_HOUR)
    TRADE_END_HOUR = config.getint(
        'Schedule', 'end_hour', fallback=TRADE_END_HOUR)
    TRADE_DURATION = config.getint(
        'Trading', 'duration', fallback=TRADE_DURATION)
    TRADE_LOG = config.get('Logs', 'trade_log', fallback=TRADE_LOG)
    ENABLE_TRADING = config.getboolean(
        'Trading', 'enable_trading', fallback=ENABLE_TRADING)


def create_default_config():
    config = configparser.ConfigParser()

    config['API'] = {
        'token': 'your_deriv_api_token'
    }

    config['Trading'] = {
        'symbol': 'R_100,R_10,R_25,R_50,R_75,R_100,R_10_1s,R_25_1s,R_50_1s,R_75_1s,R_100_1s,Boom_1000_Index,Boom_500_Index,Crash_1000_Index,Crash_500_Index,Step_Index,Jump_10_Index,Jump_25_Index,Jump_50_Index,Jump_75_Index,Jump_100_Index',
        'candle_interval': '60',
        'max_candles': '100',
        'duration': '1',
        'enable_trading': 'True'
    }

    config['Risk'] = {
        'risk_percent': '2.0'
    }

    config['Schedule'] = {
        'start_hour': '6',
        'end_hour': '20'
    }

    config['Logs'] = {
        'trade_log': 'trade_log.csv'
    }

    with open('config.ini', 'w') as f:
        config.write(f)

    print("[SETUP] Created default config.ini - please edit with your API token")

# === FILE LOGGING ===


def log_trade(time_str, direction, stake, result="PENDING", contract_id=None, profit=None):
    if not os.path.exists(TRADE_LOG):
        with open(TRADE_LOG, "w") as f:
            f.write("time,direction,stake,result,contract_id,profit\n")

    profit_str = str(profit) if profit is not None else ""
    contract_str = str(contract_id) if contract_id is not None else ""

    with open(TRADE_LOG, "a") as f:
        f.write(
            f"{time_str},{direction},{stake},{result},{contract_str},{profit_str}\n")

    # Print trade information
    if result != "PENDING":
        result_color = "\033[92m" if result == "WIN" else "\033[91m" if result == "LOSS" else "\033[93m"
        reset_color = "\033[0m"
        profit_info = f" | Profit: {profit}" if profit is not None else ""
        print(
            f"{result_color}[TRADE RESULT] {direction} | ${stake} | {result}{profit_info}{reset_color}")

# === NEWS FILTER (PLACEHOLDER) ===


def is_news_time():
    # Placeholder: In real case, call a news API and filter.
    return False

# === TIME FILTER ===


def is_within_trading_hours():
    now = datetime.now(timezone.utc)
    return TRADE_START_HOUR <= now.hour < TRADE_END_HOUR

# === CALCULATE INDICATORS ===


def calculate_rsi(data, window=14):
    """Calculate RSI indicator manually"""
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rsi = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rsi))
    return rsi


def calculate_ema(data, span):
    """Calculate EMA indicator manually"""
    return data.ewm(span=span, adjust=False).mean()


def calculate_bollinger_bands(data, window=20, num_std=2):
    """Calculate Bollinger Bands manually"""
    sma = data.rolling(window=window).mean()
    std = data.rolling(window=window).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, lower


def calculate_signals(df):
    # Calculate indicators manually instead of using ta library
    df['rsi'] = calculate_rsi(df['close'], window=14)
    df['ema_fast'] = calculate_ema(df['close'], span=10)
    df['ema_slow'] = calculate_ema(df['close'], span=20)
    df['bb_upper'], df['bb_lower'] = calculate_bollinger_bands(
        df['close'], window=20, num_std=2)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # BUY CONDITIONS
    buy = (
        last['rsi'] < 30 and
        prev['ema_fast'] < prev['ema_slow'] and
        last['ema_fast'] > last['ema_slow'] and
        last['close'] <= last['bb_lower']
    )

    # SELL CONDITIONS
    sell = (
        last['rsi'] > 70 and
        prev['ema_fast'] > prev['ema_slow'] and
        last['ema_fast'] < last['ema_slow'] and
        last['close'] >= last['bb_upper']
    )

    return 'CALL' if buy else 'PUT' if sell else None

# === RISK MANAGEMENT ===


def calculate_stake():
    global balance
    return round((RISK_PERCENT / 100) * balance, 2)

# === EXECUTE TRADE ===


def execute_trade(ws, direction):
    global last_trade_time, trade_count, active_trades

    # Check cooldown
    now = int(time.time())
    if now - last_trade_time < cooldown_seconds:
        print("[COOLDOWN] Skipping trade - cooldown active.")
        return

    # Check if trading is enabled
    if not ENABLE_TRADING:
        print(
            f"[PAPER TRADE] {direction} | Paper trading mode - no real trade executed")
        return

    # Calculate risk-managed stake amount
    stake = calculate_stake()
    if stake < 1.0:  # Minimum stake amount for Deriv
        print(
            f"[RISK WARNING] Stake ${stake} below minimum - using minimum stake")
        stake = 1.0

    # Generate a unique request ID
    req_id = str(uuid.uuid4())

    # Create payload
    payload = {
        "buy": 1,
        "price": stake,
        "parameters": {
            "amount": stake,
            "basis": "stake",
            "contract_type": direction,
            "currency": "USD",
            "duration": TRADE_DURATION,
            "duration_unit": "m",
            "symbol": SYMBOL
        },
        "req_id": req_id  # Fixed: Added comma and fixed formatting
    }

    # Store trade in active trades with request ID
    trade_entry = {
        "direction": direction,
        "stake": stake,
        "time": datetime.utcnow().isoformat(),
        "status": "PENDING"
    }
    active_trades[req_id] = trade_entry

    # Send trade to Deriv
    ws.send(json.dumps(payload))

    # Update state
    last_trade_time = now
    trade_count += 1

    # Log trade
    print(f"[TRADE #{trade_count}] Sent {direction} | Stake: ${stake}")
    log_trade(trade_entry["time"], direction, stake, contract_id=req_id)

# === WEBSOCKET CALLBACKS ===


def on_open(ws):
    print("[CONNECTED] Subscribing...")
    ws.send(json.dumps({"authorize": API_TOKEN}))


def on_message(ws, message):
    global candles, authorized, balance, active_trades, profit_today, win_count, loss_count

    try:
        data = json.loads(message)
        msg_type = data.get("msg_type")

        # Handle authorization response
        if msg_type == "authorize":
            authorized = True
            print("[AUTHORIZED] Connection established successfully")

            # Get account balance
            ws.send(json.dumps({"balance": 1, "subscribe": 1}))

            # Subscribe to price candles
            ws.send(json.dumps({
                "ticks_history": SYMBOL,
                "adjust_start_time": 1,
                "count": MAX_CANDLES,
                "granularity": CANDLE_INTERVAL,
                "style": "candles",
                "subscribe": 1
            }))

            # Get open positions to resume tracking
            ws.send(json.dumps({"proposal_open_contract": 1, "subscribe": 1}))

        # Handle balance updates
        elif msg_type == "balance":
            balance = float(data['balance']['balance'])
            print(f"[BALANCE] ${balance}")

        # Handle candle updates
        elif msg_type == "candles":
            candles_data = data['candles']
            candles = candles_data[-MAX_CANDLES:]
            evaluate_and_trade(ws)

        # Handle buy trade response
        elif msg_type == "buy":
            if data["error"]:
                print(f"[TRADE ERROR] {data['error']['message']}")
                # Remove failed trade from active trades
                req_id = data.get("req_id")
                if req_id and req_id in active_trades:
                    trade_info = active_trades.pop(req_id)
                    log_trade(
                        trade_info["time"],
                        trade_info["direction"],
                        trade_info["stake"],
                        "FAILED",
                        req_id
                    )
            else:
                # Update active trade with contract ID
                req_id = data.get("req_id")
                contract_id = data["buy"]["contract_id"]
                if req_id and req_id in active_trades:
                    active_trades[req_id]["contract_id"] = contract_id
                    print(f"[TRADE CONFIRMED] Contract ID: {contract_id}")

                    # Set up a subscription to monitor this specific contract
                    ws.send(json.dumps({
                        "proposal_open_contract": 1,
                        "contract_id": contract_id,
                        "subscribe": 1
                    }))

        # Handle contract updates
        elif msg_type == "proposal_open_contract":
            contract = data.get("proposal_open_contract", {})
            if not contract:
                return

            contract_id = contract.get("contract_id")
            if not contract_id:
                return

            # Find the trade in active_trades by contract_id
            matching_trades = [(req_id, trade_info) for req_id, trade_info in active_trades.items()
                               if trade_info.get("contract_id") == contract_id]

            if matching_trades:
                req_id, trade_info = matching_trades[0]

                # Only process if this is a completion update
                if contract.get("is_sold", 0) == 1:
                    # Calculate profit
                    buy_price = contract.get("buy_price", 0)
                    sell_price = contract.get("sell_price", 0)
                    profit = sell_price - buy_price
                    profit_today += profit

                    # Determine win/loss
                    result = "WIN" if profit > 0 else "LOSS"
                    if result == "WIN":
                        win_count += 1
                    else:
                        loss_count += 1

                    # Update logs
                    log_trade(
                        trade_info["time"],
                        trade_info["direction"],
                        trade_info["stake"],
                        result,
                        contract_id,
                        profit
                    )

                    # Remove from active trades
                    active_trades.pop(req_id, None)

                    # Display stats
                    win_rate = (win_count / (win_count + loss_count)) * \
                        100 if (win_count + loss_count) > 0 else 0
                    print(
                        f"[STATS] Win Rate: {win_rate:.1f}% | P/L Today: ${profit_today:.2f}")

    except Exception as e:
        print(f"[ERROR] Message processing error: {str(e)}")
        print(f"Message: {message[:100]}...")


def evaluate_and_trade(ws):
    if not is_within_trading_hours():
        print("[TIME FILTER] Outside trading hours.")
        return
    if is_news_time():
        print("[NEWS FILTER] High impact news time.")
        return
    if len(candles) < 21:
        print("[DATA] Not enough candles yet.")
        return

    df = pd.DataFrame(candles)
    # Make sure to convert 'close' to float if it's not already - handle potential errors
    try:
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        # Drop NaN values if any conversion failed
        df = df.dropna(subset=['close'])
        if len(df) < 21:
            print("[DATA] Not enough valid candles after cleaning.")
            return
    except Exception as e:
        print(f"[ERROR] Error preprocessing data: {e}")
        return

    try:
        signal = calculate_signals(df)
        if signal:
            execute_trade(ws, signal)
        else:
            print("[SIGNAL] No valid setup.")
    except Exception as e:
        print(f"[ERROR] Error calculating signals: {e}")


def on_error(ws, error):
    print("[ERROR]", error)


def on_close(ws, close_status_code, close_msg):
    print("[DISCONNECTED]", close_status_code, close_msg)


# === BOT COMMANDS ===
def print_status():
    """Display current bot status"""
    global balance, profit_today, trade_count, win_count, loss_count, active_trades

    # Calculate win rate
    win_rate = (win_count / (win_count + loss_count)) * \
        100 if (win_count + loss_count) > 0 else 0

    # Print status header
    print("\n" + "="*50)
    print(
        f"DERIV TRADING BOT STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    # Account info
    print(
        f"Symbol: {SYMBOL} | Balance: ${balance:.2f} | P/L Today: ${profit_today:.2f}")

    # Performance metrics
    print(
        f"Trades Today: {trade_count} | Win Rate: {win_rate:.1f}% ({win_count}/{win_count+loss_count})")

    # Active trades
    print(f"Active Trades: {len(active_trades)}")
    for req_id, trade in active_trades.items():
        contract_id = trade.get("contract_id", "pending")
        print(
            f" - {trade['direction']} | ${trade['stake']} | ID: {contract_id}")

    # Trading schedule
    trading_enabled = "ENABLED" if ENABLE_TRADING else "DISABLED (Paper Trading)"
    print(
        f"Trading: {trading_enabled} | Hours: {TRADE_START_HOUR}:00-{TRADE_END_HOUR}:00 UTC")
    print("="*50)


def command_handler():
    """Handle user commands while bot is running"""
    global bot_running, ENABLE_TRADING

    print("\nCommands: status, toggle, quit")

    while bot_running:
        try:
            cmd = input("> ").strip().lower()

            if cmd == "status":
                print_status()
            elif cmd == "toggle":
                ENABLE_TRADING = not ENABLE_TRADING
                status = "ENABLED" if ENABLE_TRADING else "DISABLED (Paper Trading)"
                print(f"[COMMAND] Trading {status}")
            elif cmd == "quit":
                print("[COMMAND] Shutting down bot...")
                bot_running = False
                break
            else:
                print("Available commands: status, toggle, quit")
        except Exception as e:
            print(f"[ERROR] Command error: {e}")


# === CONNECTION MANAGEMENT ===
def maintain_connection(ws):
    """Keep websocket connection alive with ping/pong"""
    while bot_running:
        try:
            ws.send(json.dumps({"ping": 1}))
            time.sleep(30)
        except Exception:
            break


# === RUN BOT ===
def run_bot():
    global bot_running

    # Use enableTrace for debugging if needed
    # websocket.enableTrace(True)

    print("[STARTUP] Connecting to Deriv WebSocket API...")
    ws = websocket.WebSocketApp(
        "wss://ws.deriv.com/websockets/v3",  # Fixed URL
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # Start keep alive thread
    ping_thread = threading.Thread(target=maintain_connection, args=(ws,))
    ping_thread.daemon = True
    ping_thread.start()

    # Run WebSocket connection in a loop for resilience
    while bot_running:
        try:
            ws.run_forever()
            if not bot_running:
                break
            print("[RECONNECT] Connection lost. Reconnecting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"[CRITICAL] WebSocket error: {e}")
            if not bot_running:
                break
            print("[RECONNECT] Attempting to reconnect in 10 seconds...")
            time.sleep(10)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Deriv Trading Bot')
    parser.add_argument('--paper', action='store_true',
                        help='Run in paper trading mode (no real trades)')
    parser.add_argument('--setup', action='store_true',
                        help='Create default config file and exit')
    args = parser.parse_args()

    # Handle setup mode
    if args.setup:
        create_default_config()
        print(
            "[SETUP] Configuration file created. Please edit config.ini with your API token.")
        sys.exit(0)

    print("\n===== DERIV ADVANCED TRADING BOT =====")
    print("Starting up...")

    try:
        # Install required packages if they aren't already installed
        import subprocess

        required_packages = ["websocket-client", "pandas", "numpy"]
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"[SETUP] {package} is already installed")
            except ImportError:
                print(f"[SETUP] Installing {package}...")
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package])

        # Load configuration
        load_config()

        # Override trading mode if specified
        if args.paper:
            ENABLE_TRADING = False
            print("[CONFIG] Paper trading mode enabled via command line")

        if API_TOKEN == "your_deriv_api_token":
            print(
                "[ERROR] API token not set. Please edit config.ini with your Deriv API token.")
            sys.exit(1)

        # Start the bot in a separate thread
        print("[STARTUP] Launching trading bot...")
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()

        # Start command handler in main thread
        print("[STARTUP] Bot started successfully. Type 'status' for information or 'help' for commands.")
        command_handler()

    except KeyboardInterrupt:
        print("\n[SYSTEM] Bot shutdown initiated by user")
        bot_running = False
    except Exception as e:
        print(f"[CRITICAL] Main thread error: {e}")

    print("[SHUTDOWN] Exiting bot. Please wait...")
    bot_running = False
