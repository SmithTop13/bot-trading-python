import argparse
import signal
import sys
import time

# Attempt to import project modules
try:
    import config
    from logging_alerts import setup_logging, critical_alert, error_alert
except ImportError as e:
    print(f"Error: Failed to import necessary modules. Ensure config.py and logging_alerts.py are in the PYTHONPATH. Details: {e}")
    sys.exit(1)

# Global logger instance
logger = None

def handle_shutdown_signal(signum, frame):
    """Handles graceful shutdown on receiving SIGINT (Ctrl+C) or SIGTERM."""
    global logger
    signal_name = signal.Signals(signum).name
    message = f"Shutdown signal {signal_name} ({signum}) received. Exiting gracefully..."
    if logger:
        logger.warning(message)
    else:
        print(message)

    # Perform any cleanup tasks here (e.g., close connections, save state)
    print("Performing cleanup tasks...")
    # For now, just a placeholder
    print("Cleanup complete.")

    sys.exit(0)

def main():
    """Main function to run the trading bot."""
    global logger

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="AI-Powered Cryptocurrency Trading Bot")
    parser.add_argument(
        "--config",
        type=str,
        default=None, # Defaulting to None, as we primarily use config.py
        help="Path to a JSON configuration file (optional, overrides config.py if used).",
    )
    # Add other command-line arguments as needed

    args = parser.parse_args()

    # --- Configuration Loading ---
    # For now, we primarily rely on config.py.
    # If args.config is provided, future versions could load/override settings from there.
    # For this phase, we'll just acknowledge it.

    # --- Setup Logging ---
    # Logging setup should happen as early as possible.
    # However, if config loading from a file (args.config) were to influence logging,
    # it might need to be deferred or reconfigured.
    try:
        logger = setup_logging()
    except Exception as e:
        # Fallback to print if logging setup fails catastrophically
        print(f"CRITICAL: Failed to setup logging: {e}", file=sys.stderr)
        sys.exit(1)

    logger.info("Trading Bot starting...")
    if args.config:
        logger.info(f"Configuration file specified: {args.config}. (Note: JSON config loading not fully implemented in Phase 1, using config.py)")
    else:
        logger.info("Using default configuration from config.py.")

    # --- Check Essential Configurations ---
    if not config.check_essential_configs():
        critical_alert(logger, "Essential configurations (API keys) are missing. Please set them as environment variables. Bot cannot continue.")
        sys.exit(1)
    logger.info("Essential configurations seem to be present.")

    # --- Register Signal Handlers for Graceful Shutdown ---
    signal.signal(signal.SIGINT, handle_shutdown_signal)  # Ctrl+C
    signal.signal(signal.SIGTERM, handle_shutdown_signal) # kill command
    logger.info("Signal handlers for graceful shutdown registered.")

    # --- Main Bot Loop (Integrated Test for Phase 1) ---
    logger.info("Entering main bot loop for Phase 1 integrated test...")
    try:
        # Import data collection and storage functions
        # These are imported here to ensure logger is configured before they are potentially used
        # (though their internal loggers should also work independently if needed)
        from data_collector import fetch_ticker_data, fetch_order_book_data, fetch_account_balances
        from data_storage import save_ticker_data_csv, save_order_book_snapshot_csv, save_order_book_snapshot_json

        # For Phase 1, we will fetch data once and save it.
        # A real bot would loop and fetch periodically.

        current_symbol = config.DEFAULT_TRADING_PAIR
        logger.info(f"Target trading pair: {current_symbol}")

        # 1. Fetch Ticker Data
        logger.info(f"Attempting to fetch ticker data for {current_symbol}...")
        ticker_data = fetch_ticker_data(symbol=current_symbol)
        if ticker_data:
            logger.info(f"Successfully fetched ticker data for {current_symbol}.")
            save_ticker_data_csv(symbol=current_symbol, ticker_data=ticker_data)
        else:
            logger.warning(f"Failed to fetch ticker data for {current_symbol}. Skipping save.")

        # 2. Fetch Order Book Data
        logger.info(f"Attempting to fetch order book data for {current_symbol}...")
        # Fetching with default limits (50 bids/asks)
        order_book_data = fetch_order_book_data(symbol=current_symbol)
        if order_book_data:
            logger.info(f"Successfully fetched order book data for {current_symbol}.")
            save_order_book_snapshot_csv(symbol=current_symbol, order_book_data=order_book_data)
            save_order_book_snapshot_json(symbol=current_symbol, order_book_data=order_book_data) # Also save as JSON
        else:
            logger.warning(f"Failed to fetch order book data for {current_symbol}. Skipping save.")

        # 3. Fetch Account Balances (Requires API Keys)
        logger.info("Attempting to fetch account balances...")
        if config.GEMINI_API_KEY and config.GEMINI_API_SECRET:
            account_balances = fetch_account_balances()
            if account_balances:
                logger.info("Successfully fetched account balances.")
                # For Phase 1, we just log balances. No specific save function for balances yet,
                # but they are logged by data_collector.
                # For example, print a summary:
                for balance_info in account_balances:
                    if float(balance_info.get('amount', 0)) > 0: # Log only non-zero balances
                        logger.info(f"Balance: {balance_info['currency']} - Amount: {balance_info['amount']}, Available: {balance_info['available']}")
            else:
                logger.warning("Failed to fetch account balances. Check API keys and permissions if this was expected to work.")
        else:
            logger.warning("Skipping fetch_account_balances: GEMINI_API_KEY or GEMINI_API_SECRET not set in environment variables.")
            logger.warning("To test balance fetching, set these environment variables with your Gemini API credentials (e.g., from a sandbox account).")

        logger.info("Main bot tasks for Phase 1 integrated test completed.")

    except ImportError:
        # This catch is if data_collector or data_storage are not found at runtime.
        # The initial imports at the top of the file handle their absence more gracefully for startup.
        critical_alert(logger, "Failed to import data_collector or data_storage modules within main loop. Bot cannot continue data operations.")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt caught in main loop. Initiating shutdown.")
        handle_shutdown_signal(signal.SIGINT, None)
    except Exception as e:
        error_message = f"An unexpected error occurred in the main loop: {e}"
        error_alert(logger, error_message, exc_info=True)
        # Depending on the error, might attempt a restart or just exit
        sys.exit(1)
    finally:
        logger.info("Trading Bot shutting down.")


if __name__ == "__main__":
    main()
