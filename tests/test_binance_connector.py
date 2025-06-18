import unittest
import sys
import os

# Add the parent directory (project root) to the Python path
# This allows importing modules from 'core' and 'exchange_connectors'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from exchange_connectors.binance_connector import BinanceConnector
from core.exchange_interface import Exchange

class TestBinanceConnector(unittest.TestCase):
    """
    Unit tests for the BinanceConnector class.
    """

    def setUp(self):
        """
        Set up for test methods. This method is called before each test method.
        """
        self.connector = BinanceConnector()
        self.api_key = "test_api_key"
        self.api_secret = "test_api_secret"

    def test_instance_creation_and_interface_inheritance(self):
        """
        Test that BinanceConnector can be instantiated and inherits from Exchange.
        """
        self.assertIsInstance(self.connector, BinanceConnector, "Connector is not an instance of BinanceConnector")
        self.assertIsInstance(self.connector, Exchange, "Connector does not inherit from Exchange interface")
        print("TestBinanceConnector: test_instance_creation_and_interface_inheritance PASSED")

    def test_connect(self):
        """
        Test the connect method.
        For now, just ensures it runs without raising an exception.
        """
        try:
            self.connector.connect(self.api_key, self.api_secret)
            print(f"TestBinanceConnector: connect method called with API Key: {self.connector.api_key}")
        except Exception as e:
            self.fail(f"connect() method raised an exception unexpectedly: {e}")
        print("TestBinanceConnector: test_connect PASSED")

    def test_disconnect(self):
        """
        Test the disconnect method.
        For now, just ensures it runs without raising an exception.
        """
        try:
            self.connector.disconnect()
        except Exception as e:
            self.fail(f"disconnect() method raised an exception unexpectedly: {e}")
        print("TestBinanceConnector: test_disconnect PASSED")

    def test_get_account_balance(self):
        """
        Test the get_account_balance method.
        For now, ensures it runs and returns a dictionary.
        """
        try:
            balance = self.connector.get_account_balance()
            self.assertIsInstance(balance, dict, "get_account_balance() should return a dictionary.")
            print(f"TestBinanceConnector: get_account_balance returned: {balance}")
        except Exception as e:
            self.fail(f"get_account_balance() method raised an exception unexpectedly: {e}")
        print("TestBinanceConnector: test_get_account_balance PASSED")

    def test_get_market_data(self):
        """
        Test the get_market_data method.
        For now, ensures it runs and returns a dictionary.
        """
        symbol = "BTC/USDT"
        try:
            data = self.connector.get_market_data(symbol)
            self.assertIsInstance(data, dict, "get_market_data() should return a dictionary.")
            print(f"TestBinanceConnector: get_market_data for {symbol} returned: {data}")
        except Exception as e:
            self.fail(f"get_market_data() method raised an exception unexpectedly: {e}")
        print("TestBinanceConnector: test_get_market_data PASSED")

    def test_place_order(self):
        """
        Test the place_order method.
        For now, ensures it runs and returns a string (placeholder order ID).
        """
        symbol = "BTC/USDT"
        side = "buy"
        order_type = "limit"
        amount = 0.1
        price = 50000.0
        try:
            order_id = self.connector.place_order(symbol, side, order_type, amount, price)
            self.assertIsInstance(order_id, str, "place_order() should return a string order ID.")
            print(f"TestBinanceConnector: place_order for {symbol} returned order_id: {order_id}")
        except Exception as e:
            self.fail(f"place_order() method raised an exception unexpectedly: {e}")
        print("TestBinanceConnector: test_place_order PASSED")

    def test_cancel_order(self):
        """
        Test the cancel_order method.
        For now, ensures it runs and returns a boolean.
        """
        order_id = "test_order_id_123"
        try:
            result = self.connector.cancel_order(order_id)
            self.assertIsInstance(result, bool, "cancel_order() should return a boolean.")
            print(f"TestBinanceConnector: cancel_order for {order_id} returned: {result}")
        except Exception as e:
            self.fail(f"cancel_order() method raised an exception unexpectedly: {e}")
        print("TestBinanceConnector: test_cancel_order PASSED")

    def test_get_order_status(self):
        """
        Test the get_order_status method.
        For now, ensures it runs and returns a dictionary.
        """
        order_id = "test_order_id_123"
        try:
            status = self.connector.get_order_status(order_id)
            self.assertIsInstance(status, dict, "get_order_status() should return a dictionary.")
            print(f"TestBinanceConnector: get_order_status for {order_id} returned: {status}")
        except Exception as e:
            self.fail(f"get_order_status() method raised an exception unexpectedly: {e}")
        print("TestBinanceConnector: test_get_order_status PASSED")

if __name__ == '__main__':
    print("Running tests for BinanceConnector...")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    print("Finished running tests for BinanceConnector.")
