import requests
import time
import hmac
import hashlib
import base64
import json

try:
    import config
    from logging_alerts import setup_logging # Assuming logger is passed or configured globally
except ImportError:
    print("Error: Failed to import config or logging_alerts in data_collector.py.")
    # Fallback for config if running standalone for simple tests (not recommended for full app)
    class MockConfig:
        GEMINI_API_KEY = "YOUR_GEMINI_API_KEY" # Replace with actual or env var for testing
        GEMINI_API_SECRET = "YOUR_GEMINI_API_SECRET" # Replace with actual or env var for testing
        GEMINI_TICKER_URL = "https://api.gemini.com/v1/pubticker/"
        GEMINI_ORDER_BOOK_URL = "https://api.gemini.com/v1/book/"
        GEMINI_BALANCES_URL = "https://api.gemini.com/v1/balances"
        GEMINI_API_BASE_URL = "https://api.gemini.com" # or sandbox
        DEFAULT_TRADING_PAIR = "BTCUSD"

    config = MockConfig()
    # Basic logger if logging_alerts isn't available (e.g. running standalone)
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Initialize logger - typically, this would be passed from main.py or a global instance
# For now, let's get a logger instance. If main.py runs this, it uses its configured logger.
logger = setup_logging() if 'setup_logging' in globals() else logging.getLogger('DataCollector')


# --- Private API Request Helper ---
def _gemini_private_request(endpoint_path, payload=None):
    """
    Helper function to make authenticated requests to Gemini's private API endpoints.
    """
    if not config.GEMINI_API_KEY or not config.GEMINI_API_SECRET:
        logger.error("Gemini API Key or Secret not configured. Cannot make private API calls.")
        return None

    if payload is None:
        payload = {}

    # The request path includes the API version, e.g., /v1/balances
    # Ensure endpoint_path starts with a / if it's just the path segment
    if not endpoint_path.startswith('/'):
        request_path = f"/v1/{endpoint_path}"
    else:
        request_path = endpoint_path

    payload['request'] = request_path
    payload['nonce'] = int(time.time() * 1000) # Milliseconds

    b64_payload = base64.b64encode(json.dumps(payload).encode('utf-8'))
    signature = hmac.new(config.GEMINI_API_SECRET.encode('utf-8'), b64_payload, hashlib.sha384).hexdigest()

    headers = {
        'Content-Type': 'text/plain', # Gemini specific
        'Content-Length': '0', # Gemini specific for POST requests with empty body but b64 payload in header
        'X-GEMINI-APIKEY': config.GEMINI_API_KEY,
        'X-GEMINI-PAYLOAD': b64_payload.decode('utf-8'),
        'X-GEMINI-SIGNATURE': signature,
        'Cache-Control': 'no-cache'
    }

    url = config.GEMINI_API_BASE_URL + request_path

    try:
        logger.debug(f"Making POST request to {url} with headers: { {k: (v if k != 'X-GEMINI-APIKEY' and k != 'X-GEMINI-PAYLOAD' else '...') for k,v in headers.items()} }") # Avoid logging sensitive parts of payload or key
        response = requests.post(url, headers=headers, data=None) # Data is in headers for Gemini
        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred: {req_err}")
    except json.JSONDecodeError as json_err:
        logger.error(f"Failed to decode JSON response: {json_err} - Response text: {response.text if 'response' in locals() else 'N/A'}")
    return None

# --- Public API Functions ---
def fetch_ticker_data(symbol=config.DEFAULT_TRADING_PAIR):
    """
    Fetches current ticker data for a specified trading pair from Gemini.
    Example symbol: "BTCUSD", "ETHUSD"
    """
    url = f"{config.GEMINI_TICKER_URL}{symbol.upper()}"
    try:
        logger.info(f"Fetching ticker data for {symbol} from {url}")
        response = requests.get(url)
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        data = response.json()
        logger.debug(f"Ticker data for {symbol}: {data}")
        return data
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while fetching ticker for {symbol}: {http_err} - {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred while fetching ticker for {symbol}: {req_err}")
    except json.JSONDecodeError as json_err:
        logger.error(f"Failed to decode JSON response for ticker {symbol}: {json_err} - Response text: {response.text if 'response' in locals() else 'N/A'}")
    return None

def fetch_order_book_data(symbol=config.DEFAULT_TRADING_PAIR, limit_bids=50, limit_asks=50):
    """
    Fetches order book data for a specified trading pair from Gemini.
    :param symbol: Trading symbol (e.g., "BTCUSD")
    :param limit_bids: Number of bids to retrieve (max 50)
    :param limit_asks: Number of asks to retrieve (max 50)
    """
    url = f"{config.GEMINI_ORDER_BOOK_URL}{symbol.upper()}"
    params = {}
    if limit_bids > 0 and limit_bids <= 50:
        params['limit_bids'] = limit_bids
    if limit_asks > 0 and limit_asks <= 50:
        params['limit_asks'] = limit_asks

    try:
        logger.info(f"Fetching order book data for {symbol} from {url} with params: {params}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Order book data for {symbol} (bids: {len(data.get('bids',[]))}, asks: {len(data.get('asks',[]))})")
        return data
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while fetching order book for {symbol}: {http_err} - {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred while fetching order book for {symbol}: {req_err}")
    except json.JSONDecodeError as json_err:
        logger.error(f"Failed to decode JSON response for order book {symbol}: {json_err} - Response text: {response.text if 'response' in locals() else 'N/A'}")
    return None

# --- Authenticated API Functions ---
def fetch_account_balances():
    """
    Fetches account balances from Gemini. Requires API key and secret.
    """
    logger.info("Attempting to fetch account balances...")
    # The endpoint for balances is just /v1/balances, which is handled by _gemini_private_request
    # The payload for balances request is just the standard nonce and request path
    payload = {'request': '/v1/balances'}
    # Note: _gemini_private_request adds nonce and request to payload again, so we can send minimal or let it build.
    # Let's simplify and let _gemini_private_request handle the full payload construction based on endpoint_path.

    balances_data = _gemini_private_request("balances") # Pass just the specific path part

    if balances_data:
        logger.info(f"Successfully fetched account balances. Number of currencies: {len(balances_data)}")
        logger.debug(f"Balances data: {balances_data}")
        return balances_data
    else:
        logger.error("Failed to fetch account balances.")
        return None

# --- Rate Limiting and Error Handling Notes ---
# The above functions include basic try-except blocks for network errors and HTTP errors.
# True rate limit handling would involve:
# 1. Checking response headers for rate limit information (if provided by Gemini).
# 2. Implementing exponential backoff and retry mechanisms.
#    Example: if a 429 (Too Many Requests) is received, wait for a bit and retry.
# For Phase 1, we log errors. Retries can be added in a future phase.

if __name__ == "__main__":
    print("--- Data Collector Test ---")
    # Note: These tests will make live API calls.
    # Public endpoints (ticker, order book) should work without API keys.
    # Private endpoints (balances) require GEMINI_API_KEY and GEMINI_API_SECRET to be set
    # in environment variables or directly in the MockConfig above (for testing only).

    # Ensure config is loaded (even if it's MockConfig)
    if 'config' not in globals() or config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        print("WARNING: Using mock/default config. API calls might fail or use placeholder keys.")
        print("Set GEMINI_API_KEY and GEMINI_API_SECRET environment variables for authenticated tests.")

    test_symbol = config.DEFAULT_TRADING_PAIR

    print(f"\nFetching ticker for {test_symbol}...")
    ticker = fetch_ticker_data(test_symbol)
    if ticker:
        print(f"Ticker for {test_symbol}: Last Price: {ticker.get('last')}")
    else:
        print(f"Failed to fetch ticker for {test_symbol}.")

    print(f"\nFetching order book for {test_symbol} (top 5 bids/asks)...")
    order_book = fetch_order_book_data(test_symbol, limit_bids=5, limit_asks=5)
    if order_book:
        print(f"Order book for {test_symbol}: Top bid: {order_book.get('bids', [{}])[0]}, Top ask: {order_book.get('asks', [{}])[0]}")
    else:
        print(f"Failed to fetch order book for {test_symbol}.")

    # Authenticated endpoint test
    print("\nFetching account balances (requires API keys)...")
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY" or \
       not config.GEMINI_API_SECRET or config.GEMINI_API_SECRET == "YOUR_GEMINI_API_SECRET":
        print("Skipping account balances test: API key/secret not configured for live test.")
    else:
        balances = fetch_account_balances()
        if balances:
            print("Account balances fetched successfully:")
            for balance_info in balances:
                print(f"  Currency: {balance_info['currency']}, Amount: {balance_info['amount']}, Available: {balance_info['available']}")
        else:
            print("Failed to fetch account balances. Check logs and API key configuration.")

    print("\n--- End Data Collector Test ---")
