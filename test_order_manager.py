# test_order_manager.py
import unittest
from unittest.mock import patch, MagicMock
import os
import json
import time
import base64 # Added import
import requests # Added import

# Set dummy API keys for tests BEFORE importing order_manager
os.environ["GEMINI_API_KEY"] = "TEST_GEMINI_API_KEY"
os.environ["GEMINI_API_SECRET"] = "TEST_GEMINI_API_SECRET"

# Import the module under test after setting env vars
import order_manager # noqa: E402

class TestOrderManager(unittest.TestCase):

    def setUp(self):
        # Patch requests.post for all tests in this class
        self.requests_post_patch = patch('order_manager.requests.post')
        self.mock_post = self.requests_post_patch.start()

        # Reset any cached API_KEY/API_SECRET in the module if they were loaded at import
        # This ensures that if a test modifies them (e.g. for testing missing keys),
        # it doesn't affect other tests.
        order_manager.API_KEY = os.getenv("GEMINI_API_KEY")
        order_manager.API_SECRET = os.getenv("GEMINI_API_SECRET")


    def tearDown(self):
        self.requests_post_patch.stop()

    def _mock_response(self, status_code=200, json_data=None, text_data=None, raise_for_status_error=None):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        if json_data:
            mock_resp.json.return_value = json_data
        if text_data:
            mock_resp.text = text_data

        if raise_for_status_error:
            mock_resp.raise_for_status.side_effect = raise_for_status_error
        return mock_resp

    def test_sign_payload_logic(self):
        # Test the internal signing logic (though it's also implicitly tested by successful calls)
        # This is more of a sanity check for the signing components
        payload_dict = {"request": "/v1/test", "nonce": 1234567890000, "message": "hello"}
        payload_json_str = json.dumps(payload_dict)
        dummy_secret = "mysecret"

        signature, b64_payload = order_manager._sign_payload(payload_json_str, dummy_secret)

        self.assertIsNotNone(signature)
        self.assertTrue(len(signature) == 96) # SHA384 hex digest length

        # Check b64 encoding
        import base64
        expected_b64 = base64.b64encode(payload_json_str.encode('utf-8')).decode('utf-8')
        self.assertEqual(b64_payload, expected_b64)

    @patch('order_manager._get_nonce', return_value=1234567890000) # Mock nonce for consistent signature
    def test_send_gemini_private_request_headers(self, mock_nonce):
        self.mock_post.return_value = self._mock_response(json_data={"result": "success"})

        endpoint = "/v1/test_endpoint"
        payload = {"param1": "value1"}

        order_manager._send_gemini_private_request(endpoint, payload.copy()) # Use .copy() as payload is modified

        self.mock_post.assert_called_once()
        call_args = self.mock_post.call_args
        called_url = call_args[0][0]
        called_headers = call_args[1]['headers']

        self.assertEqual(called_url, order_manager.GEMINI_SANDBOX_API_URL + endpoint)
        self.assertEqual(called_headers['X-GEMINI-APIKEY'], "TEST_GEMINI_API_KEY")
        self.assertIn('X-GEMINI-PAYLOAD', called_headers)
        self.assertIn('X-GEMINI-SIGNATURE', called_headers)
        self.assertEqual(called_headers['Content-Type'], 'text/plain')
        self.assertEqual(called_headers['Cache-Control'], 'no-cache')

        # Verify payload content in header
        # The order of keys matters for the signature and b64 encoding.
        # 'request' and 'nonce' are added to the payload dict in _send_gemini_private_request.
        expected_payload_dict_for_header = {
            "param1": "value1", # Original key from payload
            "request": endpoint,
            "nonce": 1234567890000
        }
        # To ensure consistent ordering for tests, especially if json.dumps doesn't sort by default
        # in the version of Python or if the dict internal order changes.
        # We can dump with sort_keys=True for the *test's* comparison string,
        # if the actual implementation also effectively results in a consistent order for the *same input dict*.
        # However, Gemini's actual requirement is just a valid JSON string of the payload object.
        # The most reliable way to test this is to ensure the dict passed to json.dumps in the SUT
        # has its items in the order you expect for the test comparison.
        # The current error shows 'param1' came first in the actual b64 string.

        expected_payload_json_for_header = json.dumps(expected_payload_dict_for_header) # No sort_keys here to match SUT
        expected_b64 = base64.b64encode(expected_payload_json_for_header.encode('utf-8')).decode('utf-8')
        self.assertEqual(called_headers['X-GEMINI-PAYLOAD'], expected_b64)


    def test_place_limit_order_success(self):
        mock_order_response = {
            "order_id": "12345", "client_order_id": "bot-btcusd-test1", "symbol": "btcusd",
            "price": "30000.00", "avg_execution_price": "0.00", "side": "buy",
            "type": "exchange limit", "timestamp": "1678886400000", "timestampms": 1678886400000,
            "is_live": True, "is_cancelled": False, "is_hidden": False,
            "original_amount": "0.001", "remaining_amount": "0.001", "executed_amount": "0"
        }
        self.mock_post.return_value = self._mock_response(json_data=mock_order_response)

        result = order_manager.place_limit_order("BTCUSD", "0.001", "30000.00", "buy")
        self.assertEqual(result, mock_order_response)

        # Check that the payload sent to Gemini was correct
        called_payload_b64 = self.mock_post.call_args[1]['headers']['X-GEMINI-PAYLOAD']
        called_payload_json = base64.b64decode(called_payload_b64).decode('utf-8')
        called_payload_dict = json.loads(called_payload_json)

        self.assertEqual(called_payload_dict['symbol'], "btcusd") # Lowercase
        self.assertEqual(called_payload_dict['amount'], "0.001")
        self.assertEqual(called_payload_dict['price'], "30000.00")
        self.assertEqual(called_payload_dict['side'], "buy")
        self.assertEqual(called_payload_dict['type'], "exchange limit")
        self.assertTrue(called_payload_dict['client_order_id'].startswith("bot-btcusd-"))

    def test_cancel_order_success(self):
        mock_cancel_response = {"order_id": "12345", "is_cancelled": True}
        self.mock_post.return_value = self._mock_response(json_data=mock_cancel_response)
        result = order_manager.cancel_order(12345)
        self.assertEqual(result, mock_cancel_response)

        called_payload_dict = json.loads(base64.b64decode(self.mock_post.call_args[1]['headers']['X-GEMINI-PAYLOAD']))
        self.assertEqual(called_payload_dict['order_id'], 12345)

    def test_get_order_status_success(self):
        mock_status_response = {"order_id": "12345", "is_live": False, "executed_amount": "0.001"}
        self.mock_post.return_value = self._mock_response(json_data=mock_status_response)
        result = order_manager.get_order_status(12345)
        self.assertEqual(result, mock_status_response)

    def test_get_active_orders_success(self):
        mock_active_orders_response = [{"order_id": "123"}, {"order_id": "456"}]
        self.mock_post.return_value = self._mock_response(json_data=mock_active_orders_response)
        result = order_manager.get_active_orders()
        self.assertEqual(result, mock_active_orders_response)

    def test_get_trade_history_success(self):
        mock_trades_response = [{"tid": 789, "price": "30000", "amount": "0.001"}]
        self.mock_post.return_value = self._mock_response(json_data=mock_trades_response)
        result = order_manager.get_trade_history("BTCUSD", limit_trades=1)
        self.assertEqual(result, mock_trades_response)

        called_payload_dict = json.loads(base64.b64decode(self.mock_post.call_args[1]['headers']['X-GEMINI-PAYLOAD']))
        self.assertEqual(called_payload_dict['symbol'], "btcusd")
        self.assertEqual(called_payload_dict['limit_trades'], 1)


    def test_api_error_response_parsing(self):
        gemini_error = {"result": "error", "reason": "InsufficientFunds", "message": "You do not have enough..."}
        self.mock_post.return_value = self._mock_response(status_code=400, json_data=gemini_error)

        result = order_manager.place_limit_order("BTCUSD", "100", "30000", "buy")
        self.assertEqual(result, gemini_error)

    def test_http_error_no_json_response(self):
        # Create a mock response specifically for this test
        mock_resp_http_error = MagicMock()
        mock_resp_http_error.status_code = 500
        mock_resp_http_error.text = "Internal Server Error Text"
        mock_resp_http_error.raise_for_status.side_effect = requests.exceptions.HTTPError("Server Error")
        # Crucially, make .json() call raise an error for this specific mock
        mock_resp_http_error.json.side_effect = json.JSONDecodeError("Simulated JSON decode error", "doc", 0)

        self.mock_post.return_value = mock_resp_http_error

        result = order_manager.place_limit_order("BTCUSD", "0.001", "30000", "buy")
        self.assertEqual(result['result'], "error")
        self.assertEqual(result['reason'], "HTTPError")
        self.assertTrue("Server Error" in result['message'])

    def test_request_exception(self):
        self.mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")
        result = order_manager.place_limit_order("BTCUSD", "0.001", "30000", "buy")
        self.assertEqual(result['result'], "error")
        self.assertEqual(result['reason'], "RequestException")
        self.assertTrue("Connection timed out" in result['message'])

    def test_no_api_keys_configured(self):
        order_manager.API_KEY = None # Temporarily unset
        result = order_manager.place_limit_order("BTCUSD", "0.001", "30000", "buy")
        self.assertEqual(result['result'], "error")
        self.assertEqual(result['reason'], "ConfigurationError")
        self.assertIn("API key or secret not configured", result['message'])
        order_manager.API_KEY = os.getenv("GEMINI_API_KEY") # Restore

    def test_no_api_secret_configured(self):
        order_manager.API_SECRET = None # Temporarily unset
        result = order_manager.place_limit_order("BTCUSD", "0.001", "30000", "buy")
        self.assertEqual(result['result'], "error")
        self.assertEqual(result['reason'], "ConfigurationError")
        self.assertIn("API key or secret not configured", result['message'])
        order_manager.API_SECRET = os.getenv("GEMINI_API_SECRET") # Restore

if __name__ == '__main__':
    unittest.main()
