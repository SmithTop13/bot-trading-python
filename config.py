import os

# API Keys - Load from environment variables for security
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_SECRET = os.environ.get('GEMINI_API_SECRET')

# Gemini API Endpoints
GEMINI_API_BASE_URL = "https://api.gemini.com"  # Or "https://api.sandbox.gemini.com" for testing
GEMINI_TICKER_URL = f"{GEMINI_API_BASE_URL}/v1/pubticker/"  # Append <symbol>
GEMINI_ORDER_BOOK_URL = f"{GEMINI_API_BASE_URL}/v1/book/"  # Append <symbol>
GEMINI_BALANCES_URL = f"{GEMINI_API_BASE_URL}/v1/balances"

# Logging Settings
LOG_FILE = "bot.log"
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Trading Parameters (Initial)
DEFAULT_TRADING_PAIR = "BTCUSD"
# Add other parameters as needed, e.g., trade size, risk limits, etc.

# --- Helper function to check if essential configs are set ---
def check_essential_configs():
    """Checks if essential API keys are set."""
    if not GEMINI_API_KEY:
        print("CRITICAL: GEMINI_API_KEY environment variable not set.")
        return False
    if not GEMINI_API_SECRET:
        print("CRITICAL: GEMINI_API_SECRET environment variable not set.")
        return False
    return True

if __name__ == '__main__':
    # Example of how to use and check config
    print("--- Configuration Test ---")
    if check_essential_configs():
        print("Essential API keys are set.")
    else:
        print("Essential API keys are MISSING. Please set them as environment variables.")

    print(f"Gemini API Key: {'Set' if GEMINI_API_KEY else 'Not Set'}")
    print(f"Gemini API Secret: {'Set' if GEMINI_API_SECRET else 'Not Set'}")
    print(f"Gemini Base URL: {GEMINI_API_BASE_URL}")
    print(f"Default Trading Pair: {DEFAULT_TRADING_PAIR}")
    print(f"Log File: {LOG_FILE}")
    print(f"Log Level: {LOG_LEVEL}")
    print("--- End Configuration Test ---")
