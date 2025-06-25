# test_risk_management.py
import unittest
from risk_management import (
    check_position_size,
    check_max_open_positions,
    calculate_conceptual_stop_loss,
    check_minimum_balance,
    is_trade_approved,
    MAX_CAPITAL_PER_TRADE_PERCENTAGE,
    MAX_CONCURRENT_OPEN_TRADES,
    DEFAULT_STOP_LOSS_PERCENTAGE,
    MIN_USD_BALANCE_AFTER_TRADE
)

class TestRiskManagement(unittest.TestCase):

    def test_check_position_size(self):
        self.assertTrue(check_position_size(100, 10000, 0.02)[0])  # 1% < 2%
        self.assertFalse(check_position_size(300, 10000, 0.02)[0]) # 3% > 2%
        self.assertTrue(check_position_size(200, 10000, 0.02)[0])  # 2% == 2%
        self.assertFalse(check_position_size(100, 0, 0.02)[0])     # Zero capital
        self.assertFalse(check_position_size(100, -100, 0.02)[0])  # Negative capital
        self.assertIn("exceeds max allowed", check_position_size(300, 10000, 0.02)[1])
        self.assertEqual("Total capital is zero or negative.", check_position_size(100, 0, 0.02)[1])

    def test_check_max_open_positions(self):
        self.assertTrue(check_max_open_positions(0, 3)[0])
        self.assertTrue(check_max_open_positions(2, 3)[0])
        self.assertFalse(check_max_open_positions(3, 3)[0])
        self.assertFalse(check_max_open_positions(4, 3)[0])
        self.assertIn("exceed max 3 open positions", check_max_open_positions(3, 3)[1])

    def test_calculate_conceptual_stop_loss(self):
        self.assertAlmostEqual(calculate_conceptual_stop_loss(100, "BUY", 0.05), 95.0)
        self.assertAlmostEqual(calculate_conceptual_stop_loss(100, "SELL", 0.05), 105.0)
        self.assertIsNone(calculate_conceptual_stop_loss(100, "HOLD", 0.05))
        self.assertIsNone(calculate_conceptual_stop_loss(0, "BUY", 0.05))
        self.assertIsNone(calculate_conceptual_stop_loss(-10, "BUY", 0.05))


    def test_check_minimum_balance(self):
        # Spending USD for a BUY
        self.assertTrue(check_minimum_balance(1000, 500, MIN_USD_BALANCE_AFTER_TRADE)[0]) # 1000-500=500 > 10
        self.assertFalse(check_minimum_balance(1000, 995, MIN_USD_BALANCE_AFTER_TRADE)[0])# 1000-995=5 < 10
        self.assertTrue(check_minimum_balance(100, 90, MIN_USD_BALANCE_AFTER_TRADE)[0]) # 100-90=10 == 10
        self.assertFalse(check_minimum_balance(500, 1000, MIN_USD_BALANCE_AFTER_TRADE)[0])# Insufficient to spend
        self.assertIn("Insufficient balance", check_minimum_balance(10, 20, 0)[1])
        self.assertIn("below minimum required", check_minimum_balance(100, 95, 10)[1])

        # Spending Crypto for a SELL (min_required_balance_after_trade is 0 for crypto in this example)
        self.assertTrue(check_minimum_balance(0.5, 0.1, 0)[0])
        self.assertFalse(check_minimum_balance(0.5, 0.6, 0)[0]) # Insufficient crypto
        self.assertTrue(check_minimum_balance(0.1, 0.1, 0)[0]) # Spend all available, remaining 0 is fine


    def setUp(self):
        self.total_capital_usd = 10000.0
        self.open_positions = 1
        self.available_usd = 5000.0
        self.available_btc = 0.5

        self.base_buy_proposal = {
            'action': 'BUY',
            'symbol': 'BTCUSD',
            'amount_crypto': 0.002,  # 0.002 BTC * 50000 USD/BTC = 100 USD (1% of 10k capital)
            'price': 50000.0,
            'estimated_value_usd': 100.0
        }
        self.base_sell_proposal = { # Adjusted to be within 2% capital limit
            'action': 'SELL',
            'symbol': 'BTCUSD',
            'amount_crypto': 0.003,  # 0.003 BTC * 50000 USD/BTC = 150 USD (1.5% of 10k capital)
            'price': 50000.0,
            'estimated_value_usd': 150.0
        }

    def test_is_trade_approved_buy_ok(self):
        approved, reason, sl = is_trade_approved(
            self.base_buy_proposal, self.total_capital_usd, self.open_positions,
            self.available_usd, "USD"
        )
        self.assertTrue(approved)
        self.assertEqual(reason, "Trade approved by risk management.")
        self.assertAlmostEqual(sl, 50000 * (1 - DEFAULT_STOP_LOSS_PERCENTAGE))

    def test_is_trade_approved_sell_ok(self):
        approved, reason, sl = is_trade_approved(
            self.base_sell_proposal, self.total_capital_usd, self.open_positions,
            self.available_btc, "BTC"
        )
        self.assertTrue(approved)
        self.assertEqual(reason, "Trade approved by risk management.")
        self.assertAlmostEqual(sl, 50000 * (1 + DEFAULT_STOP_LOSS_PERCENTAGE))

    def test_is_trade_approved_fail_position_size(self):
        proposal = self.base_buy_proposal.copy()
        proposal['estimated_value_usd'] = self.total_capital_usd * MAX_CAPITAL_PER_TRADE_PERCENTAGE * 2 # Too large
        proposal['amount_crypto'] = proposal['estimated_value_usd'] / proposal['price']

        approved, reason, _ = is_trade_approved(
            proposal, self.total_capital_usd, self.open_positions,
            self.available_usd, "USD"
        )
        self.assertFalse(approved)
        self.assertIn("exceeds max allowed", reason)

    def test_is_trade_approved_fail_max_open_positions(self):
        approved, reason, _ = is_trade_approved(
            self.base_buy_proposal, self.total_capital_usd, MAX_CONCURRENT_OPEN_TRADES, # Already at max
            self.available_usd, "USD"
        )
        self.assertFalse(approved)
        self.assertIn("exceed max", reason)

    def test_is_trade_approved_fail_min_usd_balance_buy(self):
        proposal = { # Trade value $150, within 2% of 10k capital
            'action': 'BUY', 'symbol': 'BTCUSD', 'price': 50000.0,
            'amount_crypto': 0.003, 'estimated_value_usd': 150.0
        }
        available_usd_just_enough_to_fail_min = 150.0 + MIN_USD_BALANCE_AFTER_TRADE - 1.0 # e.g. 150 + 10 - 1 = 159

        approved, reason, _ = is_trade_approved(
            proposal, self.total_capital_usd, self.open_positions,
            available_usd_just_enough_to_fail_min, "USD"
        )
        self.assertFalse(approved)
        self.assertIn("below minimum required", reason)

    def test_is_trade_approved_fail_insufficient_usd_balance_buy(self):
        proposal = { # Trade value $150, within 2% of 10k capital
            'action': 'BUY', 'symbol': 'BTCUSD', 'price': 50000.0,
            'amount_crypto': 0.003, 'estimated_value_usd': 150.0
        }
        insufficient_usd_to_cover_trade = 100.0 # Needs 150 USD

        approved, reason, _ = is_trade_approved(
            proposal, self.total_capital_usd, self.open_positions,
            insufficient_usd_to_cover_trade, "USD"
        )
        self.assertFalse(approved)
        self.assertIn("Insufficient balance of asset to spend", reason)

    def test_is_trade_approved_fail_insufficient_crypto_balance_sell(self):
        proposal = { # Selling 0.003 BTC (value $150), within 2% of 10k capital
            'action': 'SELL', 'symbol': 'BTCUSD', 'price': 50000.0,
            'amount_crypto': 0.003, 'estimated_value_usd': 150.0
        }
        insufficient_btc_to_cover_trade = 0.001 # Needs 0.003 BTC

        approved, reason, _ = is_trade_approved(
            proposal, self.total_capital_usd, self.open_positions,
            insufficient_btc_to_cover_trade, "BTC"
        )
        self.assertFalse(approved)
        self.assertIn("Insufficient balance of asset to spend", reason)

    def test_is_trade_approved_incomplete_proposal(self):
        incomplete_proposal = {'action': 'BUY', 'symbol': 'BTCUSD'} # Missing price, amounts
        approved, reason, _ = is_trade_approved(
            incomplete_proposal, self.total_capital_usd, self.open_positions,
            self.available_usd, "USD"
        )
        self.assertFalse(approved)
        self.assertEqual(reason, "Trade proposal incomplete.")

    def test_is_trade_approved_invalid_action(self):
        proposal = self.base_buy_proposal.copy()
        proposal['action'] = 'HOLD'
        approved, reason, _ = is_trade_approved(
            proposal, self.total_capital_usd, self.open_positions,
            self.available_usd, "USD"
        )
        self.assertFalse(approved)
        self.assertEqual(reason, "Invalid action 'HOLD' for risk approval.")

if __name__ == '__main__':
    unittest.main()
