import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory (project root) to the Python path
# This allows importing modules from 'core' and 'exchange_connectors'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from exchange_connectors.binance_connector import BinanceConnector, Client  # Import Client for patching
from core.exchange_interface import Exchange
from binance.exceptions import BinanceAPIException, BinanceRequestException


class TestBinanceConnector(unittest.TestCase):
    """
    Unit tests for the BinanceConnector class.
    """

    def setUp(self):
        """
        Set up for test methods. This method is called before each test method.
        """
        self.api_key = "test_api_key"
        self.api_secret = "test_api_secret"
        # Initialize connector without keys for some tests, with keys for others
        self.connector = BinanceConnector()
        self.connector_with_keys = BinanceConnector(api_key=self.api_key, api_secret=self.api_secret)
        print("TestBinanceConnector: setUp completed.")


    def test_instance_creation_and_interface_inheritance(self):
        """
        Test that BinanceConnector can be instantiated and inherits from Exchange.
        """
        self.assertIsInstance(self.connector, BinanceConnector, "Connector is not an instance of BinanceConnector")
        self.assertIsInstance(self.connector, Exchange, "Connector does not inherit from Exchange interface")
        self.assertIsNone(self.connector.api_key)
        self.assertIsNone(self.connector.api_secret)
        self.assertIsNotNone(self.connector_with_keys.api_key)
        self.assertIsNotNone(self.connector_with_keys.api_secret)
        print("TestBinanceConnector: test_instance_creation_and_interface_inheritance PASSED")

    @patch('exchange_connectors.binance_connector.Client')
    def test_connect_success_with_args(self, MockClient):
        """
        Test the connect method successfully connects when keys are passed as arguments.
        """
        print("TestBinanceConnector: test_connect_success_with_args started.")
        mock_client_instance = MockClient.return_value
        mock_client_instance.ping.return_value = {}  # Simulate successful ping
        mock_client_instance.get_server_time.return_value = {'serverTime': 1234567890}

        result = self.connector.connect(self.api_key, self.api_secret)

        self.assertTrue(result)
        MockClient.assert_called_once_with(self.api_key, self.api_secret)
        mock_client_instance.ping.assert_called_once()
        mock_client_instance.get_server_time.assert_called_once()
        self.assertIsNotNone(self.connector.client)
        self.assertEqual(self.connector.api_key, self.api_key)
        self.assertEqual(self.connector.api_secret, self.api_secret)
        print("TestBinanceConnector: test_connect_success_with_args PASSED")

    @patch('exchange_connectors.binance_connector.Client')
    def test_connect_success_with_init_keys(self, MockClient):
        """
        Test the connect method successfully connects when keys are provided during __init__.
        """
        print("TestBinanceConnector: test_connect_success_with_init_keys started.")
        mock_client_instance = MockClient.return_value
        mock_client_instance.ping.return_value = {}
        mock_client_instance.get_server_time.return_value = {'serverTime': 1234567890}

        result = self.connector_with_keys.connect()

        self.assertTrue(result)
        MockClient.assert_called_once_with(self.api_key, self.api_secret)
        mock_client_instance.ping.assert_called_once()
        mock_client_instance.get_server_time.assert_called_once()
        self.assertIsNotNone(self.connector_with_keys.client)
        print("TestBinanceConnector: test_connect_success_with_init_keys PASSED")

    def test_connect_failure_no_keys(self):
        """
        Test the connect method fails with ValueError if no API keys are provided.
        """
        print("TestBinanceConnector: test_connect_failure_no_keys started.")
        with self.assertRaises(ValueError) as context:
            self.connector.connect()
        self.assertIn("API key and secret must be provided", str(context.exception))
        print("TestBinanceConnector: test_connect_failure_no_keys PASSED")

    @patch('exchange_connectors.binance_connector.Client')
    def test_connect_failure_api_exception(self, MockClient):
        """
        Test the connect method raises ConnectionError on BinanceAPIException.
        """
        print("TestBinanceConnector: test_connect_failure_api_exception started.")
        # The BinanceAPIException constructor is (response, status_code, text)
        # We mock the response object and provide the status code and text message.
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": -1121, "msg": "API Error for test"} # Simulate Binance error format
        mock_response.text = '{"code": -1121, "msg": "API Error for test"}'

        MockClient.side_effect = BinanceAPIException(response=mock_response, status_code=400, text="API Error for test")

        with self.assertRaises(ConnectionError) as context:
            self.connector.connect(self.api_key, self.api_secret)
        self.assertIn("Failed to connect to Binance due to API error", str(context.exception))
        print("TestBinanceConnector: test_connect_failure_api_exception PASSED")

    @patch('exchange_connectors.binance_connector.Client')
    def test_connect_failure_request_exception(self, MockClient):
        """
        Test the connect method raises ConnectionError on BinanceRequestException.
        """
        print("TestBinanceConnector: test_connect_failure_request_exception started.")
        MockClient.side_effect = BinanceRequestException("Request Error")

        with self.assertRaises(ConnectionError) as context:
            self.connector.connect(self.api_key, self.api_secret)
        self.assertIn("Failed to connect to Binance due to request error", str(context.exception))
        print("TestBinanceConnector: test_connect_failure_request_exception PASSED")

    def test_disconnect(self):
        """
        Test the disconnect method.
        It should set the client to None and return True.
        """
        print("TestBinanceConnector: test_disconnect started.")
        # First, simulate a connected state
        self.connector_with_keys.client = MagicMock()

        result = self.connector_with_keys.disconnect()

        self.assertTrue(result)
        self.assertIsNone(self.connector_with_keys.client)
        print("TestBinanceConnector: test_disconnect PASSED")

    def test_get_account_balance_not_connected(self):
        """
        Test get_account_balance raises ConnectionError if client is not connected.
        """
        print("TestBinanceConnector: test_get_account_balance_not_connected started.")
        with self.assertRaises(ConnectionError) as context:
            self.connector.get_account_balance() # Using connector without established client
        self.assertIn("Client not connected", str(context.exception))
        print("TestBinanceConnector: test_get_account_balance_not_connected PASSED")

    @patch.object(Client, 'get_account')
    def test_get_account_balance_success(self, mock_get_account):
        """
        Test get_account_balance successfully retrieves and processes balances.
        """
        print("TestBinanceConnector: test_get_account_balance_success started.")
        mock_api_response = {
            "makerCommission": 15,
            "takerCommission": 15,
            "buyerCommission": 0,
            "sellerCommission": 0,
            "canTrade": True,
            "canWithdraw": True,
            "canDeposit": True,
            "updateTime": 1234567890000,
            "accountType": "SPOT",
            "balances": [
                {"asset": "BTC", "free": "0.50000000", "locked": "0.00000000"},
                {"asset": "ETH", "free": "10.12345678", "locked": "1.00000000"},
                {"asset": "USDT", "free": "10000.00000000", "locked": "0.00000000"},
                {"asset": "LTC", "free": "0.00000000", "locked": "0.00000000"} # Zero balance asset
            ],
            "permissions": ["SPOT"]
        }
        mock_get_account.return_value = mock_api_response

        # Simulate connected state
        self.connector_with_keys.client = MagicMock()
        # Assign the mock to the client instance's method
        self.connector_with_keys.client.get_account = mock_get_account

        balance = self.connector_with_keys.get_account_balance()

        mock_get_account.assert_called_once()
        self.assertIsInstance(balance, dict)
        self.assertEqual(balance["BTC"], "0.50000000")
        self.assertEqual(balance["ETH"], "10.12345678")
        self.assertEqual(balance["USDT"], "10000.00000000")
        self.assertNotIn("LTC", balance, "Zero balance assets should not be included.")
        # self.assertIn("Account balances retrieved", self.connector_with_keys.get_account_balance.__doc__) # This check is not useful
        print(f"TestBinanceConnector: get_account_balance returned: {balance}")
        print("TestBinanceConnector: test_get_account_balance_success PASSED")

    @patch.object(Client, 'get_account')
    def test_get_account_balance_api_exception(self, mock_get_account):
        """
        Test get_account_balance handles BinanceAPIException.
        """
        print("TestBinanceConnector: test_get_account_balance_api_exception started.")
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": -1001, "msg": "API Error"}
        mock_response.text = '{"code": -1001, "msg": "API Error"}'
        mock_get_account.side_effect = BinanceAPIException(response=mock_response, status_code=400, text="API Error")

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.get_account = mock_get_account

        with self.assertRaises(RuntimeError) as context:
            self.connector_with_keys.get_account_balance()
        self.assertIn("Failed to get account balance due to API error", str(context.exception))
        print("TestBinanceConnector: test_get_account_balance_api_exception PASSED")

    @patch.object(Client, 'get_account')
    def test_get_account_balance_request_exception(self, mock_get_account):
        """
        Test get_account_balance handles BinanceRequestException.
        """
        print("TestBinanceConnector: test_get_account_balance_request_exception started.")
        mock_get_account.side_effect = BinanceRequestException("Request Error")

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.get_account = mock_get_account

        with self.assertRaises(RuntimeError) as context:
            self.connector_with_keys.get_account_balance()
        self.assertIn("Failed to get account balance due to request error", str(context.exception))
        print("TestBinanceConnector: test_get_account_balance_request_exception PASSED")

    # --- Tests for get_market_data ---
    def test_get_market_data_not_connected(self):
        """
        Test get_market_data raises ConnectionError if client is not connected.
        """
        print("TestBinanceConnector: test_get_market_data_not_connected started.")
        with self.assertRaises(ConnectionError) as context:
            self.connector.get_market_data("BTCUSDT")
        self.assertIn("Client not connected", str(context.exception))
        print("TestBinanceConnector: test_get_market_data_not_connected PASSED")

    def test_get_market_data_invalid_symbol_format(self):
        """
        Test get_market_data raises ValueError for invalid symbol format.
        """
        print("TestBinanceConnector: test_get_market_data_invalid_symbol_format started.")
        self.connector_with_keys.client = MagicMock() # Simulate connected state
        with self.assertRaises(ValueError) as context:
            self.connector_with_keys.get_market_data("BTC/USDT")
        self.assertIn("Symbol format is invalid", str(context.exception))
        print("TestBinanceConnector: test_get_market_data_invalid_symbol_format PASSED")

    @patch.object(Client, 'get_symbol_ticker')
    @patch.object(Client, 'get_ticker')
    def test_get_market_data_success(self, mock_get_24hr_ticker, mock_get_symbol_ticker):
        """
        Test get_market_data successfully retrieves and processes market data.
        """
        print("TestBinanceConnector: test_get_market_data_success started.")
        symbol = "BTCUSDT"
        mock_get_symbol_ticker.return_value = {'symbol': symbol, 'price': '52000.50'}
        mock_get_24hr_ticker.return_value = {'symbol': symbol, 'volume': '1234.567', 'quoteVolume': '64000000.0'}

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.get_symbol_ticker = mock_get_symbol_ticker
        self.connector_with_keys.client.get_ticker = mock_get_24hr_ticker

        market_data = self.connector_with_keys.get_market_data(symbol)

        mock_get_symbol_ticker.assert_called_once_with(symbol=symbol)
        mock_get_24hr_ticker.assert_called_once_with(symbol=symbol)
        self.assertIsInstance(market_data, dict)
        self.assertEqual(market_data['price'], '52000.50')
        self.assertEqual(market_data['volume_24h'], '1234.567')
        print(f"TestBinanceConnector: get_market_data for {symbol} returned: {market_data}")
        print("TestBinanceConnector: test_get_market_data_success PASSED")

    @patch.object(Client, 'get_symbol_ticker')
    def test_get_market_data_api_exception_symbol_ticker(self, mock_get_symbol_ticker):
        """
        Test get_market_data handles BinanceAPIException from get_symbol_ticker.
        """
        print("TestBinanceConnector: test_get_market_data_api_exception_symbol_ticker started.")
        symbol = "BTCUSDT"
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": -1002, "msg": "Symbol ticker API Error"}
        mock_response.text = '{"code": -1002, "msg": "Symbol ticker API Error"}'
        mock_get_symbol_ticker.side_effect = BinanceAPIException(response=mock_response, status_code=400, text="Symbol ticker API Error")

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.get_symbol_ticker = mock_get_symbol_ticker

        with self.assertRaises(RuntimeError) as context:
            self.connector_with_keys.get_market_data(symbol)
        self.assertIn(f"Failed to get market data for {symbol} due to API error", str(context.exception))
        print("TestBinanceConnector: test_get_market_data_api_exception_symbol_ticker PASSED")

    @patch.object(Client, 'get_symbol_ticker') # Mock this to succeed
    @patch.object(Client, 'get_ticker') # This one will fail
    def test_get_market_data_api_exception_24hr_ticker(self, mock_get_24hr_ticker, mock_get_symbol_ticker):
        """
        Test get_market_data handles BinanceAPIException from get_ticker (for volume).
        """
        print("TestBinanceConnector: test_get_market_data_api_exception_24hr_ticker started.")
        symbol = "BTCUSDT"
        mock_get_symbol_ticker.return_value = {'symbol': symbol, 'price': '52000.50'} # This call succeeds

        mock_response = MagicMock()
        mock_response.json.return_value = {"code": -1003, "msg": "24hr ticker API Error"}
        mock_response.text = '{"code": -1003, "msg": "24hr ticker API Error"}'
        mock_get_24hr_ticker.side_effect = BinanceAPIException(response=mock_response, status_code=400, text="24hr ticker API Error")

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.get_symbol_ticker = mock_get_symbol_ticker
        self.connector_with_keys.client.get_ticker = mock_get_24hr_ticker

        with self.assertRaises(RuntimeError) as context:
            self.connector_with_keys.get_market_data(symbol)
        self.assertIn(f"Failed to get market data for {symbol} due to API error", str(context.exception))
        print("TestBinanceConnector: test_get_market_data_api_exception_24hr_ticker PASSED")

    @patch.object(Client, 'get_symbol_ticker')
    def test_get_market_data_missing_data(self, mock_get_symbol_ticker):
        """
        Test get_market_data handles missing 'price' or 'volume' in API responses.
        """
        print("TestBinanceConnector: test_get_market_data_missing_data started.")
        symbol = "BTCUSDT"
        # Simulate missing 'price'
        mock_get_symbol_ticker.return_value = {'symbol': symbol} # No 'price' key

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.get_symbol_ticker = mock_get_symbol_ticker
        # We don't even need to mock get_ticker if get_symbol_ticker already results in missing data path

        with self.assertRaises(RuntimeError) as context:
            self.connector_with_keys.get_market_data(symbol)
        self.assertIn(f"Could not retrieve complete market data for {symbol}", str(context.exception))
        print("TestBinanceConnector: test_get_market_data_missing_data (price) PASSED")

        # Simulate missing 'volume'
        mock_get_symbol_ticker.return_value = {'symbol': symbol, 'price': '52000.50'} # Price is present

        with patch.object(Client, 'get_ticker') as mock_get_24hr_ticker_volume_missing:
            mock_get_24hr_ticker_volume_missing.return_value = {'symbol': symbol} # No 'volume' key
            self.connector_with_keys.client.get_ticker = mock_get_24hr_ticker_volume_missing

            with self.assertRaises(RuntimeError) as context:
                self.connector_with_keys.get_market_data(symbol)
            self.assertIn(f"Could not retrieve complete market data for {symbol}", str(context.exception))
        print("TestBinanceConnector: test_get_market_data_missing_data (volume) PASSED")

    # --- Tests for place_order ---
    def test_place_order_not_connected(self):
        """Test place_order raises ConnectionError if client is not connected."""
        print("TestBinanceConnector: test_place_order_not_connected started.")
        with self.assertRaises(ConnectionError) as context:
            self.connector.place_order("BTCUSDT", "BUY", "LIMIT", 0.1, 50000)
        self.assertIn("Client not connected", str(context.exception))
        print("TestBinanceConnector: test_place_order_not_connected PASSED")

    def test_place_order_invalid_arguments(self):
        """Test place_order raises ValueError for various invalid arguments."""
        print("TestBinanceConnector: test_place_order_invalid_arguments started.")
        self.connector_with_keys.client = MagicMock() # Simulate connected state

        test_cases = [
            ("BTC/USDT", "BUY", "LIMIT", 0.1, 50000, "Symbol format is invalid"), # Invalid symbol
            ("BTCUSDT", "BUYING", "LIMIT", 0.1, 50000, "Order side must be 'BUY' or 'SELL'"), # Invalid side
            ("BTCUSDT", "BUY", "WRONG_TYPE", 0.1, 50000, "Order type must be 'LIMIT' or 'MARKET'"), # Invalid type
            ("BTCUSDT", "BUY", "LIMIT", -0.1, 50000, "Order amount must be a positive number"), # Invalid amount
            ("BTCUSDT", "BUY", "LIMIT", 0, 50000, "Order amount must be a positive number"), # Invalid amount
            ("BTCUSDT", "BUY", "LIMIT", 0.1, None, "Price must be a positive number for LIMIT orders"), # Missing price for limit
            ("BTCUSDT", "BUY", "LIMIT", 0.1, -50000, "Price must be a positive number for LIMIT orders"), # Invalid price
        ]

        for symbol, side, order_type, amount, price, error_msg in test_cases:
            with self.subTest(msg=f"Testing: {symbol}, {side}, {order_type}, {amount}, {price}"):
                with self.assertRaises(ValueError) as context:
                    self.connector_with_keys.place_order(symbol, side, order_type, amount, price)
                self.assertIn(error_msg, str(context.exception))
        print("TestBinanceConnector: test_place_order_invalid_arguments PASSED")

    @patch.object(Client, 'order_limit_buy')
    def test_place_order_limit_buy_success(self, mock_order_limit_buy):
        """Test successful placing of a LIMIT BUY order."""
        print("TestBinanceConnector: test_place_order_limit_buy_success started.")
        symbol, side, order_type, amount, price = "BTCUSDT", "BUY", "LIMIT", 0.01, 50000.0
        mock_response = {
            "symbol": symbol, "orderId": 12345, "clientOrderId": "testOrder", "transactTime": 1616420000000,
            "price": str(price), "origQty": str(amount), "executedQty": "0.0", "cummulativeQuoteQty": "0.0",
            "status": "NEW", "timeInForce": "GTC", "type": order_type, "side": side
        }
        mock_order_limit_buy.return_value = mock_response
        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.order_limit_buy = mock_order_limit_buy

        result = self.connector_with_keys.place_order(symbol, side, order_type, amount, price)

        mock_order_limit_buy.assert_called_once_with(symbol=symbol, quantity=amount, price=str(price))
        self.assertEqual(result['order_id'], str(mock_response['orderId']))
        self.assertEqual(result['status'], mock_response['status'])
        self.assertEqual(result['symbol'], symbol)
        self.assertEqual(result['raw_response'], mock_response)
        print("TestBinanceConnector: test_place_order_limit_buy_success PASSED")

    @patch.object(Client, 'order_limit_sell')
    def test_place_order_limit_sell_success(self, mock_order_limit_sell):
        """Test successful placing of a LIMIT SELL order."""
        print("TestBinanceConnector: test_place_order_limit_sell_success started.")
        symbol, side, order_type, amount, price = "ETHUSDT", "SELL", "LIMIT", 0.5, 3000.0
        mock_response = {"symbol": symbol, "orderId": 54321, "status": "NEW", "type": order_type, "side": side, "price": str(price), "origQty": str(amount)}
        mock_order_limit_sell.return_value = mock_response
        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.order_limit_sell = mock_order_limit_sell

        result = self.connector_with_keys.place_order(symbol, side, order_type, amount, price)
        mock_order_limit_sell.assert_called_once_with(symbol=symbol, quantity=amount, price=str(price))
        self.assertEqual(result['order_id'], str(mock_response['orderId']))
        print("TestBinanceConnector: test_place_order_limit_sell_success PASSED")

    @patch.object(Client, 'order_market_buy')
    def test_place_order_market_buy_success(self, mock_order_market_buy):
        """Test successful placing of a MARKET BUY order."""
        print("TestBinanceConnector: test_place_order_market_buy_success started.")
        symbol, side, order_type, amount = "BNBUSDT", "BUY", "MARKET", 10.0
        mock_response = {"symbol": symbol, "orderId": 67890, "status": "FILLED", "type": order_type, "side": side, "origQty": str(amount)}
        mock_order_market_buy.return_value = mock_response
        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.order_market_buy = mock_order_market_buy

        result = self.connector_with_keys.place_order(symbol, side, order_type, amount) # Price is None
        mock_order_market_buy.assert_called_once_with(symbol=symbol, quantity=amount)
        self.assertEqual(result['order_id'], str(mock_response['orderId']))
        print("TestBinanceConnector: test_place_order_market_buy_success PASSED")

    @patch.object(Client, 'order_market_sell')
    def test_place_order_market_sell_success(self, mock_order_market_sell):
        """Test successful placing of a MARKET SELL order."""
        print("TestBinanceConnector: test_place_order_market_sell_success started.")
        symbol, side, order_type, amount = "ADAUSDT", "SELL", "MARKET", 100.0
        mock_response = {"symbol": symbol, "orderId": 98765, "status": "FILLED", "type": order_type, "side": side, "origQty": str(amount)}
        mock_order_market_sell.return_value = mock_response
        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.order_market_sell = mock_order_market_sell

        result = self.connector_with_keys.place_order(symbol, side, order_type, amount)
        mock_order_market_sell.assert_called_once_with(symbol=symbol, quantity=amount)
        self.assertEqual(result['order_id'], str(mock_response['orderId']))
        print("TestBinanceConnector: test_place_order_market_sell_success PASSED")

    @patch.object(Client, 'order_limit_buy')
    def test_place_order_api_exception(self, mock_order_limit_buy):
        """Test place_order handles BinanceAPIException."""
        print("TestBinanceConnector: test_place_order_api_exception started.")
        symbol, side, order_type, amount, price = "BTCUSDT", "BUY", "LIMIT", 0.01, 10000.0 # Low price might cause error

        mock_response = MagicMock()
        mock_response.json.return_value = {"code": -2010, "msg": "Insufficient balance."} # Example error
        mock_response.text = '{"code": -2010, "msg": "Insufficient balance."}'
        mock_order_limit_buy.side_effect = BinanceAPIException(response=mock_response, status_code=400, text="Insufficient balance.")

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.order_limit_buy = mock_order_limit_buy

        with self.assertRaises(RuntimeError) as context:
            self.connector_with_keys.place_order(symbol, side, order_type, amount, price)
        self.assertIn("Failed to place order due to API error", str(context.exception))
        print("TestBinanceConnector: test_place_order_api_exception PASSED")

    @patch.object(Client, 'order_market_sell')
    def test_place_order_unexpected_response(self, mock_order_market_sell):
        """Test place_order handles unexpected (e.g., empty) response from API call."""
        print("TestBinanceConnector: test_place_order_unexpected_response started.")
        symbol, side, order_type, amount = "ADAUSDT", "SELL", "MARKET", 100.0
        mock_order_market_sell.return_value = {} # Empty response

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.order_market_sell = mock_order_market_sell

        with self.assertRaises(RuntimeError) as context:
            self.connector_with_keys.place_order(symbol, side, order_type, amount)
        self.assertIn("Order placement failed or received unexpected response", str(context.exception))
        print("TestBinanceConnector: test_place_order_unexpected_response PASSED")

    # --- Tests for cancel_order ---
    def test_cancel_order_not_connected(self):
        """Test cancel_order raises ConnectionError if client is not connected."""
        print("TestBinanceConnector: test_cancel_order_not_connected started.")
        with self.assertRaises(ConnectionError) as context:
            self.connector.cancel_order("12345", "BTCUSDT")
        self.assertIn("Client not connected", str(context.exception))
        print("TestBinanceConnector: test_cancel_order_not_connected PASSED")

    def test_cancel_order_invalid_arguments(self):
        """Test cancel_order raises ValueError for invalid arguments."""
        print("TestBinanceConnector: test_cancel_order_invalid_arguments started.")
        self.connector_with_keys.client = MagicMock() # Simulate connected

        test_cases = [
            (None, "BTCUSDT", "Order ID must be provided"),
            ("", "BTCUSDT", "Order ID must be provided"),
            ("12345", None, "Valid symbol (e.g., 'BTCUSDT') must be provided"),
            ("12345", "", "Valid symbol (e.g., 'BTCUSDT') must be provided"),
            ("12345", "BTC/USDT", "Valid symbol (e.g., 'BTCUSDT') must be provided"),
        ]
        for order_id, symbol, error_msg in test_cases:
            with self.subTest(msg=f"Testing order_id={order_id}, symbol={symbol}"):
                with self.assertRaises(ValueError) as context:
                    self.connector_with_keys.cancel_order(order_id, symbol)
                self.assertIn(error_msg, str(context.exception))
        print("TestBinanceConnector: test_cancel_order_invalid_arguments PASSED")

    @patch.object(Client, 'cancel_order')
    def test_cancel_order_success(self, mock_cancel_order_api):
        """Test successful order cancellation."""
        print("TestBinanceConnector: test_cancel_order_success started.")
        order_id, symbol = "123456", "BTCUSDT"
        mock_response = {
            "symbol": symbol, "orderId": order_id, "origClientOrderId": "myOrder1",
            "clientOrderId": "cancelMyOrder1", "status": "CANCELED", "type": "LIMIT",
            "side": "BUY", "price": "50000.00", "origQty": "0.01", "executedQty": "0.0"
        }
        mock_cancel_order_api.return_value = mock_response
        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.cancel_order = mock_cancel_order_api

        result = self.connector_with_keys.cancel_order(order_id, symbol)

        mock_cancel_order_api.assert_called_once_with(symbol=symbol, orderId=order_id)
        self.assertEqual(result['order_id'], order_id)
        self.assertEqual(result['status'], "CANCELED")
        self.assertEqual(result['symbol'], symbol)
        self.assertEqual(result['raw_response'], mock_response)
        print("TestBinanceConnector: test_cancel_order_success PASSED")

    @patch.object(Client, 'cancel_order')
    def test_cancel_order_api_exception(self, mock_cancel_order_api):
        """Test cancel_order handles BinanceAPIException (e.g., order not found)."""
        print("TestBinanceConnector: test_cancel_order_api_exception started.")
        order_id, symbol = "123457", "ETHUSDT"
        mock_response = MagicMock()
        # Error code for "Unknown order sent." or "Order does not exist."
        mock_response.json.return_value = {"code": -2011, "msg": "Unknown order sent."}
        mock_response.text = '{"code": -2011, "msg": "Unknown order sent."}'
        mock_cancel_order_api.side_effect = BinanceAPIException(response=mock_response, status_code=400, text="Unknown order sent.")

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.cancel_order = mock_cancel_order_api

        with self.assertRaises(RuntimeError) as context:
            self.connector_with_keys.cancel_order(order_id, symbol)
        self.assertIn(f"Failed to cancel order {order_id} for {symbol} due to API error", str(context.exception))
        print("TestBinanceConnector: test_cancel_order_api_exception PASSED")

    @patch.object(Client, 'cancel_order')
    def test_cancel_order_unexpected_response(self, mock_cancel_order_api):
        """Test cancel_order handles unexpected (e.g., empty) API response."""
        print("TestBinanceConnector: test_cancel_order_unexpected_response started.")
        order_id, symbol = "123458", "BNBUSDT"
        mock_cancel_order_api.return_value = {} # Empty response

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.cancel_order = mock_cancel_order_api

        with self.assertRaises(RuntimeError) as context:
            self.connector_with_keys.cancel_order(order_id, symbol)
        self.assertIn("Order cancellation failed or received unexpected response", str(context.exception))
        print("TestBinanceConnector: test_cancel_order_unexpected_response PASSED")

    # --- Tests for get_order_status ---
    def test_get_order_status_not_connected(self):
        """Test get_order_status raises ConnectionError if client is not connected."""
        print("TestBinanceConnector: test_get_order_status_not_connected started.")
        with self.assertRaises(ConnectionError) as context:
            self.connector.get_order_status("12345", "BTCUSDT")
        self.assertIn("Client not connected", str(context.exception))
        print("TestBinanceConnector: test_get_order_status_not_connected PASSED")

    def test_get_order_status_invalid_arguments(self):
        """Test get_order_status raises ValueError for invalid arguments."""
        print("TestBinanceConnector: test_get_order_status_invalid_arguments started.")
        self.connector_with_keys.client = MagicMock() # Simulate connected

        test_cases = [
            (None, "BTCUSDT", "Order ID must be provided"),
            ("", "BTCUSDT", "Order ID must be provided"),
            ("12345", None, "Valid symbol (e.g., 'BTCUSDT') must be provided"),
            ("12345", "", "Valid symbol (e.g., 'BTCUSDT') must be provided"),
            ("12345", "BTC/USDT", "Valid symbol (e.g., 'BTCUSDT') must be provided"),
        ]
        for order_id, symbol, error_msg in test_cases:
            with self.subTest(msg=f"Testing order_id={order_id}, symbol={symbol}"):
                with self.assertRaises(ValueError) as context:
                    self.connector_with_keys.get_order_status(order_id, symbol)
                self.assertIn(error_msg, str(context.exception))
        print("TestBinanceConnector: test_get_order_status_invalid_arguments PASSED")

    @patch.object(Client, 'get_order')
    def test_get_order_status_success(self, mock_get_order_api):
        """Test successful retrieval of order status."""
        print("TestBinanceConnector: test_get_order_status_success started.")
        order_id, symbol = "123456", "BTCUSDT"
        mock_response = {
            "symbol": symbol, "orderId": order_id, "orderListId": -1, "clientOrderId": "myOrder1",
            "price": "50000.00", "origQty": "0.01", "executedQty": "0.01",
            "cummulativeQuoteQty": "500.00", "status": "FILLED", "timeInForce": "GTC",
            "type": "LIMIT", "side": "BUY", "stopPrice": "0.0", "icebergQty": "0.0",
            "time": 1616420000000, "updateTime": 1616420000000, "isWorking": True,
            "origQuoteOrderQty": "0.000000"
        }
        mock_get_order_api.return_value = mock_response
        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.get_order = mock_get_order_api

        result = self.connector_with_keys.get_order_status(order_id, symbol)

        mock_get_order_api.assert_called_once_with(symbol=symbol, orderId=order_id)
        self.assertEqual(result['order_id'], order_id)
        self.assertEqual(result['status'], "FILLED")
        self.assertEqual(result['symbol'], symbol)
        self.assertEqual(result['executed_qty'], "0.01")
        self.assertEqual(result['raw_response'], mock_response)
        print("TestBinanceConnector: test_get_order_status_success PASSED")

    @patch.object(Client, 'get_order')
    def test_get_order_status_api_exception(self, mock_get_order_api):
        """Test get_order_status handles BinanceAPIException (e.g., order not found)."""
        print("TestBinanceConnector: test_get_order_status_api_exception started.")
        order_id, symbol = "123457", "ETHUSDT"
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": -2013, "msg": "Order does not exist."}
        mock_response.text = '{"code": -2013, "msg": "Order does not exist."}'
        mock_get_order_api.side_effect = BinanceAPIException(response=mock_response, status_code=400, text="Order does not exist.")

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.get_order = mock_get_order_api

        with self.assertRaises(RuntimeError) as context:
            self.connector_with_keys.get_order_status(order_id, symbol)
        self.assertIn(f"Failed to get status for order {order_id} ({symbol}) due to API error", str(context.exception))
        print("TestBinanceConnector: test_get_order_status_api_exception PASSED")

    @patch.object(Client, 'get_order')
    def test_get_order_status_unexpected_response(self, mock_get_order_api):
        """Test get_order_status handles unexpected (e.g., empty) API response."""
        print("TestBinanceConnector: test_get_order_status_unexpected_response started.")
        order_id, symbol = "123458", "BNBUSDT"
        mock_get_order_api.return_value = {} # Empty response

        self.connector_with_keys.client = MagicMock()
        self.connector_with_keys.client.get_order = mock_get_order_api

        with self.assertRaises(RuntimeError) as context:
            self.connector_with_keys.get_order_status(order_id, symbol)
        self.assertIn("Failed to get order status or received unexpected response", str(context.exception))
        print("TestBinanceConnector: test_get_order_status_unexpected_response PASSED")


if __name__ == '__main__':
    print("Running tests for BinanceConnector...")
    # unittest.main() # This will try to run tests from the command line args
    # To run specifically this test suite when the file is executed directly:
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBinanceConnector))
    runner = unittest.TextTestRunner()
    runner.run(suite)
    print("Finished running tests for BinanceConnector.")
