# order_manager.py
# This module will interact with the Binance exchange API (Testnet or Mainnet) for order execution.

import os
# import requests # Not needed if using python-binance client exclusively
import json
# import base64 # Handled by python-binance
# import hmac # Handled by python-binance
# import hashlib # Handled by python-binance
import time
import logging
import uuid
from binance.client import Client
from binance.enums import * # For order types, sides, etc.
from binance.exceptions import BinanceAPIException, BinanceOrderException, BinanceRequestException

try:
    import config # Assuming config.py is in the same directory or accessible via PYTHONPATH
    from logging_alerts import setup_logging
except ImportError:
    print("Error: Failed to import config or logging_alerts in order_manager.py.")
    # Fallback for config if running standalone for simple tests
    class MockConfig:
        BINANCE_API_KEY = "YOUR_BINANCE_TESTNET_API_KEY"
        BINANCE_API_SECRET = "YOUR_BINANCE_TESTNET_API_SECRET"
        BINANCE_API_BASE_URL = "https://testnet.binance.vision/api" # Important for Client
        DEFAULT_TRADING_PAIR = "BTCUSDT"
    config = MockConfig()
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


logger = setup_logging() if 'setup_logging' in globals() else logging.getLogger('OrderManager')


# Initialize Binance Client
# This should ideally be managed carefully, perhaps passed around or initialized once.
binance_client_om = None

def get_binance_client_om():
    """Initializes and returns a Binance client instance for Order Manager."""
    global binance_client_om
    if binance_client_om is None:
        if config.BINANCE_API_KEY and config.BINANCE_API_SECRET:
            try:
                # Determine if using testnet from config.BINANCE_API_BASE_URL
                is_testnet = "testnet" in config.BINANCE_API_BASE_URL.lower()
                binance_client_om = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=is_testnet)
                # Optionally, set the base URL if it's different from default testnet/mainnet,
                # though python-binance usually handles this with the `testnet` flag.
                # If your config.BINANCE_API_BASE_URL is specific (e.g. proxy or regional), you might need:
                # binance_client_om.API_URL = config.BINANCE_API_BASE_URL

                # Verify connectivity (optional, but good for early failure detection)
                binance_client_om.ping()
                logger.info(f"Binance client for Order Manager initialized (Testnet: {is_testnet}). Connection verified.")
            except Exception as e:
                logger.error(f"Failed to initialize Binance client for Order Manager: {e}")
                binance_client_om = None
        else:
            logger.warning(
                "BINANCE_API_KEY or BINANCE_API_SECRET not found. "
                "Order Manager will not be able to authenticate with Binance."
            )
    return binance_client_om


def _handle_binance_api_error(e, context_msg=""):
    """Helper to log Binance API errors."""
    if isinstance(e, BinanceAPIException):
        logger.error(f"Binance API Exception {context_msg}: Status Code: {e.status_code}, Response: {e.response}, Message: {e.message}, Code: {e.code}")
        return {"result": "error", "reason": "BinanceAPIException", "message": e.message, "code": e.code, "status_code": e.status_code}
    elif isinstance(e, BinanceOrderException):
        logger.error(f"Binance Order Exception {context_msg}: Code: {e.code}, Message: {e.message}")
        return {"result": "error", "reason": "BinanceOrderException", "message": e.message, "code": e.code}
    elif isinstance(e, BinanceRequestException):
        logger.error(f"Binance Request Exception {context_msg}: Message: {e.message}")
        return {"result": "error", "reason": "BinanceRequestException", "message": e.message}
    else:
        logger.error(f"An unexpected error occurred {context_msg}: {e}")
        return {"result": "error", "reason": "UnexpectedError", "message": str(e)}


def place_limit_order(symbol: str, quantity: str, price: str, side: str) -> dict:
    """
    Places a new limit order on Binance.

    Args:
        symbol: The trading symbol (e.g., "BTCUSDT", "ETHBTC").
        quantity: The amount of cryptocurrency to trade (as a string).
        price: The price for the order (as a string).
        side: "BUY" or "SELL" (case-insensitive, will be upper-cased).

    Returns:
        The order details from Binance API or an error dictionary.
    """
    client = get_binance_client_om()
    if not client:
        return {"result": "error", "reason": "ClientNotInitialized", "message": "Binance client not initialized."}

    try:
        order_side = SIDE_BUY if side.upper() == "BUY" else SIDE_SELL
        # Binance requires uppercase symbol
        symbol_upper = symbol.upper()
        # Generate a unique client order ID (optional but good practice)
        # client_order_id = f"bot-{symbol_upper}-{str(uuid.uuid4())[:8]}"

        logger.info(f"Placing {side.upper()} order: {quantity} {symbol_upper} @ {price}")
        # For limit orders, timeInForce defaults to GTC (Good 'Til Canceled)
        order = client.create_order(
            symbol=symbol_upper,
            side=order_side,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_GTC, # Good Til Canceled
            quantity=quantity,
            price=price
            # newClientOrderId=client_order_id # Optional
        )
        logger.info(f"Order placed successfully: {order}")
        return order # Successful order response from Binance
    except Exception as e:
        return _handle_binance_api_error(e, f"while placing {side.upper()} order for {quantity} {symbol.upper()} @ {price}")


def cancel_order(symbol: str, order_id: str = None, orig_client_order_id: str = None) -> dict:
    """
    Cancels an active order on Binance.
    Either order_id or orig_client_order_id must be provided.

    Args:
        symbol: The trading symbol (e.g., "BTCUSDT").
        order_id: The exchange's order ID.
        orig_client_order_id: The client's original order ID.

    Returns:
        The cancellation status from Binance API or an error dictionary.
    """
    client = get_binance_client_om()
    if not client:
        return {"result": "error", "reason": "ClientNotInitialized", "message": "Binance client not initialized."}

    if not order_id and not orig_client_order_id:
        logger.error("Either order_id or orig_client_order_id must be provided to cancel_order.")
        return {"result": "error", "reason": "InputError", "message": "Missing order identifier."}

    try:
        symbol_upper = symbol.upper()
        logger.info(f"Attempting to cancel order on {symbol_upper} (ID: {order_id or orig_client_order_id})")
        if order_id:
            cancel_status = client.cancel_order(symbol=symbol_upper, orderId=order_id)
        else: # orig_client_order_id must be set
            cancel_status = client.cancel_order(symbol=symbol_upper, origClientOrderId=orig_client_order_id)
        logger.info(f"Order cancellation status: {cancel_status}")
        return cancel_status
    except Exception as e:
        return _handle_binance_api_error(e, f"while cancelling order on {symbol.upper()} (ID: {order_id or orig_client_order_id})")


def get_order_status(symbol: str, order_id: str = None, orig_client_order_id: str = None) -> dict:
    """
    Retrieves the status of a specific order from Binance.
    Either order_id or orig_client_order_id must be provided.

    Args:
        symbol: The trading symbol (e.g., "BTCUSDT").
        order_id: The exchange's order ID.
        orig_client_order_id: The client's original order ID.

    Returns:
        The order status details from Binance API or an error dictionary.
    """
    client = get_binance_client_om()
    if not client:
        return {"result": "error", "reason": "ClientNotInitialized", "message": "Binance client not initialized."}

    if not order_id and not orig_client_order_id:
        logger.error("Either order_id or orig_client_order_id must be provided to get_order_status.")
        return {"result": "error", "reason": "InputError", "message": "Missing order identifier."}

    try:
        symbol_upper = symbol.upper()
        logger.debug(f"Fetching status for order on {symbol_upper} (ID: {order_id or orig_client_order_id})")
        if order_id:
            order_info = client.get_order(symbol=symbol_upper, orderId=order_id)
        else: # orig_client_order_id must be set
            order_info = client.get_order(symbol=symbol_upper, origClientOrderId=orig_client_order_id)
        logger.debug(f"Order status details: {order_info}")
        return order_info
    except Exception as e:
        return _handle_binance_api_error(e, f"while fetching status for order on {symbol.upper()} (ID: {order_id or orig_client_order_id})")


def get_active_orders(symbol: str = None) -> list | dict:
    """
    Retrieves all open orders from Binance. Can be filtered by symbol.

    Args:
        symbol: Optional. The trading symbol (e.g., "BTCUSDT") to filter orders.

    Returns:
        A list of active orders or an error dictionary.
    """
    client = get_binance_client_om()
    if not client:
        return {"result": "error", "reason": "ClientNotInitialized", "message": "Binance client not initialized."}

    try:
        if symbol:
            symbol_upper = symbol.upper()
            logger.debug(f"Fetching active orders for {symbol_upper}.")
            orders = client.get_open_orders(symbol=symbol_upper)
        else:
            logger.debug("Fetching all active orders.")
            orders = client.get_open_orders()
        logger.debug(f"Found {len(orders)} active order(s).")
        return orders
    except Exception as e:
        return _handle_binance_api_error(e, f"while fetching active orders (symbol: {symbol})")


def get_trade_history(symbol: str, limit: int = 500, from_id: int = None, start_time: int = None, end_time: int = None) -> list | dict:
    """
    Retrieves personal trade history for a given symbol from Binance.

    Args:
        symbol: The trading symbol (e.g., "BTCUSDT").
        limit: Default 500; max 1000.
        from_id: TradeId to fetch from. Default gets most recent trades.
        start_time: Optional. Timestamp in ms to get trades from INCLUSIVE.
        end_time: Optional. Timestamp in ms to get trades up to INCLUSIVE.


    Returns:
        A list of trades or an error dictionary.
    """
    client = get_binance_client_om()
    if not client:
        return {"result": "error", "reason": "ClientNotInitialized", "message": "Binance client not initialized."}

    try:
        symbol_upper = symbol.upper()
        params = {'symbol': symbol_upper, 'limit': min(limit, 1000)}
        if from_id is not None:
            params['fromId'] = from_id
        if start_time is not None:
            params['startTime'] = start_time
        if end_time is not None:
            params['endTime'] = end_time

        logger.debug(f"Fetching trade history for {symbol_upper} with params: {params}")
        trades = client.get_my_trades(**params)
        logger.debug(f"Found {len(trades)} trade(s) for {symbol_upper}.")
        return trades
    except Exception as e:
        return _handle_binance_api_error(e, f"while fetching trade history for {symbol.upper()}")


if __name__ == '__main__':
    # Ensure logging is configured for standalone script execution
    if 'setup_logging' not in globals() or not logger.handlers: # Basic check if logger is already configured
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger = logging.getLogger('OrderManagerTest') # Use a specific logger for tests

    logger.info("Testing Order Manager Module with Binance (ensure API keys are for TESTNET if testing live)...")

    # Attempt to initialize client for tests
    client_for_test = get_binance_client_om()

    if not client_for_test:
        logger.error("Cannot run live tests: Binance client for Order Manager failed to initialize. Check API keys and config.")
    else:
        test_symbol = config.DEFAULT_TRADING_PAIR # e.g. BTCUSDT from config

        logger.info(f"Attempting to fetch active orders for {test_symbol} (should be empty or show test orders)...")
        active_orders = get_active_orders(symbol=test_symbol)
        if isinstance(active_orders, list):
            logger.info(f"Active orders for {test_symbol}: {json.dumps(active_orders, indent=2)}")
        elif active_orders.get("result") == "error":
            logger.error(f"Error fetching active orders: {active_orders}")
        else:
            logger.info(f"Active orders response (raw): {active_orders}")

        logger.info(f"\nAttempting to fetch {test_symbol} trade history (last 5)...")
        trades = get_trade_history(symbol=test_symbol, limit=5)
        if isinstance(trades, list):
            logger.info(f"{test_symbol} Trade history: {json.dumps(trades, indent=2)}")
        elif trades.get("result") == "error":
            logger.error(f"Error fetching trade history: {trades}")
        else:
            logger.info(f"Trade history response (raw): {trades}")

        # --- Example: Place and then try to get status and cancel a small order ---
        # Note: This will place a real order on the TESTNET (if configured).
        # Use a very small amount and a price far from market for testing if you don't want fills.
        test_quantity = "0.001" # Small amount of base asset (e.g., BTC for BTCUSDT)
        # For testnet, it's good to get current price to place order nearby
        try:
            ticker = client_for_test.get_symbol_ticker(symbol=test_symbol)
            current_price = float(ticker['price'])
            test_buy_price_far_from_market = f"{current_price * 0.8:.2f}" # 20% below current price
            test_sell_price_far_from_market = f"{current_price * 1.2:.2f}" # 20% above current price
        except Exception as e:
            logger.error(f"Could not fetch current price for {test_symbol} to set test order prices: {e}")
            test_buy_price_far_from_market = "10000.00" # Fallback price

        logger.info(f"\nAttempting to place a test BUY order for {test_quantity} {test_symbol} at ${test_buy_price_far_from_market}...")
        placed_order_info = place_limit_order(
            symbol=test_symbol,
            quantity=test_quantity,
            price=test_buy_price_far_from_market,
            side="BUY"
        )
        logger.info(f"Place order response: {json.dumps(placed_order_info, indent=2)}")

        new_order_id = None
        # Binance returns dict on success, check for 'orderId'
        if isinstance(placed_order_info, dict) and "orderId" in placed_order_info and placed_order_info.get("status") != "REJECTED":
            new_order_id = str(placed_order_info.get("orderId")) # Ensure it's a string
            client_order_id = placed_order_info.get("clientOrderId")
            logger.info(f"Order placed successfully. Order ID: {new_order_id}, Client Order ID: {client_order_id}")

            logger.info(f"\nAttempting to get status for order ID: {new_order_id}...")
            order_status = get_order_status(symbol=test_symbol, order_id=new_order_id)
            logger.info(f"Order status response: {json.dumps(order_status, indent=2)}")

            # Only cancel if it's still open (e.g. NEW, PARTIALLY_FILLED)
            if isinstance(order_status, dict) and order_status.get("status") in ["NEW", "PARTIALLY_FILLED"]:
                logger.info(f"\nAttempting to cancel order ID: {new_order_id}...")
                cancel_status = cancel_order(symbol=test_symbol, order_id=new_order_id)
                logger.info(f"Cancel order response: {json.dumps(cancel_status, indent=2)}")

                logger.info(f"\nAttempting to get status for order ID: {new_order_id} again (should be CANCELED)...")
                order_status_after_cancel = get_order_status(symbol=test_symbol, order_id=new_order_id)
                logger.info(f"Order status after cancel: {json.dumps(order_status_after_cancel, indent=2)}")
            elif isinstance(order_status, dict):
                 logger.info(f"Order ID {new_order_id} status is {order_status.get('status')}, not attempting cancellation.")
            else:
                logger.error(f"Could not determine status of order {new_order_id} to decide on cancellation.")

        elif isinstance(placed_order_info, dict) and placed_order_info.get("result") == "error":
            logger.error(f"Failed to place order: {placed_order_info.get('reason')} - {placed_order_info.get('message')} (Code: {placed_order_info.get('code')})")
        else:
            logger.error(f"Failed to place order, unexpected response: {placed_order_info}")

    logger.info("\nOrder Manager Module (Binance) live testing finished.")
    logger.warning("REMINDER: The tests above interact with the Binance API (ideally TESTNET) using your API keys.")
    logger.warning("Ensure keys are for TESTNET ONLY if actual orders were placed, and you understand the implications.")
