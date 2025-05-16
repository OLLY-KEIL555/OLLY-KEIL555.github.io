import asyncio
import json
import websockets
import time
from typing import Dict, Callable, List

# === CONFIGURATION ===
DERIV_API_TOKEN = "mZyBTUr3MQ0yB"  # Replace with your actual API token
DERIV_WS_URI = "wss://ws.derivws.com/websockets/v3"


class DerivWebSocketClient:
    def __init__(self, token: str):
        self.token = token
        self.ws = None
        self.connected = False
        self.authorized = False
        self.active_subscriptions = {}  # Track active subscriptions by ID
        self.message_handlers = {}  # Callback handlers for different message types

        # Register default handlers
        self.register_handler("ping", self._handle_ping)

    async def connect(self):
        try:
            self.ws = await websockets.connect(DERIV_WS_URI)
            self.connected = True
            print("Connected to Deriv WebSocket API.")

            # Authorize immediately after connecting
            await self.authorize()

            # Start the keep-alive ping task
            asyncio.create_task(self._keep_alive())

            return True
        except Exception as e:
            print(f"Connection error: {e}")
            self.connected = False
            return False

    async def reconnect(self):
        print("Attempting to reconnect...")
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass

        self.ws = None
        self.connected = False
        self.authorized = False

        # Try to reconnect with exponential backoff
        max_retries = 5
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

                print(f"Reconnection attempt {attempt + 1}/{max_retries}")
                if await self.connect():
                    print("Reconnected successfully!")

                    # Restore subscriptions
                    await self._restore_subscriptions()
                    return True
            except Exception as e:
                print(f"Reconnection attempt failed: {e}")

        print("Failed to reconnect after multiple attempts")
        return False

    async def _restore_subscriptions(self):
        """Restore all active subscriptions after reconnection"""
        if not self.active_subscriptions:
            return

        print(f"Restoring {len(self.active_subscriptions)} subscriptions...")

        restored = 0
        for sub_id, sub_request in list(self.active_subscriptions.items()):
            try:
                # Send the original subscription request again
                response = await self.send(sub_request)

                # Update subscription ID if successful
                if "subscription" in response:
                    new_id = response["subscription"]["id"]
                    self.active_subscriptions[new_id] = sub_request

                    # Remove old subscription ID if it's different
                    if new_id != sub_id:
                        self.active_subscriptions.pop(sub_id, None)

                    restored += 1
                else:
                    print(f"Failed to restore subscription: {sub_request}")
            except Exception as e:
                print(f"Error restoring subscription: {e}")

        print(
            f"Restored {restored}/{len(self.active_subscriptions)} subscriptions")

    async def _keep_alive(self):
        """Send periodic pings to keep the connection alive"""
        while self.connected:
            try:
                await asyncio.sleep(30)  # Send ping every 30 seconds
                if self.connected:
                    await self.send({"ping": 1})
            except Exception as e:
                print(f"Keep-alive error: {e}")
                if self.connected:  # Only try to reconnect if we think we're still connected
                    self.connected = False
                    asyncio.create_task(self.reconnect())
                break

    def _handle_ping(self, message):
        """Handle ping response"""
        if "ping" in message:
            # print("Ping response received")
            pass  # Just a keep-alive, no action needed

    async def send(self, payload: Dict):
        """Send a request to Deriv API"""
        if not self.connected:
            raise ConnectionError("WebSocket not connected")

        try:
            await self.ws.send(json.dumps(payload))
            return await self.receive()
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed unexpectedly")
            self.connected = False
            await self.reconnect()
            # Retry the send after reconnecting
            if self.connected:
                await self.ws.send(json.dumps(payload))
                return await self.receive()
            raise ConnectionError("Failed to reconnect")
        except Exception as e:
            print(f"Send error: {e}")
            raise

    async def receive(self) -> Dict:
        """Receive a single message"""
        if not self.connected:
            raise ConnectionError("WebSocket not connected")

        try:
            response = await self.ws.recv()
            return json.loads(response)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed while receiving")
            self.connected = False
            await self.reconnect()
            raise ConnectionError("Connection closed during receive")
        except Exception as e:
            print(f"Receive error: {e}")
            raise

    async def authorize(self):
        """Authorize with the Deriv API"""
        try:
            response = await self.send({"authorize": self.token})

            if response.get("msg_type") == "authorize":
                auth = response["authorize"]
                self.authorized = True
                print(
                    f"Authorized: {auth['loginid']} | Balance: {auth['balance']} {auth['currency']}")
                return auth
            else:
                error_msg = response.get("error", {}).get(
                    "message", "Unknown error")
                print(f"Authorization failed: {error_msg}")
                self.authorized = False
                return None
        except Exception as e:
            print(f"Authorization error: {e}")
            self.authorized = False
            return None

    async def get_balance(self, subscribe=False):
        """Get account balance, optionally subscribing to updates"""
        request = {"balance": 1}

        if subscribe:
            request["subscribe"] = 1

        response = await self.send(request)

        if response.get("msg_type") == "balance":
            balance = response["balance"]
            print(f"Balance: {balance['balance']} {balance['currency']}")

            # Store subscription if requested
            if subscribe and "subscription" in response:
                sub_id = response["subscription"]["id"]
                self.active_subscriptions[sub_id] = request

            return balance
        else:
            error_msg = response.get("error", {}).get(
                "message", "Unknown error")
            print(f"Balance fetch failed: {error_msg}")
            return None

    async def subscribe_ticks(self, symbol):
        """Subscribe to price ticks for a symbol"""
        if not self.authorized:
            print("Not authorized. Please authorize before subscribing.")
            return None

        request = {
            "ticks": symbol,
            "subscribe": 1
        }

        response = await self.send(request)

        if response.get("msg_type") == "tick":
            print(f"Subscribed to {symbol} ticks")

            # Store subscription
            if "subscription" in response:
                sub_id = response["subscription"]["id"]
                self.active_subscriptions[sub_id] = request

            return response["tick"]
        else:
            error_msg = response.get("error", {}).get(
                "message", "Unknown error")
            print(f"Tick subscription failed: {error_msg}")
            return None

    async def subscribe_candles(self, symbol, interval=60):
        """Subscribe to candles/OHLC for a symbol"""
        if not self.authorized:
            print("Not authorized. Please authorize before subscribing.")
            return None

        request = {
            "ticks_history": symbol,
            "style": "candles",
            "granularity": interval,  # in seconds
            "count": 10,  # initial candles
            "subscribe": 1
        }

        response = await self.send(request)

        if response.get("msg_type") == "candles":
            print(f"Subscribed to {symbol} candles with {interval}s interval")

            # Store subscription
            if "subscription" in response:
                sub_id = response["subscription"]["id"]
                self.active_subscriptions[sub_id] = request

            return response["candles"]
        else:
            error_msg = response.get("error", {}).get(
                "message", "Unknown error")
            print(f"Candle subscription failed: {error_msg}")
            return None

    def register_handler(self, msg_type: str, callback: Callable):
        """Register a callback for a specific message type"""
        self.message_handlers[msg_type] = callback

    async def process_messages(self):
        """Process incoming messages continuously"""
        if not self.connected:
            print("Not connected. Please connect first.")
            return

        print("Starting message processing loop...")
        try:
            while self.connected:
                try:
                    message = await self.receive()
                    msg_type = message.get("msg_type")

                    # Handle the message with registered callback if available
                    if msg_type in self.message_handlers:
                        self.message_handlers[msg_type](message)
                    else:
                        # Default handling based on message type
                        if msg_type == "tick":
                            tick = message["tick"]
                            print(f"Tick: {tick['symbol']} @ {tick['quote']}")
                        elif msg_type == "candle":
                            candle = message["candle"]
                            print(
                                f"Candle: {candle['symbol']} O:{candle['open']} H:{candle['high']} L:{candle['low']} C:{candle['close']}")
                        elif msg_type == "balance":
                            balance = message["balance"]
                            print(
                                f"Balance update: {balance['balance']} {balance['currency']}")
                        elif "error" in message:
                            print(f"Error: {message['error']['message']}")

                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed during message processing")
                    self.connected = False
                    await self.reconnect()
                    if not self.connected:
                        break
                except Exception as e:
                    print(f"Error processing message: {e}")

        except asyncio.CancelledError:
            print("Message processing cancelled")
        finally:
            print("Message processing loop ended")

    async def close(self):
        """Close the WebSocket connection"""
        self.connected = False
        if self.ws:
            await self.ws.close()
            self.ws = None
            print("Connection closed.")


async def main():
    client = DerivWebSocketClient(DERIV_API_TOKEN)

    try:
        # Connect to Deriv API
        await client.connect()

        # Get account balance and subscribe to updates
        await client.get_balance(subscribe=True)

        # Subscribe to ticks for a symbol
        await client.subscribe_ticks("R_100")

        # Subscribe to candles/OHLC for a symbol
        await client.subscribe_candles("R_100", interval=60)

        # Define a custom tick handler
        def handle_tick(message):
            tick = message["tick"]
            print(f"Custom handler: {tick['symbol']} price: {tick['quote']}")

        # Register the custom handler
        client.register_handler("tick", handle_tick)

        # Process messages in the background
        message_task = asyncio.create_task(client.process_messages())

        # Run for 5 minutes
        await asyncio.sleep(300)

        # Cancel message processing
        message_task.cancel()

    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Ensure connection is closed properly
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
