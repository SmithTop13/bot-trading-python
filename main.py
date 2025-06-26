import argparse
import signal
import sys
import time

from data_collector import fetch_account_balances

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

    # --- Initialize Bot State (Simplified for Phase 2) ---
    # In a real bot, this would be loaded from a persistent store or live from exchange
    TOTAL_CAPITAL_USD = 10000.0  # Example starting capital
    AVAILABLE_BALANCES = {
        "USD": 10000.0,
        "BTC": 0.0,
        "ETH": 0.0
    }
    # MAX_OPEN_TRADES = risk_management.MAX_CONCURRENT_OPEN_TRADES # Loaded from module
    current_open_positions = 0 # Simple counter

    # --- Import Phase 2 Modules ---
    try:
        from data_collector import fetch_ticker_data # fetch_account_balances (already imported by old code)
        import news_collector
        import ai_analyst
        import decision_engine
        import risk_management
        import order_manager
    except ImportError as e:
        critical_alert(logger, f"Failed to import Phase 2 modules: {e}. Bot cannot continue.")
        sys.exit(1)

    # Ensure AI Analyst is configured (it tries on import, this is a check)
    if not ai_analyst.IS_GEMINI_CONFIGURED: # This check remains relevant for Google GenAI key
        logger.warning("AI Analyst (Google GenAI) may not be configured due to missing GOOGLE_GENAI_API_KEY. Sentiment analysis will fail.")
    # No direct API_KEY check for order_manager here, its functions will handle client init.
    # We can add a call to initialize or check client if needed, e.g.
    # if not order_manager.get_binance_client_om():
    #     logger.warning("Order Manager (Binance Exchange) could not initialize client. Order placement will fail. Check API keys in config.")


    # --- Main Bot Loop Function ---
    def run_trading_cycle():
        nonlocal current_open_positions # Allow modification of this outer scope variable
        nonlocal TOTAL_CAPITAL_USD # Allow modification (though less likely to change than balances)
        nonlocal AVAILABLE_BALANCES

        logger.info("Starting new trading cycle...")

        # 1. Fetch Market Data (Using Binance)
        logger.info("Fetching market data from Binance...")
        market_data_for_engine = {}

        # Fetch data for the default trading pair from config
        default_pair = config.DEFAULT_TRADING_PAIR # e.g., "BTCUSDT"
        ticker_data = fetch_ticker_data(symbol=default_pair)

        if ticker_data and ticker_data.get('lastPrice'):
            try:
                price = float(ticker_data['lastPrice'])
                volume = float(ticker_data.get('volume', 0)) # Base asset volume
                market_data_for_engine[default_pair] = {
                    'price': price,
                    'volume': volume,
                }
                logger.info(f"{default_pair} Ticker: Price={price}, Volume={volume}")
            except ValueError as ve:
                logger.error(f"Could not parse price/volume for {default_pair} from ticker data: {ticker_data}. Error: {ve}")
        else:
            logger.warning(f"Failed to fetch {default_pair} ticker data or 'lastPrice' missing. Skipping decisions for this pair.")

        # Example for a second pair if needed (e.g. ETHUSDT)
        # second_pair = "ETHUSDT" # Or from a list in config
        # eth_ticker_data = fetch_ticker_data(symbol=second_pair)
        # if eth_ticker_data and eth_ticker_data.get('lastPrice'):
        #     try:
        #         eth_price = float(eth_ticker_data['lastPrice'])
        #         eth_volume = float(eth_ticker_data.get('volume',0))
        #         market_data_for_engine[second_pair] = {
        #             'price': eth_price,
        #             'volume': eth_volume,
        #         }
        #         logger.info(f"{second_pair} Ticker: Price={eth_price}, Volume={eth_volume}")
        #     except ValueError as ve:
        #         logger.error(f"Could not parse price/volume for {second_pair} from ticker data: {eth_ticker_data}. Error: {ve}")
        # else:
        #    logger.warning(f"Failed to fetch {second_pair} ticker data or 'lastPrice' missing.")


        # 1.b. Fetch account balances (Example of another data_collector call)
        logger.info("Fetching account balances from Binance...")
        account_balances = fetch_account_balances()
        if account_balances is not None: # Returns a list or None on error
            logger.info(f"Fetched {len(account_balances)} asset balances.")
            # Update AVAILABLE_BALANCES (simplified representation)
            # A more robust update would iterate and match assets.
            temp_balances = {"USD": 0.0, "USDT": 0.0} # Initialize with common quote assets
            for bal in account_balances:
                asset = bal['asset']
                free_amount = float(bal['free'])
                if asset in AVAILABLE_BALANCES or asset.upper() in ["USDT", "BTC", "ETH"]: # Track specific assets
                    temp_balances[asset.upper()] = free_amount
            AVAILABLE_BALANCES = temp_balances # Overwrite with fetched (simplified)
            logger.info(f"Updated AVAILABLE_BALANCES for tracking: {AVAILABLE_BALANCES}")
        else:
            logger.warning("Failed to fetch account balances.")


        # 2. Fetch News & AI Analysis
        logger.info("Fetching news and performing AI analysis...")
        ai_sentiment_for_engine = {'sentiment': 'neutral', 'reasoning': 'Default: No news or analysis yet.'}
        try:
            # Ensure NEWS_API_KEY is available, either via config or direct check
            if not config.NEWS_API_KEY:
                logger.warning("NEWS_API_KEY not found. Skipping news collection.")
            else:
                news_articles = news_collector.fetch_crypto_news(
                    config.NEWS_API_KEY,
                    query="Bitcoin OR Ethereum OR cryptocurrency",
                    num_articles=3 # Fetch fewer articles for faster cycle in testing
                )
                if news_articles:
                    logger.info(f"Fetched {len(news_articles)} news articles.")
                    # Analyze the first relevant article (simple strategy)
                    # More complex: analyze all, look for BTC/ETH specific, aggregate sentiment
                    article_to_analyze = news_articles[0] # Or find most relevant
                    full_text_to_analyze = f"{article_to_analyze['headline']}. {article_to_analyze['body']}"

                    # Determine target_cryptos for focused analysis
                    target_cryptos_in_news = []
                    if "bitcoin" in full_text_to_analyze.lower() or "btc" in full_text_to_analyze.lower():
                        target_cryptos_in_news.append("Bitcoin")
                    if "ethereum" in full_text_to_analyze.lower() or "eth" in full_text_to_analyze.lower():
                        target_cryptos_in_news.append("Ethereum")

                    logger.info(f"Analyzing sentiment for article: \"{article_to_analyze['headline'][:50]}...\" (Targets: {target_cryptos_in_news if target_cryptos_in_news else 'General'})")
                    ai_result = ai_analyst.analyze_sentiment_gemini(full_text_to_analyze, target_cryptos=target_cryptos_in_news if target_cryptos_in_news else None)
                    if ai_result and ai_result.get('error') is None:
                        ai_sentiment_for_engine = ai_result
                        logger.info(f"AI Sentiment: {ai_sentiment_for_engine['sentiment']}. Reasoning: {ai_sentiment_for_engine['reasoning']}")
                    elif ai_result:
                        logger.warning(f"AI analysis returned an error: {ai_result.get('error')} - {ai_result.get('reasoning')}")
                    else:
                        logger.warning("AI analysis failed or returned no result.")
                else:
                    logger.info("No news articles fetched.")
        except Exception as e:
            error_alert(logger, f"Error during news collection or AI analysis: {e}", exc_info=True)


        # 3. Get Trading Proposal
        logger.info("Generating trading proposal...")
        if not market_data_for_engine:
            logger.warning("Market data is empty, cannot generate proposal. Holding.")
            trade_proposal = {'action': 'HOLD', 'reason': 'Market data unavailable.'}
        else:
            trade_proposal = decision_engine.generate_trade_proposal(market_data_for_engine, ai_sentiment_for_engine)

        logger.info(f"Decision Engine Proposal: {trade_proposal}")

        # 4. Risk Management & Order Execution
        action = trade_proposal.get('action', 'HOLD').upper()
        symbol = trade_proposal.get('symbol') # e.g., BTCUSD

        if action in ['BUY', 'SELL'] and symbol:
            logger.info(f"Processing '{action}' proposal for '{symbol}'.")

            percentage_capital_to_allocate = trade_proposal.get('amount_percentage_capital', 0.0)
            if percentage_capital_to_allocate <= 0:
                logger.warning(f"Proposal amount_percentage_capital is {percentage_capital_to_allocate}. Skipping trade.")
            else:
                current_asset_price = market_data_for_engine.get(symbol, {}).get('price')
                if not current_asset_price:
                    logger.error(f"Cannot execute {action} for {symbol}: Price data unavailable. Holding.")
                else:
                    risk_checked_proposal = {
                        'action': action,
                        'symbol': symbol,
                        'price': current_asset_price,
                        # 'amount_crypto' and 'estimated_value_usd' to be calculated for risk check
                    }

                    asset_to_be_spent_symbol = "" # e.g., "USDT" for buying BTC in BTCUSDT
                    available_balance_of_asset_to_be_spent = 0.0
                    amount_of_asset_to_spend_for_trade = 0.0
                    base_asset_symbol = "" # e.g., "BTC" for BTCUSDT
                    quote_asset_symbol = "" # e.g., "USDT" for BTCUSDT

                    # Determine base and quote assets from symbol (e.g., BTCUSDT)
                    # This is a simplified assumption, real exchanges might have more complex pairings.
                    # Common quote assets: USDT, BUSD, USDC, USD, BTC, ETH...
                    known_quote_assets = ["USDT", "BUSD", "USDC", "TUSD", "USD", "DAI", "PAX"] # Add more if needed

                    temp_quote = ""
                    for qa in known_quote_assets:
                        if symbol.endswith(qa):
                            temp_quote = qa
                            break
                    if temp_quote:
                        quote_asset_symbol = temp_quote
                        base_asset_symbol = symbol[:-len(quote_asset_symbol)]
                    else: # Fallback for pairs like ETHBTC
                        # Heuristic: assume last 3 or 4 chars are quote if common like BTC/ETH
                        if symbol.endswith("BTC") and len(symbol) > 3:
                            quote_asset_symbol = "BTC"
                            base_asset_symbol = symbol[:-3]
                        elif symbol.endswith("ETH") and len(symbol) > 3:
                            quote_asset_symbol = "ETH"
                            base_asset_symbol = symbol[:-3]
                        else:
                            logger.error(f"Could not determine base/quote for symbol {symbol}. Skipping trade logic.")
                            return  # Exit the function instead of using 'continue'

                    logger.info(f"Determined Base: {base_asset_symbol}, Quote: {quote_asset_symbol} for symbol {symbol}")


                    if action == 'BUY': # Buying base_asset with quote_asset
                        asset_to_be_spent_symbol = quote_asset_symbol
                        available_balance_of_asset_to_be_spent = AVAILABLE_BALANCES.get(quote_asset_symbol, 0.0)

                        # Calculate quote_asset value of the trade based on percentage of total capital (if quote is USD-like)
                        # Or percentage of available quote_asset if not USD-like.
                        # For simplicity, let's assume percentage_capital_to_allocate refers to a portion of available quote_asset
                        # if quote_asset is not USD. If it is USDT/BUSD etc., assume it's a proxy for USD capital.

                        # If we treat TOTAL_CAPITAL_USD as the main reference:
                        estimated_value_in_quote_asset_terms = TOTAL_CAPITAL_USD * percentage_capital_to_allocate
                        # This line assumes TOTAL_CAPITAL_USD can be directly converted to quote_asset_symbol for spending.
                        # This is true if quote_asset_symbol is USD, or a stablecoin like USDT.
                        # If quote_asset_symbol is BTC (e.g. for ETHBTC), this logic needs adjustment.
                        # For now, assume quote_asset_symbol is USDT or similar stablecoin.

                        amount_of_asset_to_spend_for_trade = estimated_value_in_quote_asset_terms

                        # Calculate base_asset amount (quantity) from quote_asset value and current price
                        quantity_base_asset = amount_of_asset_to_spend_for_trade / current_asset_price

                        risk_checked_proposal['estimated_value_quote'] = amount_of_asset_to_spend_for_trade
                        risk_checked_proposal['quantity'] = quantity_base_asset # For Binance, it's 'quantity'

                    elif action == 'SELL': # Selling base_asset for quote_asset
                        asset_to_be_spent_symbol = base_asset_symbol
                        available_balance_of_asset_to_be_spent = AVAILABLE_BALANCES.get(base_asset_symbol, 0.0)

                        # Amount to sell is a percentage of available base_asset
                        quantity_base_asset = available_balance_of_asset_to_be_spent * percentage_capital_to_allocate
                        amount_of_asset_to_spend_for_trade = quantity_base_asset # Spending Base Asset

                        estimated_value_in_quote_asset_terms = quantity_base_asset * current_asset_price

                        risk_checked_proposal['estimated_value_quote'] = estimated_value_in_quote_asset_terms
                        risk_checked_proposal['quantity'] = quantity_base_asset

                    logger.debug(f"Data for Risk Check: Total Capital (ref USD): {TOTAL_CAPITAL_USD}, Open Positions: {current_open_positions}, "
                                 f"Asset to spend: {asset_to_be_spent_symbol}, Available: {available_balance_of_asset_to_be_spent}, "
                                 f"Proposed trade value (in quote asset {quote_asset_symbol}): {risk_checked_proposal.get('estimated_value_quote')}, "
                                 f"Proposed quantity (of base asset {base_asset_symbol}): {risk_checked_proposal.get('quantity')}")

                    # The risk_management.is_trade_approved function might need its parameters updated
                    # if it was tightly coupled to 'estimated_value_usd' and 'amount_crypto' keys.
                    # For now, we assume it can work with 'estimated_value_quote' and 'quantity'.
                    # Or, we adapt the call:
                    temp_risk_proposal_for_check = risk_checked_proposal.copy()
                    temp_risk_proposal_for_check['estimated_value_usd'] = risk_checked_proposal.get('estimated_value_quote') # Assuming quote is USD-like for total capital check
                    temp_risk_proposal_for_check['amount_crypto'] = risk_checked_proposal.get('quantity')

                    is_approved, reason, conceptual_sl = risk_management.is_trade_approved(
                        temp_risk_proposal_for_check, # Use the adapted proposal for the check
                        TOTAL_CAPITAL_USD, # Still using this as overall reference
                        current_open_positions,
                        available_balance_of_asset_to_be_spent,
                        asset_symbol_being_spent=asset_to_be_spent_symbol
                    )

                    if is_approved:
                        logger.info(f"Trade approved by Risk Management: {reason}. Conceptual SL: {conceptual_sl}")

                        order_quantity_str = f"{risk_checked_proposal['quantity']:.8f}" # Format for exchange
                        order_price_str = f"{risk_checked_proposal['price']:.2f}" # Format for exchange. Precision may vary by pair.

                        logger.info(f"Attempting to place {action} order for {order_quantity_str} {base_asset_symbol} (in {symbol} market) at {order_price_str} {quote_asset_symbol}")

                        # order_manager.place_limit_order will handle client initialization check
                        placed_order_details = order_manager.place_limit_order(
                            symbol=symbol,      # Full market symbol e.g. BTCUSDT
                            quantity=order_quantity_str,
                            price=order_price_str,
                            side=action.upper() # Expects "BUY" or "SELL"
                        )
                        logger.info(f"Order placement response: {placed_order_details}")

                        # Binance order success typically returns a dict with 'orderId', 'status', etc.
                        # Error responses are handled by _handle_binance_api_error in order_manager
                        if isinstance(placed_order_details, dict) and placed_order_details.get("orderId") and placed_order_details.get("result") != "error":
                            logger.info(f"Order {placed_order_details['orderId']} placed successfully for {symbol}.")
                            # --- Simplified State Update ---
                            if action == 'BUY': # Bought base_asset, spent quote_asset
                                AVAILABLE_BALANCES[quote_asset_symbol] = AVAILABLE_BALANCES.get(quote_asset_symbol, 0.0) - risk_checked_proposal['estimated_value_quote']
                                AVAILABLE_BALANCES[base_asset_symbol] = AVAILABLE_BALANCES.get(base_asset_symbol, 0.0) + risk_checked_proposal['quantity']
                                current_open_positions += 1
                            elif action == 'SELL': # Sold base_asset, received quote_asset
                                AVAILABLE_BALANCES[base_asset_symbol] = AVAILABLE_BALANCES.get(base_asset_symbol, 0.0) - risk_checked_proposal['quantity']
                                AVAILABLE_BALANCES[quote_asset_symbol] = AVAILABLE_BALANCES.get(quote_asset_symbol, 0.0) + risk_checked_proposal['estimated_value_quote']
                                current_open_positions = max(0, current_open_positions - 1)
                            logger.info(f"Updated Balances (simplified): {AVAILABLE_BALANCES}, Open Positions: {current_open_positions}")
                        elif isinstance(placed_order_details, dict) and placed_order_details.get("result") == "error":
                            error_detail = placed_order_details.get('message', 'Unknown error during order placement.')
                            error_code = placed_order_details.get('code', '')
                            error_alert(logger, f"Failed to place {action} order for {symbol}. Reason: {error_detail} (Code: {error_code})")
                        else:
                            error_alert(logger, f"Failed to place {action} order for {symbol}. Unexpected response structure: {placed_order_details}")
                    else:
                        logger.info(f"Trade for {symbol} denied by Risk Management: {reason}")
        else:
            logger.info(f"Holding action proposed for {symbol if symbol else 'all assets'}. Reason: {trade_proposal.get('reason')}")

        # Example: Fetch active orders for the default pair (read-only test)
        logger.info(f"Fetching active orders for {default_pair} as a test...")
        active_orders_test = order_manager.get_active_orders(symbol=default_pair)
        if isinstance(active_orders_test, list):
            logger.info(f"Found {len(active_orders_test)} active order(s) for {default_pair}: {active_orders_test}")
        elif isinstance(active_orders_test, dict) and active_orders_test.get("result") == "error":
            logger.warning(f"Could not fetch active orders for {default_pair}: {active_orders_test.get('message')}")
        else:
            logger.warning(f"Unexpected response when fetching active orders for {default_pair}: {active_orders_test}")


        logger.info("Trading cycle finished.")
    # --- End of Main Bot Loop Function ---


    # --- Main Execution ---
    logger.info("Entering main bot execution block...")
    try:
        # For Phase 2, run the trading cycle once for demonstration.
        # A real bot would loop with time.sleep(config.MAIN_LOOP_SLEEP_INTERVAL)
        run_trading_cycle()

        # Example of a loop (commented out for single run in Phase 2 dev)
        # while True:
        #     run_trading_cycle()
        #     logger.info(f"Sleeping for {config.MAIN_LOOP_SLEEP_INTERVAL} seconds until next cycle.")
        #     time.sleep(config.MAIN_LOOP_SLEEP_INTERVAL)

    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt caught in main. Initiating shutdown.")
        handle_shutdown_signal(signal.SIGINT, None) # Call the handler directly
    except Exception as e:
        error_message = f"An unexpected error occurred in main execution: {e}"
        error_alert(logger, error_message, exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Trading Bot shutting down.")


if __name__ == "__main__":
    main()
