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
    if not ai_analyst.IS_GEMINI_CONFIGURED:
        logger.warning("AI Analyst (Gemini) may not be configured due to missing GOOGLE_GENAI_API_KEY. Sentiment analysis will fail.")
    if not order_manager.API_KEY or not order_manager.API_SECRET:
        logger.warning("Order Manager (Gemini Exchange) may not be configured due to missing GEMINI_API_KEY/SECRET. Order placement will fail.")


    # --- Main Bot Loop Function ---
    def run_trading_cycle():
        nonlocal current_open_positions # Allow modification of this outer scope variable
        nonlocal TOTAL_CAPITAL_USD # Allow modification (though less likely to change than balances)
        nonlocal AVAILABLE_BALANCES

        logger.info("Starting new trading cycle...")

        # 1. Fetch Market Data
        logger.info("Fetching market data...")
        market_data_for_engine = {}
        btc_ticker = fetch_ticker_data(symbol="BTCUSD")
        if btc_ticker and btc_ticker.get('last'):
            market_data_for_engine['BTCUSD'] = {
                'price': float(btc_ticker['last']),
                'volume': float(btc_ticker['volume'].get('BTC', 0)), # Example: get BTC volume
                # 'recent_change_percent': 0.0 # Placeholder - data_collector doesn't provide this
            }
            logger.info(f"BTCUSD Ticker: Price={market_data_for_engine['BTCUSD']['price']}")
        else:
            logger.warning("Failed to fetch BTCUSD ticker data. Skipping this cycle for BTC decisions.")
            # Potentially skip cycle or handle missing data gracefully

        eth_ticker = fetch_ticker_data(symbol="ETHUSD") # Example for future expansion
        if eth_ticker and eth_ticker.get('last'):
             market_data_for_engine['ETHUSD'] = {
                'price': float(eth_ticker['last']),
                'volume': float(eth_ticker['volume'].get('ETH', 0)),
            }
             logger.info(f"ETHUSD Ticker: Price={market_data_for_engine['ETHUSD']['price']}")


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

                    asset_to_be_spent_symbol = ""
                    available_balance_of_asset_to_be_spent = 0.0
                    amount_of_asset_to_spend_for_trade = 0.0

                    if action == 'BUY':
                        asset_to_be_spent_symbol = "USD"
                        available_balance_of_asset_to_be_spent = AVAILABLE_BALANCES.get("USD", 0.0)

                        # Calculate USD value of the trade based on percentage of total capital
                        estimated_value_usd = TOTAL_CAPITAL_USD * percentage_capital_to_allocate
                        amount_of_asset_to_spend_for_trade = estimated_value_usd # Spending USD

                        # Calculate crypto amount from USD value and current price
                        amount_crypto = estimated_value_usd / current_asset_price

                        risk_checked_proposal['estimated_value_usd'] = estimated_value_usd
                        risk_checked_proposal['amount_crypto'] = amount_crypto

                    elif action == 'SELL':
                        # Assuming 'symbol' is like 'BTCUSD', so crypto_asset is 'BTC'
                        crypto_asset_symbol = symbol[:-3].upper() # BTC from BTCUSD
                        asset_to_be_spent_symbol = crypto_asset_symbol
                        available_balance_of_asset_to_be_spent = AVAILABLE_BALANCES.get(crypto_asset_symbol, 0.0)

                        # Amount to sell is a percentage of available crypto asset
                        amount_crypto = available_balance_of_asset_to_be_spent * percentage_capital_to_allocate
                        amount_of_asset_to_spend_for_trade = amount_crypto # Spending Crypto

                        estimated_value_usd = amount_crypto * current_asset_price

                        risk_checked_proposal['estimated_value_usd'] = estimated_value_usd
                        risk_checked_proposal['amount_crypto'] = amount_crypto

                    logger.debug(f"Data for Risk Check: Total Capital USD: {TOTAL_CAPITAL_USD}, Open Positions: {current_open_positions}, "
                                 f"Asset to spend: {asset_to_be_spent_symbol}, Available: {available_balance_of_asset_to_be_spent}, "
                                 f"Proposed trade value USD: {risk_checked_proposal.get('estimated_value_usd')}, "
                                 f"Proposed crypto amount: {risk_checked_proposal.get('amount_crypto')}")

                    is_approved, reason, conceptual_sl = risk_management.is_trade_approved(
                        risk_checked_proposal,
                        TOTAL_CAPITAL_USD,
                        current_open_positions,
                        available_balance_of_asset_to_be_spent,
                        asset_symbol_being_spent=asset_to_be_spent_symbol
                    )

                    if is_approved:
                        logger.info(f"Trade approved by Risk Management: {reason}. Conceptual SL: {conceptual_sl}")

                        order_amount_str = f"{risk_checked_proposal['amount_crypto']:.8f}" # Format for exchange
                        order_price_str = f"{risk_checked_proposal['price']:.2f}" # Format for exchange

                        logger.info(f"Attempting to place {action} order for {order_amount_str} {symbol} at {order_price_str}")

                        # Ensure order_manager is configured before calling
                        if order_manager.API_KEY and order_manager.API_SECRET:
                            placed_order_details = order_manager.place_limit_order(
                                symbol=symbol,
                                amount_crypto=order_amount_str,
                                price=order_price_str,
                                side=action.lower()
                            )
                            logger.info(f"Order placement response: {placed_order_details}")

                            if placed_order_details and placed_order_details.get("order_id") and not placed_order_details.get("result") == "error":
                                logger.info(f"Order {placed_order_details['order_id']} placed successfully for {symbol}.")
                                # --- Simplified State Update ---
                                if action == 'BUY':
                                    AVAILABLE_BALANCES['USD'] -= risk_checked_proposal['estimated_value_usd']
                                    AVAILABLE_BALANCES[symbol[:-3].upper()] += risk_checked_proposal['amount_crypto']
                                    current_open_positions += 1
                                elif action == 'SELL':
                                    AVAILABLE_BALANCES[symbol[:-3].upper()] -= risk_checked_proposal['amount_crypto']
                                    AVAILABLE_BALANCES['USD'] += risk_checked_proposal['estimated_value_usd']
                                    # Simple model: selling reduces an open position if any exist
                                    current_open_positions = max(0, current_open_positions - 1)
                                logger.info(f"Updated Balances: {AVAILABLE_BALANCES}, Open Positions: {current_open_positions}")
                            else:
                                error_detail = placed_order_details.get('message', 'Unknown error during order placement.')
                                error_alert(logger, f"Failed to place {action} order for {symbol}. Reason: {error_detail}")
                        else:
                            logger.error("Order Manager not configured with API keys. Cannot place order.")
                    else:
                        logger.info(f"Trade for {symbol} denied by Risk Management: {reason}")
        else:
            logger.info(f"Holding action proposed for {symbol if symbol else 'all assets'}. Reason: {trade_proposal.get('reason')}")

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
