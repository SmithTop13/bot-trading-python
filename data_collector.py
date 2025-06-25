import requests
import time
import hmac
import hashlib
# import base64 # Not directly needed for Binance public requests, python-binance handles auth
import json
from binance.client import Client # For authenticated requests
from binance.exceptions import BinanceAPIException, BinanceRequestException

try:
    import config
    from logging_alerts import setup_logging # Assuming logger is passed or configured globally
except ImportError:
    print("Error: Failed to import config or logging_alerts in data_collector.py.")
    # Fallback for config if running standalone for simple tests (not recommended for full app)
    class MockConfig:
        BINANCE_API_KEY = "YOUR_BINANCE_API_KEY" # Replace with actual or env var for testing
        BINANCE_API_SECRET = "YOUR_BINANCE_API_SECRET" # Replace with actual or env var for testing
        BINANCE_TICKER_URL = "https://testnet.binance.vision/api/v3/ticker/24hr"
        BINANCE_ORDER_BOOK_URL = "https://testnet.binance.vision/api/v3/depth"
        # BINANCE_BALANCES_URL = "https://testnet.binance.vision/api/v3/account" # Handled by client
        BINANCE_API_BASE_URL = "https://testnet.binance.vision/api"
        DEFAULT_TRADING_PAIR = "BTCUSDT"

    config = MockConfig()
    # Basic logger if logging_alerts isn't available (e.g. running standalone)
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Initialize logger - typically, this would be passed from main.py or a global instance
logger = setup_logging() if 'setup_logging' in globals() else logging.getLogger('DataCollector')

# Initialize Binance Client
# It's better to initialize it once if API keys are available,
# or initialize it when needed for specific functions.
# For now, initialize lazily or within functions that need it.
binance_client = None

def get_binance_client():
    """Initializes and returns a Binance client instance."""
    global binance_client
    if binance_client is None:
        if config.BINANCE_API_KEY and config.BINANCE_API_SECRET:
            try:
                binance_client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, tld='com', testnet=True if "testnet" in config.BINANCE_API_BASE_URL else False)
                # Verify connectivity
                binance_client.ping()
                logger.info("Binance client initialized and connection verified.")
            except Exception as e:
                logger.error(f"Failed to initialize Binance client: {e}")
                binance_client = None # Ensure it's None if initialization fails
        else:
            logger.warning("Binance API Key or Secret not configured. Authenticated client calls will fail.")
    return binance_client


# --- Public API Functions ---
def fetch_ticker_data(symbol=config.DEFAULT_TRADING_PAIR):
    """
    Fetches current ticker data for a specified trading pair from Binance.
    Example symbol: "BTCUSDT", "ETHBTC"
    """
    url = config.BINANCE_TICKER_URL
    params = {'symbol': symbol.upper()}
    try:
        logger.info(f"Fetching ticker data for {symbol} from {url} with params: {params}")
        response = requests.get(url, params=params)
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

def fetch_order_book_data(symbol=config.DEFAULT_TRADING_PAIR, limit=100):
    """
    Fetches order book data for a specified trading pair from Binance.
    :param symbol: Trading symbol (e.g., "BTCUSDT")
    :param limit: Number of bids/asks to retrieve (default 100, max 5000, allowed values: [5, 10, 20, 50, 100, 500, 1000, 5000])
    """
    url = config.BINANCE_ORDER_BOOK_URL
    # Validate limit against allowed values if necessary, or let Binance API handle it
    params = {'symbol': symbol.upper(), 'limit': limit}

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
    Fetches account balances from Binance. Requires API key and secret.
    """
    logger.info("Attempting to fetch account balances from Binance...")
    client = get_binance_client()
    if not client:
        logger.error("Binance client not available. Cannot fetch account balances.")
        return None

    try:
        account_info = client.get_account() # Uses BINANCE_ACCOUNT_INFO_URL implicitly
        balances_data = account_info.get('balances', [])
        logger.info(f"Successfully fetched account balances. Number of assets: {len(balances_data)}")
        logger.debug(f"Balances data: {balances_data}")
        # Filter for non-zero balances if desired, or return all
        # active_balances = [b for b in balances_data if float(b['free']) > 0 or float(b['locked']) > 0]
        # return active_balances
        return balances_data
    except BinanceAPIException as api_err:
        logger.error(f"Binance API exception occurred while fetching account balances: {api_err}")
    except BinanceRequestException as req_err:
        logger.error(f"Binance request exception occurred while fetching account balances: {req_err}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching account balances: {e}")
    return None

# --- Rate Limiting and Error Handling Notes ---
# The python-binance library handles some aspects of rate limiting but careful usage is still needed.
# The above functions include basic try-except blocks.
# For production, more robust error handling and retry mechanisms (e.g., exponential backoff)
# might be necessary beyond what the library provides.

if __name__ == "__main__":
    print("--- Data Collector Test (Binance) ---")
    # Note: These tests will make live API calls to Binance (Testnet if configured).
    # Public endpoints (ticker, order book) should work without API keys.
    # Private endpoints (balances) require BINANCE_API_KEY and BINANCE_API_SECRET to be set
    # in environment variables or directly in the MockConfig above (for testing only).

    if 'config' not in globals() or config.BINANCE_API_KEY == "YOUR_BINANCE_API_KEY":
        print("WARNING: Using mock/default config. API calls might fail or use placeholder keys.")
        print("Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables for authenticated tests.")

    test_symbol = config.DEFAULT_TRADING_PAIR # e.g., BTCUSDT

    print(f"\nFetching ticker for {test_symbol}...")
    ticker = fetch_ticker_data(test_symbol)
    if ticker:
        # Binance ticker response is a dict, 'lastPrice' is one of the fields
        print(f"Ticker for {test_symbol}: Last Price: {ticker.get('lastPrice')}, Volume: {ticker.get('volume')}")
    else:
        print(f"Failed to fetch ticker for {test_symbol}.")

    print(f"\nFetching order book for {test_symbol} (top 5 bids/asks)...")
    # Binance default limit for order book is 100. Max is 5000.
    # For consistency with Gemini example, let's aim for a small number, though API might return more.
    # The `limit` param in fetch_order_book_data is for the number of entries.
    order_book = fetch_order_book_data(test_symbol, limit=5)
    if order_book:
        # Binance order book has 'bids' and 'asks' which are lists of [price, quantity]
        top_bid = order_book.get('bids', [[]])[0] if order_book.get('bids') else "N/A"
        top_ask = order_book.get('asks', [[]])[0] if order_book.get('asks') else "N/A"
        print(f"Order book for {test_symbol}: Top bid (Price, Qty): {top_bid}, Top ask (Price, Qty): {top_ask}")
    else:
        print(f"Failed to fetch order book for {test_symbol}.")

    # Authenticated endpoint test
    print("\nFetching account balances (requires API keys)...")
    # Check if keys are placeholder or actually missing from config object
    api_key_missing = not hasattr(config, 'BINANCE_API_KEY') or not config.BINANCE_API_KEY or config.BINANCE_API_KEY == "YOUR_BINANCE_API_KEY"
    api_secret_missing = not hasattr(config, 'BINANCE_API_SECRET') or not config.BINANCE_API_SECRET or config.BINANCE_API_SECRET == "YOUR_BINANCE_API_SECRET"

    if api_key_missing or api_secret_missing:
        print("Skipping account balances test: Binance API key/secret not configured for live test.")
    else:
        balances = fetch_account_balances()
        if balances is not None: # Check for None explicitly as an empty list is a valid (though perhaps empty) response
            print("Account balances fetched successfully:")
            for balance_info in balances:
                # Filter to show only assets with some balance for brevity
                if float(balance_info.get('free', 0)) > 0 or float(balance_info.get('locked', 0)) > 0:
                    print(f"  Asset: {balance_info['asset']}, Free: {balance_info['free']}, Locked: {balance_info['locked']}")
        else:
            print("Failed to fetch account balances. Check logs and API key configuration.")

    print("\n--- End Data Collector Test (Binance) ---")
