# order_manager.py
# This module will interact with the Gemini exchange API (Sandbox) for order execution.

import os
import requests
import json
import base64
import hmac
import hashlib
import time
import logging
import uuid

logger = logging.getLogger(__name__)

GEMINI_SANDBOX_API_URL = "https://api.sandbox.gemini.com"
# Production URL (for future reference, DO NOT USE FOR DEVELOPMENT/TESTING):
# GEMINI_PRODUCTION_API_URL = "https://api.gemini.com"

# Ensure GEMINI_API_KEY and GEMINI_API_SECRET are set as environment variables for the Sandbox
API_KEY = os.getenv("GEMINI_API_KEY")
API_SECRET = os.getenv("GEMINI_API_SECRET")

if not API_KEY or not API_SECRET:
    logger.warning(
        "GEMINI_API_KEY or GEMINI_API_SECRET not found in environment variables. "
        "Order Manager will not be able to authenticate with Gemini Sandbox."
    )

def _get_nonce():
    """Generates a nonce (milliseconds since epoch)."""
    return int(time.time() * 1000)

def _sign_payload(payload_json_str: str, api_secret: str) -> str:
    """Signs the payload using HMAC-SHA384."""
    payload_b64 = base64.b64encode(payload_json_str.encode('utf-8'))
    signature = hmac.new(
        api_secret.encode('utf-8'),
        payload_b64,
        hashlib.sha384
    ).hexdigest()
    return signature, payload_b64.decode('utf-8')


def _send_gemini_private_request(endpoint_path: str, payload: dict) -> dict:
    """
    Sends an authenticated private request to the Gemini API (Sandbox).

    Args:
        endpoint_path: The API endpoint path (e.g., "/v1/order/new").
        payload: The request payload as a dictionary.

    Returns:
        The JSON response from the API as a dictionary, or an error dictionary.
    """
    if not API_KEY or not API_SECRET:
        error_msg = "API key or secret not configured for Gemini."
        logger.error(error_msg)
        return {"result": "error", "reason": "ConfigurationError", "message": error_msg}

    url = GEMINI_SANDBOX_API_URL + endpoint_path
    payload['request'] = endpoint_path # Add the request path to the payload
    payload['nonce'] = _get_nonce()

    payload_json_str = json.dumps(payload)
    signature, b64_payload = _sign_payload(payload_json_str, API_SECRET)

    headers = {
        'Content-Type': 'text/plain', # As per Gemini docs for signed requests
        'Content-Length': '0', # Should be 0 for POST with b64 payload in header
        'X-GEMINI-APIKEY': API_KEY,
        'X-GEMINI-PAYLOAD': b64_payload,
        'X-GEMINI-SIGNATURE': signature,
        'Cache-Control': 'no-cache'
    }

    try:
        logger.debug(f"Sending private request to {url} with payload: {payload_json_str[:200]}...") # Log snippet
        response = requests.post(url, headers=headers, timeout=15) # data=None as payload is in header
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        response_data = response.json()
        logger.debug(f"Gemini response for {endpoint_path}: {response_data}")
        return response_data
    except requests.exceptions.HTTPError as http_err:
        error_msg = f"HTTP error occurred: {http_err} - Response: {response.text}"
        logger.error(error_msg)
        try:
            # Try to parse Gemini's error format if available
            return response.json()
        except json.JSONDecodeError:
            return {"result": "error", "reason": "HTTPError", "message": str(http_err)}
    except requests.exceptions.RequestException as req_err:
        error_msg = f"Request exception occurred: {req_err}"
        logger.error(error_msg)
        return {"result": "error", "reason": "RequestException", "message": str(req_err)}
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        logger.error(error_msg)
        return {"result": "error", "reason": "UnexpectedError", "message": str(e)}


def place_limit_order(symbol: str, amount_crypto: str, price: str, side: str) -> dict:
    """
    Places a new limit order on the Gemini Sandbox.

    Args:
        symbol: The trading symbol (e.g., "BTCUSD", "ETHUSD").
        amount_crypto: The amount of cryptocurrency to trade (as a string).
        price: The price for the order (as a string).
        side: "buy" or "sell".

    Returns:
        The order details from Gemini API or an error dictionary.
    """
    endpoint = "/v1/order/new"
    client_order_id = f"bot-{symbol.lower()}-{str(uuid.uuid4())[:8]}" # Unique client order ID

    payload = {
        # "request": endpoint, # Added by _send_gemini_private_request
        "client_order_id": client_order_id,
        "symbol": symbol.lower(), # Gemini expects lowercase symbols in request
        "amount": amount_crypto,
        "price": price,
        "side": side.lower(),
        "type": "exchange limit", # Standard limit order
        "options": [] # e.g., ["maker-or-cancel"], ["immediate-or-cancel"] - keeping it simple for now
    }
    logger.info(f"Placing {side} order: {amount_crypto} {symbol} @ {price}. Client ID: {client_order_id}")
    return _send_gemini_private_request(endpoint, payload)


def cancel_order(order_id: int) -> dict:
    """
    Cancels an active order on the Gemini Sandbox.

    Args:
        order_id: The ID of the order to cancel.

    Returns:
        The cancellation status from Gemini API or an error dictionary.
    """
    endpoint = "/v1/order/cancel"
    payload = {
        "order_id": order_id
    }
    logger.info(f"Attempting to cancel order ID: {order_id}")
    return _send_gemini_private_request(endpoint, payload)


def get_order_status(order_id: int) -> dict:
    """
    Retrieves the status of a specific order from the Gemini Sandbox.

    Args:
        order_id: The ID of the order.

    Returns:
        The order status details from Gemini API or an error dictionary.
    """
    endpoint = "/v1/order/status"
    payload = {
        "order_id": order_id
    }
    logger.debug(f"Fetching status for order ID: {order_id}")
    return _send_gemini_private_request(endpoint, payload)


def get_active_orders() -> dict:
    """
    Retrieves all active orders from the Gemini Sandbox.

    Returns:
        A list of active orders or an error dictionary.
        (Note: Gemini returns a list directly, not a dict with 'result' for this one on success)
    """
    endpoint = "/v1/orders"
    payload = {} # No specific payload needed beyond auth for this endpoint
    logger.debug("Fetching active orders.")
    return _send_gemini_private_request(endpoint, payload)


def get_trade_history(symbol: str, limit_trades: int = 50, timestamp: int = None) -> dict:
    """
    Retrieves personal trade history for a given symbol from the Gemini Sandbox.

    Args:
        symbol: The trading symbol (e.g., "BTCUSD").
        limit_trades: The maximum number of trades to retrieve (max 500).
        timestamp: Optional. Only trades occurring after this timestamp (ms) will be returned.

    Returns:
        A list of trades or an error dictionary.
        (Note: Gemini returns a list directly, not a dict with 'result' for this one on success)
    """
    endpoint = "/v1/mytrades"
    payload = {
        "symbol": symbol.lower(),
        "limit_trades": min(limit_trades, 500)
    }
    if timestamp:
        payload["timestamp"] = timestamp

    logger.debug(f"Fetching trade history for {symbol}, limit {limit_trades}.")
    return _send_gemini_private_request(endpoint, payload)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG) # Show debug logs for testing
    logger.info("Testing Order Manager Module (requires GEMINI_API_KEY and GEMINI_API_SECRET for Sandbox)...")

    if not API_KEY or not API_SECRET:
        logger.error("Cannot run live tests: GEMINI_API_KEY or GEMINI_API_SECRET for Sandbox are not set.")
    else:
        logger.info("Attempting to fetch active orders (should be empty or show test orders)...")
        active_orders = get_active_orders()
        if isinstance(active_orders, list):
            logger.info(f"Active orders response: {json.dumps(active_orders, indent=2)}")
        elif active_orders.get("result") == "error":
            logger.error(f"Error fetching active orders: {active_orders.get('message')}")
        else: # Should be a list on success from Gemini
            logger.info(f"Active orders (raw): {active_orders}")


        logger.info("\nAttempting to fetch BTCUSD trade history...")
        trades = get_trade_history("BTCUSD", limit_trades=5)
        if isinstance(trades, list):
            logger.info(f"BTCUSD Trade history: {json.dumps(trades, indent=2)}")
        elif trades.get("result") == "error":
            logger.error(f"Error fetching trade history: {trades.get('message')}")
        else: # Should be a list on success from Gemini
            logger.info(f"Trade history (raw): {trades}")

        # --- Example: Place and then try to get status and cancel a small order ---
        # Note: This will place a real order on the SANDBOX.
        # It might get filled if the price is near market.
        # Use a very small amount and a price far from market for testing if you don't want fills.
        test_symbol = "BTCUSD"
        test_amount = "0.00001" # Very small amount of BTC
        test_price_far_from_market = "10000.00" # Far below typical BTC price

        logger.info(f"\nAttempting to place a test BUY order for {test_amount} {test_symbol} at ${test_price_far_from_market}...")
        placed_order_info = place_limit_order(
            symbol=test_symbol,
            amount_crypto=test_amount,
            price=test_price_far_from_market,
            side="buy"
        )
        logger.info(f"Place order response: {json.dumps(placed_order_info, indent=2)}")

        new_order_id = None
        if placed_order_info and not placed_order_info.get("result") == "error" and "order_id" in placed_order_info:
            new_order_id = placed_order_info.get("order_id")
            logger.info(f"Order placed successfully. Order ID: {new_order_id}")

            logger.info(f"\nAttempting to get status for order ID: {new_order_id}...")
            order_status = get_order_status(int(new_order_id)) # Gemini order_id is usually int
            logger.info(f"Order status response: {json.dumps(order_status, indent=2)}")

            # Only cancel if it's still active (or for testing cancellation path)
            # if order_status and order_status.get("is_live"):
            logger.info(f"\nAttempting to cancel order ID: {new_order_id}...")
            cancel_status = cancel_order(int(new_order_id))
            logger.info(f"Cancel order response: {json.dumps(cancel_status, indent=2)}")

            logger.info(f"\nAttempting to get status for order ID: {new_order_id} again (should be cancelled)...")
            order_status_after_cancel = get_order_status(int(new_order_id))
            logger.info(f"Order status after cancel: {json.dumps(order_status_after_cancel, indent=2)}")

        elif placed_order_info.get("result") == "error":
            logger.error(f"Failed to place order: {placed_order_info.get('reason')} - {placed_order_info.get('message')}")
        else:
            logger.error(f"Failed to place order, unexpected response: {placed_order_info}")

    logger.info("\nOrder Manager Module live testing finished.")
    logger.warning("REMINDER: The tests above interact with the Gemini SANDBOX environment using your API keys.")
    logger.warning("Ensure keys are for SANDBOX ONLY and you understand any orders placed are on the sandbox.")
