from core.exchange_interface import Exchange
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

class BinanceConnector(Exchange):
    """
    Connector for the Binance exchange.
    Implements the Exchange interface for Binance-specific functionalities
    using the python-binance library.
    """

    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Initializes the BinanceConnector.

        Args:
            api_key: The API key for Binance authentication.
            api_secret: The API secret for Binance authentication.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = None
        print("BinanceConnector initialized.")

    def connect(self, api_key: str = None, api_secret: str = None) -> bool:
        """
        Connects to the Binance exchange using the provided API key and secret.
        If api_key and api_secret are not provided, it uses the ones from __init__.

        Args:
            api_key: The API key for Binance authentication.
            api_secret: The API secret for Binance authentication.

        Returns:
            True if connection is successful, False otherwise.

        Raises:
            ConnectionError: If the connection to Binance fails.
        """
        if api_key:
            self.api_key = api_key
        if api_secret:
            self.api_secret = api_secret

        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret must be provided either during initialization or connect call.")

        print(f"Connecting to Binance with API key: {self.api_key[:5]}...") # Print only partial key for security
        try:
            self.client = Client(self.api_key, self.api_secret)
            # Test connection by pinging the server
            self.client.ping()
            server_time = self.client.get_server_time()
            print(f"Successfully connected to Binance. Server time: {server_time['serverTime']}")
            return True
        except BinanceAPIException as e:
            print(f"Binance API Exception: {e}")
            raise ConnectionError(f"Failed to connect to Binance due to API error: {e}")
        except BinanceRequestException as e:
            print(f"Binance Request Exception: {e}")
            raise ConnectionError(f"Failed to connect to Binance due to request error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during connection: {e}")
            raise ConnectionError(f"An unexpected error occurred: {e}")

    def disconnect(self) -> bool:
        """
        Disconnects from the Binance exchange.
        For python-binance, this primarily means clearing the client instance.
        Actual websocket connections would need explicit closing if used.

        Returns:
            True.
        """
        print("Disconnecting from Binance.")
        self.client = None
        # Add any websocket specific disconnection logic here in the future
        return True

    def get_account_balance(self) -> dict[str, str]:
        """
        Retrieves the account balance from Binance.

        Returns:
            A dictionary where keys are asset symbols (e.g., 'BTC')
            and values are their respective 'free' (available) amounts as strings.

        Raises:
            ConnectionError: If the client is not connected.
            RuntimeError: If there's an API error or other issue fetching the balance.
        """
        if not self.client:
            raise ConnectionError("Client not connected. Please call connect() first.")

        print("Retrieving account balance from Binance...")
        try:
            account_info = self.client.get_account()
            balances = {}
            if 'balances' in account_info:
                for asset_balance in account_info['balances']:
                    # Store only assets with a non-zero free amount
                    if float(asset_balance['free']) > 0:
                        balances[asset_balance['asset']] = asset_balance['free']

            if not balances:
                print("No non-zero balances found or 'balances' key missing in response.")
            else:
                print(f"Account balances retrieved: {balances}")
            return balances
        except BinanceAPIException as e:
            print(f"Binance API Exception while fetching account balance: {e}")
            raise RuntimeError(f"Failed to get account balance due to API error: {e}")
        except BinanceRequestException as e:
            print(f"Binance Request Exception while fetching account balance: {e}")
            raise RuntimeError(f"Failed to get account balance due to request error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while fetching account balance: {e}")
            raise RuntimeError(f"An unexpected error occurred while fetching account balance: {e}")

    def get_market_data(self, symbol: str) -> dict[str, str]:
        """
        Retrieves market data (latest price and 24h volume) for a specific trading symbol from Binance.
        Symbol should be in Binance format, e.g., 'BTCUSDT'.

        Args:
            symbol: The trading symbol (e.g., 'BTCUSDT').

        Returns:
            A dictionary containing market data:
            {'price': 'current_price', 'volume_24h': 'total_traded_base_asset_volume_in_24hr'}

        Raises:
            ConnectionError: If the client is not connected.
            ValueError: If the symbol format is invalid (e.g., contains '/').
            RuntimeError: If there's an API error or other issue fetching market data.
        """
        if not self.client:
            raise ConnectionError("Client not connected. Please call connect() first.")

        if '/' in symbol:
            raise ValueError("Symbol format is invalid. Use format like 'BTCUSDT', not 'BTC/USDT'.")

        print(f"Retrieving market data for {symbol} from Binance...")
        try:
            # Get latest price
            ticker_data = self.client.get_symbol_ticker(symbol=symbol)
            latest_price = ticker_data.get('price')

            # Get 24hr Klines for volume
            # The klines data format:
            # [
            #   [
            #     1499040000000,      // Open time
            #     "0.01634790",       // Open
            #     "0.80000000",       // High
            #     "0.01575800",       // Low
            #     "0.01577100",       // Close
            #     "148976.11427815",  // Volume (Base asset volume)
            #     1499644799999,      // Close time
            #     "2434.19055334",    // Quote asset volume
            #     308,                // Number of trades
            #     "1756.87402397",    // Taker buy base asset volume
            #     "28.46694368",      // Taker buy quote asset volume
            #     "17928899.62484339" // Ignore.
            #   ]
            # ]
            # We need the 'Volume' (index 5) from the most recent daily kline.
            # Using get_klines instead of get_historical_klines as it's simpler for recent data.
            # Limit to 1 to get the most recent completed + current ongoing kline data.
            # For 24hr volume, get_24hr_ticker might be more direct if precision requirements are met.
            # Let's use get_ticker for simplicity for 24h volume.
            # Example: {'symbol': 'BTCUSDT', 'priceChange': ..., 'volume': '24H_VOLUME_IN_BASE_ASSET', ...}

            # Alternative: Use get_24hr_ticker for volume
            # This provides volume in base asset for the last 24 hours.
            ticker_24hr_data = self.client.get_ticker(symbol=symbol)
            volume_24h = ticker_24hr_data.get('volume') # This is 'volume' in base asset
            # quote_volume_24h = ticker_24hr_data.get('quoteVolume') # This is 'quoteVolume'

            if latest_price is None or volume_24h is None:
                raise RuntimeError(f"Could not retrieve complete market data for {symbol}. "
                                   f"Price: {latest_price}, Volume: {volume_24h}")

            market_data = {
                'price': latest_price,
                'volume_24h': volume_24h
            }
            print(f"Market data for {symbol}: {market_data}")
            return market_data

        except BinanceAPIException as e:
            print(f"Binance API Exception while fetching market data for {symbol}: {e}")
            raise RuntimeError(f"Failed to get market data for {symbol} due to API error: {e}")
        except BinanceRequestException as e:
            print(f"Binance Request Exception while fetching market data for {symbol}: {e}")
            raise RuntimeError(f"Failed to get market data for {symbol} due to request error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while fetching market data for {symbol}: {e}")
            raise RuntimeError(f"An unexpected error occurred while fetching market data for {symbol}: {e}")

    def place_order(self, symbol: str, side: str, order_type: str, amount: float, price: float = None) -> dict:
        """
        Places a new order on Binance.
        Symbol should be in Binance format, e.g., 'BTCUSDT'.
        Side should be 'BUY' or 'SELL'.
        Order_type should be 'LIMIT' or 'MARKET'.

        Args:
            symbol: The trading symbol (e.g., 'BTCUSDT').
            side: The order side ('BUY' or 'SELL').
            order_type: The order type ('LIMIT' or 'MARKET').
            amount: The quantity of the asset to trade.
            price: The price for LIMIT orders (required for LIMIT, ignored for MARKET).

        Returns:
            A dictionary containing order information, e.g.,
            {'order_id': '12345', 'status': 'NEW', 'symbol': 'BTCUSDT', ... (other fields from response)}

        Raises:
            ConnectionError: If the client is not connected.
            ValueError: If any of the arguments are invalid.
            RuntimeError: If there's an API error or other issue placing the order.
        """
        if not self.client:
            raise ConnectionError("Client not connected. Please call connect() first.")

        # Argument validation
        if '/' in symbol: # Basic symbol validation, more specific checks done by API
            raise ValueError("Symbol format is invalid. Use format like 'BTCUSDT', not 'BTC/USDT'.")
        if side.upper() not in ['BUY', 'SELL']:
            raise ValueError("Order side must be 'BUY' or 'SELL'.")
        if order_type.upper() not in ['LIMIT', 'MARKET']:
            raise ValueError("Order type must be 'LIMIT' or 'MARKET'.")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Order amount must be a positive number.")

        side_upper = side.upper()
        order_type_upper = order_type.upper()

        if order_type_upper == 'LIMIT':
            if price is None or (not isinstance(price, (int, float)) or price <= 0):
                raise ValueError("Price must be a positive number for LIMIT orders.")

        print(f"Placing {order_type_upper} {side_upper} order for {amount} of {symbol} "
              f"{('at price ' + str(price)) if order_type_upper == 'LIMIT' else ''} on Binance.")

        try:
            order_response = None
            if order_type_upper == 'LIMIT':
                if side_upper == 'BUY':
                    order_response = self.client.order_limit_buy(
                        symbol=symbol,
                        quantity=amount,
                        price=str(price) # API expects price as string
                    )
                else: # SELL
                    order_response = self.client.order_limit_sell(
                        symbol=symbol,
                        quantity=amount,
                        price=str(price)
                    )
            elif order_type_upper == 'MARKET':
                if side_upper == 'BUY':
                    # For MARKET BUY, quantity can be quoteOrderQty (total USDT to spend)
                    # or quantity (amount of BTC to buy).
                    # Using quantity for consistency with LIMIT orders for now.
                    # Consider adding quoteOrderQty support if needed.
                    order_response = self.client.order_market_buy(
                        symbol=symbol,
                        quantity=amount
                    )
                else: # SELL
                    order_response = self.client.order_market_sell(
                        symbol=symbol,
                        quantity=amount
                    )

            if not order_response or 'orderId' not in order_response:
                raise RuntimeError(f"Order placement failed or received unexpected response: {order_response}")

            # Standardize response slightly if needed, or return as is.
            # Example: {'orderId': 123, 'status': 'NEW', ...}
            # The actual response is quite detailed.
            formatted_response = {
                'order_id': str(order_response.get('orderId')),
                'status': order_response.get('status'),
                'symbol': order_response.get('symbol'),
                'type': order_response.get('type'),
                'side': order_response.get('side'),
                'price': order_response.get('price'),
                'orig_qty': order_response.get('origQty'),
                'executed_qty': order_response.get('executedQty'),
                'cummulative_quote_qty': order_response.get('cummulativeQuoteQty'),
                'client_order_id': order_response.get('clientOrderId'),
                'transact_time': order_response.get('transactTime'),
                'raw_response': order_response # Include the full response
            }
            print(f"Order placed successfully: {formatted_response['order_id']}, Status: {formatted_response['status']}")
            return formatted_response

        except BinanceAPIException as e:
            print(f"Binance API Exception while placing order: {e}")
            raise RuntimeError(f"Failed to place order due to API error: {e}")
        except BinanceRequestException as e:
            print(f"Binance Request Exception while placing order: {e}")
            raise RuntimeError(f"Failed to place order due to request error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while placing order: {e}")
            raise RuntimeError(f"An unexpected error occurred while placing order: {e}")

    def cancel_order(self, order_id: str, symbol: str) -> dict:
        """
        Cancels an existing order on Binance.
        Symbol must be in Binance format, e.g., 'BTCUSDT'.

        Args:
            order_id: The ID of the order to cancel.
            symbol: The trading symbol of the order to cancel (e.g., 'BTCUSDT').

        Returns:
            A dictionary containing details of the cancelled order, similar to place_order's response,
            e.g., {'order_id': '12345', 'status': 'CANCELED', 'symbol': 'BTCUSDT', ...}

        Raises:
            ConnectionError: If the client is not connected.
            ValueError: If any of the arguments are invalid.
            RuntimeError: If there's an API error (e.g., order not found, already filled) or other issue.
        """
        if not self.client:
            raise ConnectionError("Client not connected. Please call connect() first.")

        if not order_id: # order_id can be string or int, API handles specific format.
            raise ValueError("Order ID must be provided.")
        if not symbol or '/' in symbol: # Basic symbol validation
            raise ValueError("Valid symbol (e.g., 'BTCUSDT') must be provided.")

        print(f"Cancelling order {order_id} for symbol {symbol} on Binance.")
        try:
            cancel_response = self.client.cancel_order(
                symbol=symbol,
                orderId=order_id
            )

            if not cancel_response or 'orderId' not in cancel_response:
                raise RuntimeError(f"Order cancellation failed or received unexpected response: {cancel_response}")

            # The response for a successful cancel is similar to an order placement/query response
            formatted_response = {
                'order_id': str(cancel_response.get('orderId')),
                'status': cancel_response.get('status'),
                'symbol': cancel_response.get('symbol'),
                'type': cancel_response.get('type'),
                'side': cancel_response.get('side'),
                'price': cancel_response.get('price'),
                'orig_qty': cancel_response.get('origQty'),
                'executed_qty': cancel_response.get('executedQty'),
                'cummulative_quote_qty': cancel_response.get('cummulativeQuoteQty'),
                'client_order_id': cancel_response.get('clientOrderId'),
                # transact_time might not be present in cancel response, check API docs
                'raw_response': cancel_response
            }
            print(f"Order {order_id} for {symbol} cancelled successfully. Status: {formatted_response['status']}")
            return formatted_response

        except BinanceAPIException as e:
            # Example error codes for cancel:
            # -2011: "Unknown order sent." (Order not found, or already filled/cancelled)
            # -2013: "Order does not exist."
            print(f"Binance API Exception while cancelling order {order_id} for {symbol}: {e}")
            raise RuntimeError(f"Failed to cancel order {order_id} for {symbol} due to API error: {e}")
        except BinanceRequestException as e:
            print(f"Binance Request Exception while cancelling order {order_id} for {symbol}: {e}")
            raise RuntimeError(f"Failed to cancel order {order_id} for {symbol} due to request error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while cancelling order {order_id} for {symbol}: {e}")
            raise RuntimeError(f"An unexpected error occurred while cancelling order {order_id} for {symbol}: {e}")

    def get_order_status(self, order_id: str, symbol: str) -> dict:
        """
        Retrieves the status and details of a specific order from Binance.
        Symbol must be in Binance format, e.g., 'BTCUSDT'.

        Args:
            order_id: The ID of the order to check.
            symbol: The trading symbol of the order (e.g., 'BTCUSDT').

        Returns:
            A dictionary containing order status information, e.g.,
            {'order_id': '12345', 'status': 'FILLED', 'symbol': 'BTCUSDT',
             'type': 'LIMIT', 'side': 'BUY', 'price': '50000.00',
             'orig_qty': '1.0', 'executed_qty': '1.0',
             'cummulative_quote_qty': '50000.00', ... , 'raw_response': ...}

        Raises:
            ConnectionError: If the client is not connected.
            ValueError: If any of the arguments are invalid.
            RuntimeError: If there's an API error (e.g., order not found) or other issue.
        """
        if not self.client:
            raise ConnectionError("Client not connected. Please call connect() first.")

        if not order_id:
            raise ValueError("Order ID must be provided.")
        if not symbol or '/' in symbol:
            raise ValueError("Valid symbol (e.g., 'BTCUSDT') must be provided.")

        print(f"Retrieving status for order {order_id}, symbol {symbol} from Binance.")
        try:
            order_info = self.client.get_order(
                symbol=symbol,
                orderId=order_id
            )

            if not order_info or 'orderId' not in order_info:
                raise RuntimeError(f"Failed to get order status or received unexpected response: {order_info}")

            # The response from get_order is quite comprehensive.
            # We can choose to return a subset or the whole thing, similar to place_order and cancel_order.
            formatted_response = {
                'order_id': str(order_info.get('orderId')),
                'status': order_info.get('status'),
                'symbol': order_info.get('symbol'),
                'type': order_info.get('type'),
                'side': order_info.get('side'),
                'price': order_info.get('price'),
                'orig_qty': order_info.get('origQty'), # Original quantity
                'executed_qty': order_info.get('executedQty'), # Filled quantity
                'cummulative_quote_qty': order_info.get('cummulativeQuoteQty'), # Total quote asset spent/received
                'time_in_force': order_info.get('timeInForce'),
                'client_order_id': order_info.get('clientOrderId'),
                'time': order_info.get('time'), # Order creation time
                'update_time': order_info.get('updateTime'), # Last update time
                'is_working': order_info.get('isWorking'),
                'raw_response': order_info
            }
            print(f"Status for order {order_id} ({symbol}): {formatted_response['status']}")
            return formatted_response

        except BinanceAPIException as e:
            # -2013: "Order does not exist."
            print(f"Binance API Exception while getting status for order {order_id} ({symbol}): {e}")
            raise RuntimeError(f"Failed to get status for order {order_id} ({symbol}) due to API error: {e}")
        except BinanceRequestException as e:
            print(f"Binance Request Exception while getting status for order {order_id} ({symbol}): {e}")
            raise RuntimeError(f"Failed to get status for order {order_id} ({symbol}) due to request error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while getting status for order {order_id} ({symbol}): {e}")
            raise RuntimeError(f"An unexpected error occurred while getting status for order {order_id} ({symbol}): {e}")
