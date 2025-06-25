import csv
import os
from datetime import datetime
import json

try:
    # Assuming logger is set up and passed or globally available
    from logging_alerts import setup_logging
    logger = setup_logging() # Or get existing logger if already configured
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("logging_alerts not found, using basic logging for data_storage.")


# --- Configuration for Data Storage ---
# TODO: Consider moving these to config.py if they need to be user-configurable
DATA_DIRECTORY = "market_data"
TICKER_DATA_FILE_TEMPLATE = os.path.join(DATA_DIRECTORY, "{symbol}_ticker_{timestamp}.csv")
ORDER_BOOK_DATA_FILE_TEMPLATE = os.path.join(DATA_DIRECTORY, "{symbol}_orderbook_{timestamp}.csv")
ORDER_BOOK_SNAPSHOT_JSON_FILE_TEMPLATE = os.path.join(DATA_DIRECTORY, "{symbol}_orderbook_snapshot_{timestamp}.json")


def _ensure_data_directory():
    """Ensures the data directory exists."""
    if not os.path.exists(DATA_DIRECTORY):
        try:
            os.makedirs(DATA_DIRECTORY)
            logger.info(f"Created data directory: {DATA_DIRECTORY}")
        except OSError as e:
            logger.error(f"Error creating data directory {DATA_DIRECTORY}: {e}", exc_info=True)
            return False
    return True

def save_ticker_data_csv(symbol, ticker_data):
    """
    Saves ticker data to a CSV file.
    The ticker_data is expected to be a dictionary from fetch_ticker_data.
    Example: {'ask': '9740.21', 'bid': '9740.20', 'last': '9740.21', 'volume': {'BTC': '10.0', ...}}
    We will flatten relevant parts of this structure for CSV.
    """
    if not _ensure_data_directory() or not ticker_data:
        logger.error(f"Cannot save ticker data for {symbol}. Directory or data missing.")
        return

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f") # Microsecond precision
    filepath = TICKER_DATA_FILE_TEMPLATE.format(symbol=symbol.upper(), timestamp=timestamp_str)

    # Define headers based on expected Gemini ticker structure (V1 pubticker)
    # https://docs.gemini.com/rest-api/#ticker
    # Example fields: bid, ask, last, volume (which is a nested dict)
    # We'll save key fields and flatten volume for the currency itself.
    headers = ['timestamp_recorded', 'symbol', 'bid', 'ask', 'last',
               'volume_btc', 'volume_eth', 'volume_usd', 'volume_timestamp']

    # Extract data, handling potential missing keys gracefully
    row = {
        'timestamp_recorded': datetime.now().isoformat(),
        'symbol': symbol.upper(),
        'bid': ticker_data.get('bid'),
        'ask': ticker_data.get('ask'),
        'last': ticker_data.get('last'),
        'volume_btc': ticker_data.get('volume', {}).get('BTC'),
        'volume_eth': ticker_data.get('volume', {}).get('ETH'),
        'volume_usd': ticker_data.get('volume', {}).get('USD'), # Or other quote currency
        'volume_timestamp': ticker_data.get('volume', {}).get('timestamp') # API's volume timestamp
    }
    # Dynamically add other quote currencies if present in volume, e.g. GUSD
    for key, value in ticker_data.get('volume', {}).items():
        if key not in ['BTC', 'ETH', 'USD', 'timestamp'] and f'volume_{key.lower()}' not in headers:
            headers.append(f'volume_{key.lower()}')
            row[f'volume_{key.lower()}'] = value

    try:
        file_exists = os.path.isfile(filepath)
        with open(filepath, 'w', newline='') as csvfile: # 'w' to create a new file per snapshot
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            if not file_exists: # Write header only if file is new (though 'w' always makes it new)
                writer.writeheader()
            writer.writerow(row)
        logger.info(f"Ticker data for {symbol} saved to {filepath}")
    except IOError as e:
        logger.error(f"IOError saving ticker data for {symbol} to {filepath}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error saving ticker data for {symbol} to {filepath}: {e}", exc_info=True)


def save_order_book_snapshot_csv(symbol, order_book_data):
    """
    Saves a snapshot of the order book (bids and asks) to a CSV file.
    Order book data is expected to be a dictionary with 'bids' and 'asks' lists.
    Each item in bids/asks is like: {'price': '9739.13', 'amount': '0.03', 'timestamp': '1589520 দেখে নাও'}
    This CSV format will save each bid/ask as a row.
    """
    if not _ensure_data_directory() or not order_book_data:
        logger.error(f"Cannot save order book for {symbol}. Directory or data missing.")
        return

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = ORDER_BOOK_DATA_FILE_TEMPLATE.format(symbol=symbol.upper(), timestamp=timestamp_str)

    headers = ['timestamp_recorded', 'symbol', 'type', 'price', 'amount', 'api_timestamp']

    try:
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()

            current_time_iso = datetime.now().isoformat()

            for bid in order_book_data.get('bids', []):
                writer.writerow({
                    'timestamp_recorded': current_time_iso,
                    'symbol': symbol.upper(),
                    'type': 'bid',
                    'price': bid.get('price'),
                    'amount': bid.get('amount'),
                    'api_timestamp': bid.get('timestamp') # API's own timestamp for the entry
                })
            for ask in order_book_data.get('asks', []):
                writer.writerow({
                    'timestamp_recorded': current_time_iso,
                    'symbol': symbol.upper(),
                    'type': 'ask',
                    'price': ask.get('price'),
                    'amount': ask.get('amount'),
                    'api_timestamp': ask.get('timestamp')
                })
        logger.info(f"Order book snapshot for {symbol} saved to {filepath}")
    except IOError as e:
        logger.error(f"IOError saving order book for {symbol} to {filepath}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error saving order book for {symbol} to {filepath}: {e}", exc_info=True)

def save_order_book_snapshot_json(symbol, order_book_data):
    """
    Saves the raw order book snapshot (bids and asks) to a JSON file.
    This preserves the full structure from the API.
    """
    if not _ensure_data_directory() or not order_book_data:
        logger.error(f"Cannot save JSON order book for {symbol}. Directory or data missing.")
        return

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = ORDER_BOOK_SNAPSHOT_JSON_FILE_TEMPLATE.format(symbol=symbol.upper(), timestamp=timestamp_str)

    data_to_save = {
        'recorded_timestamp_utc': datetime.utcnow().isoformat(),
        'symbol': symbol.upper(),
        'order_book': order_book_data
    }

    try:
        with open(filepath, 'w') as jsonfile:
            json.dump(data_to_save, jsonfile, indent=4)
        logger.info(f"Raw order book snapshot for {symbol} saved to {filepath}")
    except IOError as e:
        logger.error(f"IOError saving JSON order book for {symbol} to {filepath}: {e}", exc_info=True)
    except TypeError as e: # Error during JSON serialization
        logger.error(f"TypeError saving JSON order book for {symbol} (serialization issue): {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error saving JSON order book for {symbol} to {filepath}: {e}", exc_info=True)


if __name__ == "__main__":
    print("--- Data Storage Test ---")
    _ensure_data_directory() # Ensure it exists for tests

    test_symbol = "TESTCOINUSD"

    # Mock ticker data (structure from Gemini API v1 pubticker)
    mock_ticker = {
        "bid": "9999.99", "ask": "10000.01", "last": "10000.00",
        "volume": {
            "BTC": "123.456",
            "USD": "1234560.00",
            "timestamp": int(datetime.now().timestamp() * 1000) # Milliseconds
        }
    }
    print(f"\nSaving mock ticker data for {test_symbol}...")
    save_ticker_data_csv(test_symbol, mock_ticker)

    # Mock order book data (structure from Gemini API v1 book)
    mock_order_book = {
        "bids": [
            {"price": "9999.90", "amount": "0.5", "timestamp": str(int(datetime.now().timestamp()))},
            {"price": "9999.80", "amount": "1.2", "timestamp": str(int(datetime.now().timestamp()))}
        ],
        "asks": [
            {"price": "10000.10", "amount": "0.8", "timestamp": str(int(datetime.now().timestamp()))},
            {"price": "10000.20", "amount": "0.3", "timestamp": str(int(datetime.now().timestamp()))}
        ]
    }
    print(f"\nSaving mock order book data for {test_symbol} to CSV...")
    save_order_book_snapshot_csv(test_symbol, mock_order_book)

    print(f"\nSaving mock order book data for {test_symbol} to JSON...")
    save_order_book_snapshot_json(test_symbol, mock_order_book)

    print("\n--- End Data Storage Test ---")
    print(f"Check the '{DATA_DIRECTORY}' directory for output files.")
