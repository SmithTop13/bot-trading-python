# decision_engine.py
# This module will contain the trading logic and decision-making process.

import logging

logger = logging.getLogger(__name__)

# --- Configuration for Decision Engine Rules (Hardcoded for now) ---
# Rule 1: Sentiment-driven Buy
SENTIMENT_BUY_THRESHOLD_POSITIVE = "positive"
SENTIMENT_BUY_CONSOLIDATION_MIN_PERCENT = -0.005 # -0.5%
SENTIMENT_BUY_CONSOLIDATION_MAX_PERCENT = 0.005  # +0.5%
SENTIMENT_BUY_CAPITAL_PERCENTAGE = 0.01          # 1% of capital

# Rule 2: Sentiment-driven Sell/Hold (Basic)
SENTIMENT_HOLD_THRESHOLD_NEGATIVE = "negative"

# Rule 3: Dip-buying
DIP_BUY_DROP_PERCENTAGE_THRESHOLD = -0.02 # -2% drop
DIP_BUY_SENTIMENT_NOT_NEGATIVE_THRESHOLDS = ["positive", "neutral"]
DIP_BUY_CAPITAL_PERCENTAGE = 0.005        # 0.5% of capital


def generate_trade_proposal(market_data: dict, ai_sentiment_data: dict) -> dict:
    """
    Generates a trade proposal based on market data and AI sentiment analysis.

    Args:
        market_data: A dictionary containing market information.
            Example: {
                'BTCUSD': {'price': 50000, 'volume': 1000, 'recent_change_percent': -0.001},
                'ETHUSD': {'price': 3000, 'volume': 5000, 'recent_change_percent': 0.002},
            }
            'recent_change_percent' is the change over a relevant short period.
        ai_sentiment_data: A dictionary containing AI sentiment analysis.
            Example: {
                'sentiment': 'positive', 'reasoning': 'Good news for BTC.',
                'target_cryptos': ['BTC'], # Optional, indicates primary focus of the news
                'error': None
            }
            Or if general: {'sentiment': 'neutral', 'reasoning': 'Market is calm.'}

    Returns:
        A dictionary representing a trade proposal:
        {
            'action': 'BUY' | 'SELL' | 'HOLD',
            'symbol': 'BTCUSD' | 'ETHUSD' | None, (None if HOLD and no specific symbol focus)
            'amount_percentage_capital': float (e.g., 0.01 for 1%), or None
            'reason': str (explanation for the decision)
            'price_at_decision': float | None (optional, price when decision was made)
        }
    """
    proposals = [] # Could generate multiple proposals if logic expands

    # For simplicity, let's focus on BTCUSD if no specific target from AI, or if target is BTC
    # This can be expanded to iterate over multiple symbols or use ai_sentiment_data['target_cryptos']
    # For now, we assume 'BTCUSD' is the primary focus if market_data for it exists.

    primary_symbol_focus = "BTCUSD" # Default focus
    # Could refine focus based on ai_sentiment_data['target_cryptos'] if available and relevant

    # --- Rule 1: Sentiment-driven Buy for BTCUSD ---
    if primary_symbol_focus in market_data and ai_sentiment_data:
        btc_market = market_data[primary_symbol_focus]
        sentiment = ai_sentiment_data.get('sentiment')
        # Check if sentiment is specifically about BTC or general positive
        is_btc_target = "btc" in [str(t).lower() for t in ai_sentiment_data.get('target_cryptos', [])]
        is_general_sentiment = not ai_sentiment_data.get('target_cryptos')

        if sentiment == SENTIMENT_BUY_THRESHOLD_POSITIVE and (is_btc_target or is_general_sentiment):
            price_change = btc_market.get('recent_change_percent')
            if price_change is not None and \
               SENTIMENT_BUY_CONSOLIDATION_MIN_PERCENT <= price_change <= SENTIMENT_BUY_CONSOLIDATION_MAX_PERCENT:
                reason = (f"Positive sentiment for {primary_symbol_focus} ({sentiment}) "
                          f"and price consolidation ({price_change*100:.2f}%).")
                logger.info(f"Decision Engine: Rule 1 Triggered - {reason}")
                proposals.append({
                    'action': 'BUY',
                    'symbol': primary_symbol_focus,
                    'amount_percentage_capital': SENTIMENT_BUY_CAPITAL_PERCENTAGE,
                    'reason': reason,
                    'price_at_decision': btc_market.get('price')
                })

    # --- Rule 2: Sentiment-driven Hold (if negative for BTC) ---
    if primary_symbol_focus in market_data and ai_sentiment_data and not proposals: # Only if no BUY proposal yet
        sentiment = ai_sentiment_data.get('sentiment')
        is_btc_target = "btc" in [str(t).lower() for t in ai_sentiment_data.get('target_cryptos', [])]
        is_general_sentiment = not ai_sentiment_data.get('target_cryptos')

        if sentiment == SENTIMENT_HOLD_THRESHOLD_NEGATIVE and (is_btc_target or is_general_sentiment):
            reason = f"Negative sentiment for {primary_symbol_focus} ({sentiment}). Holding or considering sell."
            logger.info(f"Decision Engine: Rule 2 Triggered - {reason}")
            proposals.append({
                'action': 'HOLD', # Could be SELL if we track open positions here
                'symbol': primary_symbol_focus,
                'amount_percentage_capital': None,
                'reason': reason,
                'price_at_decision': market_data[primary_symbol_focus].get('price')
            })

    # --- Rule 3: Dip-buying for BTCUSD ---
    if primary_symbol_focus in market_data and ai_sentiment_data and not proposals: # Only if no prior proposal
        btc_market = market_data[primary_symbol_focus]
        sentiment = ai_sentiment_data.get('sentiment')
        price_change = btc_market.get('recent_change_percent')

        if price_change is not None and price_change <= DIP_BUY_DROP_PERCENTAGE_THRESHOLD:
            # Check if sentiment is NOT strongly negative (allow neutral or positive)
            # If sentiment is specifically about BTC, use that. Otherwise, general sentiment.
            relevant_sentiment = sentiment
            is_btc_target = "btc" in [str(t).lower() for t in ai_sentiment_data.get('target_cryptos', [])]
            if not is_btc_target and ai_sentiment_data.get('target_cryptos'): # Sentiment is for other coins
                 pass # Don't use this sentiment for BTC dip buy unless it's general

            if relevant_sentiment in DIP_BUY_SENTIMENT_NOT_NEGATIVE_THRESHOLDS:
                reason = (f"Price dip ({price_change*100:.2f}%) for {primary_symbol_focus} "
                          f"with non-negative sentiment ({relevant_sentiment}).")
                logger.info(f"Decision Engine: Rule 3 Triggered - {reason}")
                proposals.append({
                    'action': 'BUY',
                    'symbol': primary_symbol_focus,
                    'amount_percentage_capital': DIP_BUY_CAPITAL_PERCENTAGE,
                    'reason': reason,
                    'price_at_decision': btc_market.get('price')
                })

    # --- Default Action ---
    if not proposals:
        logger.info("Decision Engine: No specific trading rules met. Proposing HOLD.")
        return {
            'action': 'HOLD',
            'symbol': None,
            'amount_percentage_capital': None,
            'reason': 'No specific trading signals met based on current rules.',
            'price_at_decision': None
        }

    # For now, just return the first proposal if multiple were generated (e.g. if rules overlap)
    # More sophisticated logic could prioritize or combine proposals.
    return proposals[0]


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Testing Decision Engine...")

    # Example Market Data
    market_1 = {
        'BTCUSD': {'price': 50000, 'volume': 1000, 'recent_change_percent': 0.001}, # Consolidation
        'ETHUSD': {'price': 3000, 'volume': 5000, 'recent_change_percent': 0.002},
    }
    market_2 = { # BTC Dip
        'BTCUSD': {'price': 48000, 'volume': 1200, 'recent_change_percent': -0.025}, # -2.5%
        'ETHUSD': {'price': 2900, 'volume': 5500, 'recent_change_percent': -0.03},
    }
    market_3 = { # BTC Price up
        'BTCUSD': {'price': 52000, 'volume': 900, 'recent_change_percent': 0.04}, # +4%
    }

    # Example AI Sentiment Data
    sentiment_positive_btc = {'sentiment': 'positive', 'reasoning': 'BTC looks great!', 'target_cryptos': ['BTC']}
    sentiment_positive_general = {'sentiment': 'positive', 'reasoning': 'Market looks great!'}
    sentiment_negative_btc = {'sentiment': 'negative', 'reasoning': 'BTC looks bad.', 'target_cryptos': ['BTC']}
    sentiment_neutral_general = {'sentiment': 'neutral', 'reasoning': 'Market is meh.'}
    sentiment_positive_eth = {'sentiment': 'positive', 'reasoning': 'ETH to the moon!', 'target_cryptos': ['ETH']}


    print("\n--- Test Case 1: Positive BTC Sentiment + Consolidation (Rule 1) ---")
    proposal1 = generate_trade_proposal(market_1, sentiment_positive_btc)
    print(f"Proposal 1: {proposal1}")
    assert proposal1['action'] == 'BUY' and proposal1['symbol'] == 'BTCUSD'

    print("\n--- Test Case 2: General Positive Sentiment + Consolidation (Rule 1) ---")
    proposal_gen_pos = generate_trade_proposal(market_1, sentiment_positive_general)
    print(f"Proposal Gen Pos: {proposal_gen_pos}")
    assert proposal_gen_pos['action'] == 'BUY' and proposal_gen_pos['symbol'] == 'BTCUSD'


    print("\n--- Test Case 3: Negative BTC Sentiment (Rule 2) ---")
    proposal2 = generate_trade_proposal(market_1, sentiment_negative_btc) # market_1 has consolidation
    print(f"Proposal 2: {proposal2}")
    assert proposal2['action'] == 'HOLD' and proposal2['symbol'] == 'BTCUSD'

    print("\n--- Test Case 4: BTC Dip + Neutral Sentiment (Rule 3) ---")
    proposal3 = generate_trade_proposal(market_2, sentiment_neutral_general)
    print(f"Proposal 3: {proposal3}")
    assert proposal3['action'] == 'BUY' and proposal3['symbol'] == 'BTCUSD'

    print("\n--- Test Case 5: BTC Dip + Positive ETH Sentiment (Should still trigger BTC dip if general conditions okay) ---")
    # This tests if non-BTC specific positive sentiment still allows BTC dip buy
    proposal_dip_eth_pos = generate_trade_proposal(market_2, sentiment_positive_eth)
    print(f"Proposal Dip ETH Pos: {proposal_dip_eth_pos}")
    # Expected: Dip Buy rule for BTC should trigger if the sentiment from ETH isn't negative for BTC.
    # Current logic for Rule 3: if sentiment is for other coins, it doesn't use that sentiment for BTC dip.
    # This means it will use the default 'neutral' if no general sentiment, which is fine.
    assert proposal_dip_eth_pos['action'] == 'BUY' and proposal_dip_eth_pos['symbol'] == 'BTCUSD'


    print("\n--- Test Case 6: BTC Dip + Negative BTC Sentiment (No Buy) ---")
    proposal4 = generate_trade_proposal(market_2, sentiment_negative_btc)
    print(f"Proposal 4: {proposal4}")
    # Should be HOLD because negative sentiment overrides dip-buy
    assert proposal4['action'] == 'HOLD' and proposal4['symbol'] == 'BTCUSD'


    print("\n--- Test Case 7: No specific rules met (e.g., BTC price up, neutral sentiment) ---")
    proposal5 = generate_trade_proposal(market_3, sentiment_neutral_general)
    print(f"Proposal 5: {proposal5}")
    assert proposal5['action'] == 'HOLD' and proposal5['symbol'] is None # Default HOLD

    print("\n--- Test Case 8: Positive ETH sentiment, BTC consolidating (No BTC action from this) ---")
    proposal_eth_pos_btc_consol = generate_trade_proposal(market_1, sentiment_positive_eth)
    print(f"Proposal ETH Pos BTC Consol: {proposal_eth_pos_btc_consol}")
    # Expect default HOLD because positive sentiment is for ETH, not BTC, and no other BTC rules met.
    assert proposal_eth_pos_btc_consol['action'] == 'HOLD'

    logger.info("Decision Engine testing finished.")
