import os

import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# API Keys - Load from environment variables for security
BINANCE_API_KEY = os.environ.get('BINANCE_API_KEY')
BINANCE_API_SECRET = os.environ.get('BINANCE_API_SECRET')
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
GOOGLE_GENAI_API_KEY = os.environ.get('GOOGLE_GENAI_API_KEY')


# Binance API Endpoints
# Use testnet for development and testing
BINANCE_API_BASE_URL = "https://testnet.binance.vision/api"
# BINANCE_API_BASE_URL_PRODUCTION = "https://api.binance.com/api" # For future reference

# Public Endpoints
BINANCE_TICKER_URL = f"{BINANCE_API_BASE_URL}/v3/ticker/24hr"  # ?symbol=<symbol>
BINANCE_ORDER_BOOK_URL = f"{BINANCE_API_BASE_URL}/v3/depth"  # ?symbol=<symbol>&limit=<limit>
BINANCE_SERVER_TIME_URL = f"{BINANCE_API_BASE_URL}/v3/time"
BINANCE_EXCHANGE_INFO_URL = f"{BINANCE_API_BASE_URL}/v3/exchangeInfo"

# Account Endpoints (Require Authentication)
BINANCE_ACCOUNT_INFO_URL = f"{BINANCE_API_BASE_URL}/v3/account"
BINANCE_ORDER_URL = f"{BINANCE_API_BASE_URL}/v3/order"
BINANCE_OPEN_ORDERS_URL = f"{BINANCE_API_BASE_URL}/v3/openOrders"
BINANCE_MY_TRADES_URL = f"{BINANCE_API_BASE_URL}/v3/myTrades"


# Logging Settings
LOG_FILE = "bot.log"
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Trading Parameters (Initial)
DEFAULT_TRADING_PAIR = "BTCUSDT" # Binance uses USDT, ETHBTC etc.
MAIN_LOOP_SLEEP_INTERVAL = 300 # Seconds (5 minutes)
# Add other parameters as needed, e.g., trade size, risk limits, etc.

# --- Helper function to check if essential configs are set ---
def check_essential_configs():
    """Checks if essential API keys are set."""
    keys_missing = False
    if not BINANCE_API_KEY:
        print("CRITICAL: BINANCE_API_KEY environment variable not set.")
        keys_missing = True
    if not BINANCE_API_SECRET:
        print("CRITICAL: BINANCE_API_SECRET environment variable not set.")
        keys_missing = True
    if not NEWS_API_KEY:
        print("CRITICAL: NEWS_API_KEY environment variable not set.")
        keys_missing = True
    if not GOOGLE_GENAI_API_KEY:
        print("CRITICAL: GOOGLE_GENAI_API_KEY environment variable not set.")
        keys_missing = True

    if keys_missing:
        return False
    return True

if __name__ == '__main__':
    # Example of how to use and check config
    print("--- Configuration Test ---")
    if check_essential_configs():
        print("Essential API keys are set.")
    else:
        print("Essential API keys are MISSING. Please set them as environment variables.")

    print(f"Binance API Key: {'Set' if BINANCE_API_KEY else 'Not Set'}")
    print(f"Binance API Secret: {'Set' if BINANCE_API_SECRET else 'Not Set'}")
    print(f"Binance Base URL: {BINANCE_API_BASE_URL}")
    print(f"Default Trading Pair: {DEFAULT_TRADING_PAIR}")
    print(f"Log File: {LOG_FILE}")
    print(f"Log Level: {LOG_LEVEL}")
    print("--- End Configuration Test ---")
