import asyncio
import websockets
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

# Set up logging with a more reliable path


def setup_logging():
    """Configure logging to write to a file in user's home directory and console."""
    # Create logs directory in user's home directory if it doesn't exist
    log_dir = os.path.join(os.path.expanduser("~"), "deriv_bot_logs")
    os.makedirs(log_dir, exist_ok=True)

    # Configure log file path
    log_file = os.path.join(log_dir, "deriv_bot.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("DerivBot")


# Initialize logger
logger = setup_logging()


class DerivBot:
    """A bot for trading on the Deriv platform using WebSocket API."""

    def __init__(self, api_token: str, symbols: List[str], base_url: str = "wss://ws.derivws.com/websockets/v3"):
        """
        Initialize the Deriv trading bot.

        Args:
            api_token: Your Deriv API token
            symbols: List of trading symbols to subscribe to
            base_url: The Deriv WebSocket API URL
        """
        self.api_token = api_token
        self.symbols = symbols
        self.base_url = base_url
        self.websocket = None
        self.authorized = False
        self.subscriptions = {}
        self.account_info = {}

    async def connect(self) -> None:
        """Establish a WebSocket connection to the Deriv API."""
        try:
            self.websocket = await websockets.connect(self.base_url)
            logger.info("Connected to Deriv WebSocket API")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise

    async def authorize(self) -> bool:
        """Authorize with the Deriv API using the provided token."""
        if not self.websocket:
            await self.connect()

        try:
            await self.websocket.send(json.dumps({"authorize": self.api_token}))
            response = json.loads(await self.websocket.recv())

            if "error" in response:
                logger.error(
                    f"Authorization failed: {response['error']['message']}")
                return False

            self.authorized = True
            self.account_info = response.get("authorize", {})
            logger.info(
                f"Successfully authorized as {self.account_info.get('email', 'Unknown')}")
            return True

        except Exception as e:
            logger.error(f"Authorization error: {e}")
            return False

    async def get_balance(self) -> Optional[Dict[str, Any]]:
        """Get the current account balance."""
        if not self.authorized:
            logger.warning("Not authorized, cannot get balance")
            return None

        try:
            await self.websocket.send(json.dumps({"balance": 1, "subscribe": 1}))
            response = json.loads(await self.websocket.recv())

            if "error" in response:
                logger.error(
                    f"Balance retrieval failed: {response['error']['message']}")
                return None

            balance_data = response.get("balance", {})
            logger.info(
                f"Balance: {balance_data.get('balance')} {balance_data.get('currency')}")
            return balance_data

        except Exception as e:
            logger.error(f"Balance retrieval error: {e}")
            return None

    async def subscribe_to_ticks(self, symbol: str) -> bool:
        """Subscribe to price ticks for a specific symbol."""
        if not self.authorized:
            logger.warning(f"Not authorized, cannot subscribe to {symbol}")
            return False

        try:
            await self.websocket.send(json.dumps({"ticks": symbol, "subscribe": 1}))
            response = json.loads(await self.websocket.recv())

            if "error" in response:
                logger.error(
                    f"Subscription to {symbol} failed: {response['error']['message']}")
                return False

            self.subscriptions[symbol] = response.get(
                "subscription", {}).get("id")
            logger.info(f"Successfully subscribed to {symbol}")
            return True

        except Exception as e:
            logger.error(f"Subscription error for {symbol}: {e}")
            return False

    async def place_trade(self, symbol: str, contract_type: str, stake: float, duration: int, duration_unit: str) -> Optional[Dict[str, Any]]:
        """
        Place a trade on a specific symbol.

        Args:
            symbol: The symbol to trade on (e.g., 'R_100')
            contract_type: 'CALL' for rise, 'PUT' for fall
            stake: Amount to stake in account currency
            duration: Time duration for the contract
            duration_unit: 't' for ticks, 's' for seconds, 'm' for minutes, 'h' for hours, 'd' for days

        Returns:
            The trade confirmation details if successful, None otherwise
        """
        if not self.authorized:
            logger.warning("Not authorized, cannot place trade")
            return None

        try:
            contract_request = {
                "buy": 1,
                "price": stake,
                "parameters": {
                    "amount": stake,
                    "basis": "stake",
                    "contract_type": contract_type,
                    "currency": self.account_info.get("currency", "USD"),
                    "duration": duration,
                    "duration_unit": duration_unit,
                    "symbol": symbol
                }
            }

            logger.info(
                f"Placing {contract_type} trade on {symbol} for {stake} {self.account_info.get('currency', 'USD')}")
            await self.websocket.send(json.dumps(contract_request))
            response = json.loads(await self.websocket.recv())

            if "error" in response:
                logger.error(
                    f"Trade placement failed: {response['error']['message']}")
                return None

            trade_details = response.get("buy", {})
            logger.info(
                f"Trade placed successfully: Contract ID {trade_details.get('contract_id')}")
            return trade_details

        except Exception as e:
            logger.error(f"Trade placement error: {e}")
            return None

    async def process_tick(self, tick_data: Dict[str, Any]) -> None:
        """Process incoming tick data, can be extended for implementing trading strategies."""
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote")
        timestamp = tick_data.get("epoch")

        if symbol and price and timestamp:
            formatted_time = datetime.fromtimestamp(
                timestamp).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{symbol} | Price: {price} | Time: {formatted_time}")

            # You can implement your trading strategy here
            # For example, track price movements and make trading decisions

    async def run(self) -> None:
        """Main method to run the bot."""
        try:
            # Connect and authorize
            await self.connect()
            if not await self.authorize():
                logger.error("Authorization failed, exiting")
                return

            # Get account balance
            await self.get_balance()

            # Subscribe to multiple ticks
            for symbol in self.symbols:
                await self.subscribe_to_ticks(symbol)

            # Optional: Place a sample trade
            # Uncomment if you want to place an actual trade
            # await self.place_trade(self.symbols[0], "CALL", 1.0, 5, "t")

            # Listen for incoming messages
            while True:
                response = json.loads(await self.websocket.recv())
                msg_type = response.get("msg_type")

                if msg_type == "tick":
                    await self.process_tick(response["tick"])
                elif msg_type == "balance":
                    balance_data = response.get("balance", {})
                    logger.info(
                        f"Balance update: {balance_data.get('balance')} {balance_data.get('currency')}")
                elif "error" in response:
                    logger.error(
                        f"Received error: {response['error']['message']}")

        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"WebSocket connection closed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            if self.websocket:
                await self.websocket.close()
                logger.info("WebSocket connection closed")


async def main():
    # Configure your bot
    API_TOKEN = "YOUR_DERIV_API_TOKEN"  # Replace with your actual token
    SYMBOLS = ["R_100,R_10_1s,R_25_1s,R_50_1s,R_75_1s,R_100_1s,Boom_1000_Index,Boom_500_Index,Crash_1000_Index,Crash_500_Index,Step_Index,Jump_10_Index,Jump_25_Index,Jump_50_Index,Jump_75_Index,Jump_100_Inde"]  # Synthetic indices

    # Create and run the bot
    bot = DerivBot(API_TOKEN, SYMBOLS)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
