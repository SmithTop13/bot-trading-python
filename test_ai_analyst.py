# test_ai_analyst.py
import unittest
from unittest.mock import patch, MagicMock
import os

# Set a dummy API key for tests BEFORE importing ai_analyst
os.environ["GOOGLE_GENAI_API_KEY"] = "DUMMY_KEY_FOR_TESTING"

# It's important to import the module under test AFTER potentially
# modifying environment variables it might use at import time for configuration.
import ai_analyst # noqa: E402 module level import not at top of file


class TestAiAnalyst(unittest.TestCase):

    def setUp(self):
        # Ensure IS_GEMINI_CONFIGURED is True for most tests by default,
        # simulating successful genai.configure()
        # We can override this patch for specific tests that check unconfigured behavior.
        self.configure_patch = patch('ai_analyst.IS_GEMINI_CONFIGURED', True)
        self.mock_is_configured = self.configure_patch.start()

        # Mock the GenerativeModel class itself
        self.mock_generative_model_patch = patch('ai_analyst.genai.GenerativeModel')
        self.MockGenerativeModel = self.mock_generative_model_patch.start()

        # Mock the instance of GenerativeModel and its generate_content method
        self.mock_model_instance = MagicMock()
        self.MockGenerativeModel.return_value = self.mock_model_instance


    def tearDown(self):
        self.configure_patch.stop()
        self.mock_generative_model_patch.stop()
        # Clean up environment variable if it causes issues for other tests (though usually not needed for dummy ones)
        # if "GOOGLE_GENAI_API_KEY" in os.environ:
        #     del os.environ["GOOGLE_GENAI_API_KEY"]

    def test_analyze_sentiment_success(self):
        mock_response = MagicMock()
        mock_response.text = "Sentiment: positive\nReasoning: The news is very good for crypto."
        mock_response.candidates = [MagicMock()] # Ensure candidates list is not empty
        mock_response.prompt_feedback = None
        self.mock_model_instance.generate_content.return_value = mock_response

        result = ai_analyst.analyze_sentiment_gemini("Great news for Bitcoin!")
        self.assertIsNotNone(result)
        self.assertEqual(result['sentiment'], "positive")
        self.assertEqual(result['reasoning'], "The news is very good for crypto.")
        self.assertIsNone(result['error'])
        self.mock_model_instance.generate_content.assert_called_once()

    def test_analyze_sentiment_parsing_various_formats(self):
        test_cases = [
            ("Sentiment: negative\nReasoning: Bad news.", "negative", "Bad news."),
            ("Sentiment: neutral \n Reasoning: It's okay.", "neutral", "It's okay."),
            ("Sentiment: PoSiTiVe\nReAsOnInG: Mixed case works.", "positive", "Mixed case works."),
            ("Sentiment: positive\nReasoning: This is a multi-line\nreasoning that should be captured.", "positive", "This is a multi-line\nreasoning that should be captured."),
            ("Sentiment: positive\nReasoning:   Leading and trailing spaces should be stripped.  ", "positive", "Leading and trailing spaces should be stripped."),
        ]
        for raw_text, expected_sentiment, expected_reasoning in test_cases:
            with self.subTest(raw_text=raw_text):
                mock_response = MagicMock()
                mock_response.text = raw_text
                mock_response.candidates = [MagicMock()]
                mock_response.prompt_feedback = None
                self.mock_model_instance.generate_content.return_value = mock_response

                result = ai_analyst.analyze_sentiment_gemini("Some news text")
                self.assertEqual(result['sentiment'], expected_sentiment)
                self.assertEqual(result['reasoning'], expected_reasoning)
                self.assertIsNone(result['error'])

    def test_analyze_sentiment_parsing_failure(self):
        mock_response = MagicMock()
        mock_response.text = "This is not the expected format."
        mock_response.candidates = [MagicMock()]
        mock_response.prompt_feedback = None
        self.mock_model_instance.generate_content.return_value = mock_response

        result = ai_analyst.analyze_sentiment_gemini("More news.")
        self.assertEqual(result['sentiment'], "neutral") # Default on parse fail
        self.assertTrue("Could not parse" in result['reasoning'])
        self.assertIsNone(result['error'])

    def test_analyze_sentiment_only_sentiment_parsed(self):
        mock_response = MagicMock()
        mock_response.text = "Sentiment: negative" # Reasoning missing
        mock_response.candidates = [MagicMock()]
        mock_response.prompt_feedback = None
        self.mock_model_instance.generate_content.return_value = mock_response

        result = ai_analyst.analyze_sentiment_gemini("News text")
        self.assertEqual(result['sentiment'], "negative")
        self.assertTrue("AI classified sentiment as negative but no specific reasoning was parsed." in result['reasoning'])
        self.assertIsNone(result['error'])


    def test_analyze_sentiment_api_error(self):
        self.mock_model_instance.generate_content.side_effect = Exception("API communication failed")

        result = ai_analyst.analyze_sentiment_gemini("Some news.")
        self.assertEqual(result['sentiment'], "error")
        self.assertTrue("API communication failed" in result['reasoning'])
        self.assertIsNotNone(result['error'])

    def test_analyze_sentiment_no_candidates_safety_block(self):
        mock_response = MagicMock()
        mock_response.candidates = [] # No candidates
        mock_response.prompt_feedback = MagicMock()
        mock_response.prompt_feedback.block_reason = "SAFETY"
        self.mock_model_instance.generate_content.return_value = mock_response

        result = ai_analyst.analyze_sentiment_gemini("Potentially problematic content.")
        self.assertEqual(result['sentiment'], "error")
        self.assertEqual(result['reasoning'], "Content blocked: SAFETY")
        self.assertIsNotNone(result['error'])

    def test_analyze_sentiment_no_candidates_no_block_reason(self):
        mock_response = MagicMock()
        mock_response.candidates = [] # No candidates
        mock_response.prompt_feedback = None # No block reason
        self.mock_model_instance.generate_content.return_value = mock_response

        result = ai_analyst.analyze_sentiment_gemini("Some other content.")
        self.assertEqual(result['sentiment'], "error")
        self.assertEqual(result['reasoning'], "No valid response from AI.")
        self.assertIsNotNone(result['error'])


    def test_summarize_text_success(self):
        mock_response = MagicMock()
        mock_response.text = "This is a concise summary."
        mock_response.candidates = [MagicMock()]
        mock_response.prompt_feedback = None
        self.mock_model_instance.generate_content.return_value = mock_response

        result = ai_analyst.summarize_text_gemini("A long piece of text to summarize.")
        self.assertIsNotNone(result)
        self.assertEqual(result['summary'], "This is a concise summary.")
        self.assertIsNone(result['error'])
        self.mock_model_instance.generate_content.assert_called_once()

    def test_summarize_text_api_error(self):
        self.mock_model_instance.generate_content.side_effect = Exception("Summarization API error")

        result = ai_analyst.summarize_text_gemini("Text.")
        self.assertIsNone(result['summary'])
        self.assertTrue("Summarization API error" in result['error'])

    def test_summarize_text_no_candidates_safety_block(self):
        mock_response = MagicMock()
        mock_response.candidates = []
        mock_response.prompt_feedback = MagicMock()
        mock_response.prompt_feedback.block_reason = "HARM_CATEGORY_HARASSMENT"
        self.mock_model_instance.generate_content.return_value = mock_response

        result = ai_analyst.summarize_text_gemini("Problematic text for summary.")
        self.assertIsNone(result['summary'])
        self.assertEqual(result['error'], "Content blocked: HARM_CATEGORY_HARASSMENT")

    def test_api_not_configured_sentiment(self): # Removed decorator and param
        with patch('ai_analyst.IS_GEMINI_CONFIGURED', False):
            # We don't even need to mock genai.GenerativeModel if IS_GEMINI_CONFIGURED is False
            result = ai_analyst.analyze_sentiment_gemini("Some text.")
            self.assertEqual(result['sentiment'], "error")
            self.assertEqual(result['reasoning'], "API not configured.")

    def test_api_not_configured_summary(self): # Removed decorator and param
        with patch('ai_analyst.IS_GEMINI_CONFIGURED', False):
            result = ai_analyst.summarize_text_gemini("Some text.")
            self.assertIsNone(result['summary'])
            self.assertEqual(result['error'], "API not configured.")

    def test_empty_input_sentiment(self):
        result = ai_analyst.analyze_sentiment_gemini("")
        self.assertEqual(result['sentiment'], "error")
        self.assertEqual(result['reasoning'], "No content provided.")

    def test_empty_input_summary(self):
        result = ai_analyst.summarize_text_gemini("")
        self.assertIsNone(result['summary'])
        self.assertEqual(result['error'], "No content provided.")

if __name__ == '__main__':
    unittest.main()
