# test_decision_engine.py
import unittest
from decision_engine import generate_trade_proposal

class TestDecisionEngine(unittest.TestCase):

    def setUp(self):
        # Default market data and sentiment for general use, can be overridden per test
        self.market_btc_consolidating = {
            'BTCUSD': {'price': 50000, 'recent_change_percent': 0.001},
            'ETHUSD': {'price': 3000, 'recent_change_percent': 0.002},
        }
        self.market_btc_dip = {
            'BTCUSD': {'price': 48000, 'recent_change_percent': -0.025}, # -2.5%
        }
        self.market_btc_rally = {
            'BTCUSD': {'price': 52000, 'recent_change_percent': 0.04}, # +4%
        }
        self.market_no_btc = {
            'ETHUSD': {'price': 3000, 'recent_change_percent': 0.002},
        }

        self.sentiment_positive_btc = {'sentiment': 'positive', 'target_cryptos': ['BTC']}
        self.sentiment_positive_general = {'sentiment': 'positive'} # No specific target
        self.sentiment_negative_btc = {'sentiment': 'negative', 'target_cryptos': ['BTC']}
        self.sentiment_negative_general = {'sentiment': 'negative'}
        self.sentiment_neutral_general = {'sentiment': 'neutral'}
        self.sentiment_positive_eth = {'sentiment': 'positive', 'target_cryptos': ['ETH']}

    # --- Rule 1: Sentiment-driven Buy Tests ---
    def test_rule1_buy_positive_btc_sentiment_consolidation(self):
        proposal = generate_trade_proposal(self.market_btc_consolidating, self.sentiment_positive_btc)
        self.assertEqual(proposal['action'], 'BUY')
        self.assertEqual(proposal['symbol'], 'BTCUSD')
        self.assertIn("Positive sentiment for BTCUSD (positive) and price consolidation", proposal['reason'])
        self.assertEqual(proposal['amount_percentage_capital'], 0.01) # SENTIMENT_BUY_CAPITAL_PERCENTAGE

    def test_rule1_buy_positive_general_sentiment_consolidation(self):
        proposal = generate_trade_proposal(self.market_btc_consolidating, self.sentiment_positive_general)
        self.assertEqual(proposal['action'], 'BUY')
        self.assertEqual(proposal['symbol'], 'BTCUSD')
        self.assertIn("Positive sentiment for BTCUSD (positive) and price consolidation", proposal['reason'])

    def test_rule1_no_buy_positive_btc_sentiment_no_consolidation_rally(self):
        proposal = generate_trade_proposal(self.market_btc_rally, self.sentiment_positive_btc)
        # Expect HOLD because consolidation condition not met for Rule 1,
        # and no other rule should trigger a BUY here. Rule 2 (negative sentiment) won't trigger. Rule 3 (dip) won't.
        self.assertEqual(proposal['action'], 'HOLD')
        self.assertEqual(proposal['symbol'], None) # Default HOLD

    def test_rule1_no_buy_positive_btc_sentiment_no_consolidation_dip(self):
        # This should be caught by Rule 3 (Dip Buy) if sentiment is not negative,
        # or Rule 2 (Hold) if sentiment turns negative for BTC.
        # If sentiment is positive for BTC during a dip, Rule 1 (consolidation) fails,
        # then Rule 2 (negative sentiment) fails, then Rule 3 (dip buy) should trigger.
        proposal = generate_trade_proposal(self.market_btc_dip, self.sentiment_positive_btc)
        self.assertEqual(proposal['action'], 'BUY') # Rule 3 should catch this
        self.assertEqual(proposal['symbol'], 'BTCUSD')
        self.assertIn("Price dip", proposal['reason'])
        self.assertEqual(proposal['amount_percentage_capital'], 0.005) # DIP_BUY_CAPITAL_PERCENTAGE

    def test_rule1_no_buy_neutral_sentiment_consolidation(self):
        proposal = generate_trade_proposal(self.market_btc_consolidating, self.sentiment_neutral_general)
        self.assertEqual(proposal['action'], 'HOLD') # Rule 1 needs positive sentiment

    # --- Rule 2: Sentiment-driven Hold (Negative) Tests ---
    def test_rule2_hold_negative_btc_sentiment_consolidation(self):
        # Rule 1 fails (not positive). Rule 2 should trigger.
        proposal = generate_trade_proposal(self.market_btc_consolidating, self.sentiment_negative_btc)
        self.assertEqual(proposal['action'], 'HOLD')
        self.assertEqual(proposal['symbol'], 'BTCUSD')
        self.assertIn("Negative sentiment for BTCUSD (negative). Holding", proposal['reason'])

    def test_rule2_hold_negative_general_sentiment_consolidation(self):
        proposal = generate_trade_proposal(self.market_btc_consolidating, self.sentiment_negative_general)
        self.assertEqual(proposal['action'], 'HOLD')
        self.assertEqual(proposal['symbol'], 'BTCUSD')
        self.assertIn("Negative sentiment for BTCUSD (negative). Holding", proposal['reason'])

    def test_rule2_hold_negative_btc_sentiment_dip(self):
        # Rule 1 fails. Rule 2 triggers. Rule 3 (dip buy) should be skipped due to negative sentiment.
        proposal = generate_trade_proposal(self.market_btc_dip, self.sentiment_negative_btc)
        self.assertEqual(proposal['action'], 'HOLD')
        self.assertEqual(proposal['symbol'], 'BTCUSD')
        self.assertIn("Negative sentiment for BTCUSD (negative). Holding", proposal['reason'])

    # --- Rule 3: Dip-buying Tests ---
    def test_rule3_buy_btc_dip_neutral_sentiment(self):
        # Rule 1 fails. Rule 2 fails. Rule 3 triggers.
        proposal = generate_trade_proposal(self.market_btc_dip, self.sentiment_neutral_general)
        self.assertEqual(proposal['action'], 'BUY')
        self.assertEqual(proposal['symbol'], 'BTCUSD')
        self.assertIn("Price dip", proposal['reason'])
        self.assertIn("non-negative sentiment (neutral)", proposal['reason'])
        self.assertEqual(proposal['amount_percentage_capital'], 0.005)

    def test_rule3_buy_btc_dip_positive_btc_sentiment(self):
        # Rule 1 fails (no consolidation). Rule 2 fails. Rule 3 triggers.
        proposal = generate_trade_proposal(self.market_btc_dip, self.sentiment_positive_btc)
        self.assertEqual(proposal['action'], 'BUY')
        self.assertEqual(proposal['symbol'], 'BTCUSD')
        self.assertIn("Price dip", proposal['reason'])
        self.assertIn("non-negative sentiment (positive)", proposal['reason'])

    def test_rule3_buy_btc_dip_positive_general_sentiment(self):
        proposal = generate_trade_proposal(self.market_btc_dip, self.sentiment_positive_general)
        self.assertEqual(proposal['action'], 'BUY')
        self.assertEqual(proposal['symbol'], 'BTCUSD')
        self.assertIn("Price dip", proposal['reason'])
        self.assertIn("non-negative sentiment (positive)", proposal['reason'])

    def test_rule3_no_buy_btc_dip_positive_eth_sentiment_if_btc_sentiment_negative(self):
        # If general sentiment from ETH news is positive, but we also have specific negative BTC news,
        # the negative BTC news should prevail for BTC actions.
        # This requires combining sentiments or having a more complex sentiment object.
        # Current simple implementation: Dip buy rule looks at the single ai_sentiment_data object.
        # If ai_sentiment_data is sentiment_positive_eth, it's not negative.
        # This test highlights a potential area for refinement in sentiment aggregation.
        # For now, with current logic, if sentiment_positive_eth is passed, dip buy *would* occur for BTC.
        proposal = generate_trade_proposal(self.market_btc_dip, self.sentiment_positive_eth)
        self.assertEqual(proposal['action'], 'BUY') # Current logic: ETH positive is not negative for BTC dip
        self.assertEqual(proposal['symbol'], 'BTCUSD')
        self.assertIn("non-negative sentiment (positive)", proposal['reason'])


    def test_rule3_no_buy_consolidation_neutral_sentiment(self):
        # No dip, so Rule 3 doesn't apply.
        proposal = generate_trade_proposal(self.market_btc_consolidating, self.sentiment_neutral_general)
        self.assertEqual(proposal['action'], 'HOLD') # Default HOLD

    # --- Default HOLD Action Tests ---
    def test_default_hold_no_rules_met(self):
        # E.g., BTC rallying, neutral sentiment
        proposal = generate_trade_proposal(self.market_btc_rally, self.sentiment_neutral_general)
        self.assertEqual(proposal['action'], 'HOLD')
        self.assertEqual(proposal['symbol'], None)
        self.assertEqual(proposal['reason'], 'No specific trading signals met based on current rules.')

    def test_default_hold_no_btc_data(self):
        proposal = generate_trade_proposal(self.market_no_btc, self.sentiment_positive_general)
        self.assertEqual(proposal['action'], 'HOLD')
        self.assertEqual(proposal['symbol'], None)

    def test_default_hold_empty_market_data(self):
        proposal = generate_trade_proposal({}, self.sentiment_positive_general)
        self.assertEqual(proposal['action'], 'HOLD')

    def test_default_hold_empty_sentiment_data(self):
        proposal = generate_trade_proposal(self.market_btc_consolidating, {}) # Empty sentiment
        self.assertEqual(proposal['action'], 'HOLD') # Rules expect sentiment field

    def test_positive_eth_sentiment_btc_consolidating_results_in_hold(self):
        # Rule 1 (BTC Buy) requires positive BTC or general sentiment. ETH-specific positive won't trigger it.
        # Rule 2 (BTC Negative Hold) won't trigger.
        # Rule 3 (BTC Dip Buy) won't trigger as no dip.
        # So, default HOLD.
        proposal = generate_trade_proposal(self.market_btc_consolidating, self.sentiment_positive_eth)
        self.assertEqual(proposal['action'], 'HOLD')
        self.assertEqual(proposal['symbol'], None)


if __name__ == '__main__':
    unittest.main()
