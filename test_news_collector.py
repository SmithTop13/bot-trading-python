# test_news_collector.py
import unittest
from unittest.mock import patch, MagicMock
import requests # Import requests for exceptions
from news_collector import fetch_crypto_news, clean_text

class TestNewsCollector(unittest.TestCase):

    def test_clean_text(self):
        self.assertEqual(clean_text("<p>Hello <b>World</b> &amp;  Test!</p>  "), "Hello World Test!")
        self.assertEqual(clean_text("  Extra   spaces and\nnewlines\t. "), "Extra spaces and newlines .")
        self.assertEqual(clean_text("No HTML, just clean text."), "No HTML, just clean text.")
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text("Text with numbers 123 and punctuation!?-.,"), "Text with numbers 123 and punctuation!?-.,")
        self.assertEqual(clean_text("Special chars like @#$%^&*()_+=[]{};:'\"\\|<>`~"), "Special chars like") # Most are removed, .strip() handles trailing space

    @patch('news_collector.requests.get')
    def test_fetch_crypto_news_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "totalResults": 1,
            "articles": [
                {
                    "source": {"id": "test-source", "name": "Test Source"},
                    "author": "Test Author",
                    "title": "Test Title <p>html</p>",
                    "description": "Test Description &amp; entities",
                    "content": "Test Content with more details.",
                    "url": "http://example.com/test",
                    "urlToImage": "http://example.com/image.jpg",
                    "publishedAt": "2023-01-01T12:00:00Z"
                }
            ]
        }
        mock_get.return_value = mock_response

        articles = fetch_crypto_news("fake_api_key", "Bitcoin")
        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article['headline'], "Test Title html")
        self.assertEqual(article['body'], "Test Content with more details.") # Prefers content
        self.assertEqual(article['timestamp'], "2023-01-01T12:00:00Z")
        self.assertEqual(article['source'], "Test Source")
        self.assertEqual(article['url'], "http://example.com/test")
        mock_get.assert_called_once()

    @patch('news_collector.requests.get')
    def test_fetch_crypto_news_success_uses_description_if_content_null(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "totalResults": 1,
            "articles": [
                {
                    "source": {"id": "test-source", "name": "Test Source"},
                    "author": "Test Author",
                    "title": "Test Title",
                    "description": "Test Description as body", # This should be used
                    "content": None, # Content is None
                    "url": "http://example.com/test",
                    "publishedAt": "2023-01-01T12:00:00Z"
                }
            ]
        }
        mock_get.return_value = mock_response

        articles = fetch_crypto_news("fake_api_key", "Ethereum")
        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article['body'], "Test Description as body")
        mock_get.assert_called_once()


    @patch('news_collector.requests.get')
    def test_fetch_crypto_news_api_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200 # API can return 200 but status: error
        mock_response.json.return_value = {
            "status": "error",
            "code": "apiKeyInvalid",
            "message": "Your API key is invalid or incorrect."
        }
        mock_get.return_value = mock_response

        articles = fetch_crypto_news("fake_api_key", "Crypto")
        self.assertEqual(len(articles), 0)
        mock_get.assert_called_once()

    @patch('news_collector.requests.get')
    def test_fetch_crypto_news_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Server Error")
        mock_get.return_value = mock_response

        articles = fetch_crypto_news("fake_api_key", "Blockchain")
        self.assertEqual(len(articles), 0)
        mock_get.assert_called_once()

    @patch('news_collector.requests.get')
    def test_fetch_crypto_news_request_exception(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Connection Error")

        articles = fetch_crypto_news("fake_api_key", "NFT")
        self.assertEqual(len(articles), 0)
        mock_get.assert_called_once()

    def test_fetch_crypto_news_no_api_key(self):
        articles = fetch_crypto_news("", "Bitcoin") # Empty API key
        self.assertEqual(len(articles), 0)

    @patch('news_collector.requests.get')
    def test_fetch_crypto_news_empty_articles_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "totalResults": 0,
            "articles": [] # No articles returned
        }
        mock_get.return_value = mock_response
        articles = fetch_crypto_news("fake_api_key", "ObscureCoin")
        self.assertEqual(len(articles), 0)
        mock_get.assert_called_once()

    @patch('news_collector.requests.get')
    def test_fetch_crypto_news_missing_essential_fields(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "totalResults": 1,
            "articles": [
                { # Missing title
                    "source": {"id": "test-source", "name": "Test Source"},
                    "description": "Test Description",
                    "publishedAt": "2023-01-01T12:00:00Z"
                }
            ]
        }
        mock_get.return_value = mock_response
        articles = fetch_crypto_news("fake_api_key", "IncompleteData")
        self.assertEqual(len(articles), 0) # Article should be skipped
        mock_get.assert_called_once()

if __name__ == '__main__':
    unittest.main()
