# ai_analyst.py
# This module will integrate with the Google Generative AI model (Gemini)
# for sentiment analysis and summarization.

import os
import google.generativeai as genai
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)

# It's recommended to load the API key from environment variables.
# The user should set GOOGLE_GENAI_API_KEY.
# genai.configure(api_key=os.getenv("GOOGLE_GENAI_API_KEY")) # Configure at module level or pass key to functions

DEFAULT_SENTIMENT_MODEL = "gemini-1.5-flash-latest" # Or "gemini-pro" / "gemini-1.0-pro"
DEFAULT_SUMMARIZATION_MODEL = "gemini-1.5-flash-latest"

# Generation configuration for stricter output control if needed
GENERATION_CONFIG = {
    "temperature": 0.2, # Lower temperature for more deterministic output
    "top_p": 0.8,
    "top_k": 40,
    # "max_output_tokens": 150, # Limit output size for sentiment
}

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

def configure_gemini_api():
    """Configures the Gemini API with the API key from environment variables."""
    api_key = os.getenv("GOOGLE_GENAI_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_GENAI_API_KEY not found in environment. AI Analyst will not function.")
        return False
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        logger.error(f"Error configuring Gemini API: {e}")
        return False

# Call configuration when module is loaded, or ensure it's called before use in main.py
IS_GEMINI_CONFIGURED = configure_gemini_api()


def analyze_sentiment_gemini(text_content: str, target_cryptos: list[str] = None) -> dict | None:
    """
    Analyzes the sentiment of a given text regarding its impact on cryptocurrency markets
    using the Gemini model.

    Args:
        text_content: The news article content (headline + body) to analyze.
        target_cryptos: Optional list of specific cryptocurrencies (e.g., ["Bitcoin", "Ethereum"])
                        to focus the sentiment analysis on.

    Returns:
        A dictionary with 'sentiment' ("positive", "negative", "neutral"),
        'reasoning' (brief explanation), and 'error' (if any).
        Returns None if the API is not configured or a critical error occurs.
    """
    if not IS_GEMINI_CONFIGURED:
        logger.error("Gemini API not configured. Cannot analyze sentiment.")
        return {"sentiment": "error", "reasoning": "API not configured.", "error": "API not configured."}

    if not text_content or not text_content.strip():
        logger.warning("No text content provided for sentiment analysis.")
        return {"sentiment": "error", "reasoning": "No content provided.", "error": "No content provided."}

    model = genai.GenerativeModel(
        DEFAULT_SENTIMENT_MODEL,
        generation_config=GENERATION_CONFIG,
        safety_settings=SAFETY_SETTINGS
    )

    crypto_focus = ""
    if target_cryptos:
        crypto_focus = f" Focus particularly on its impact on {', '.join(target_cryptos)}."

    prompt = f"""Analyze the following news content for its sentiment regarding the cryptocurrency market.{crypto_focus}
Classify the sentiment as "positive", "negative", or "neutral".
Provide a brief, one to two-sentence explanation for your sentiment classification.

News Content:
"{text_content}"

Output format should be:
Sentiment: [positive/negative/neutral]
Reasoning: [Your brief explanation]
"""

    try:
        logger.debug(f"Sending prompt to Gemini for sentiment analysis: {prompt[:200]}...") # Log snippet
        response = model.generate_content(prompt)

        if not response.candidates:
            logger.warning("Gemini sentiment analysis returned no candidates. Possible safety block or empty response.")
            # Check for safety ratings if available and more detailed logging
            try:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason
                    logger.warning(f"Prompt blocked for sentiment analysis. Reason: {reason}")
                    return {"sentiment": "error", "reasoning": f"Content blocked: {reason}", "error": f"Content blocked: {reason}"}
            except Exception as e:
                logger.debug(f"Could not retrieve detailed block reason: {e}")
            return {"sentiment": "error", "reasoning": "No valid response from AI.", "error": "No valid response from AI."}


        analysis_text = response.text.strip()
        logger.debug(f"Gemini sentiment analysis raw response: {analysis_text}")

        sentiment = "neutral" # Default
        reasoning = "Could not parse AI response."

        # Attempt to parse the structured response
        sentiment_match = re.search(r"Sentiment:\s*(positive|negative|neutral)", analysis_text, re.IGNORECASE)
        reasoning_match = re.search(r"Reasoning:\s*(.*)", analysis_text, re.IGNORECASE | re.DOTALL)

        if sentiment_match:
            sentiment = sentiment_match.group(1).lower()
        else:
            logger.warning(f"Could not parse sentiment from: {analysis_text}")


        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()
        else:
            logger.warning(f"Could not parse reasoning from: {analysis_text}")
            # If reasoning is missing, but sentiment found, provide a generic reasoning
            if sentiment_match:
                 reasoning = f"AI classified sentiment as {sentiment} but no specific reasoning was parsed."


        return {"sentiment": sentiment, "reasoning": reasoning, "error": None}

    except Exception as e:
        logger.error(f"Error during Gemini sentiment analysis: {e}")
        # Check for specific GenAI exceptions if desired, e.g. google.api_core.exceptions.GoogleAPIError
        return {"sentiment": "error", "reasoning": f"AI API Error: {str(e)}", "error": str(e)}


def summarize_text_gemini(text_content: str, max_length: int = 100) -> dict | None:
    """
    Summarizes a given text using the Gemini model.

    Args:
        text_content: The text to summarize.
        max_length: Approximate maximum length of the summary in words (actual output may vary).

    Returns:
        A dictionary with 'summary' and 'error' (if any).
        Returns None if the API is not configured or a critical error occurs.
    """
    if not IS_GEMINI_CONFIGURED:
        logger.error("Gemini API not configured. Cannot summarize text.")
        return {"summary": None, "error": "API not configured."}

    if not text_content or not text_content.strip():
        logger.warning("No text content provided for summarization.")
        return {"summary": None, "error": "No content provided."}

    model = genai.GenerativeModel(
        DEFAULT_SUMMARIZATION_MODEL,
        # generation_config can be adjusted for summarization
        safety_settings=SAFETY_SETTINGS
    )
    prompt = f"""Summarize the following news content concisely, aiming for around {max_length} words.
Focus on the key information relevant to cryptocurrency markets if applicable.

News Content:
"{text_content}"

Summary:
"""
    try:
        logger.debug(f"Sending prompt to Gemini for summarization: {prompt[:200]}...")
        response = model.generate_content(prompt)

        if not response.candidates:
            logger.warning("Gemini summarization returned no candidates. Possible safety block.")
            try:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason
                    logger.warning(f"Prompt blocked for summarization. Reason: {reason}")
                    return {"summary": None, "error": f"Content blocked: {reason}"}
            except Exception: # Nosec B110
                pass # Already logged the main issue
            return {"summary": None, "error": "No valid response from AI for summary."}

        summary = response.text.strip()
        logger.debug(f"Gemini summarization raw response: {summary}")
        return {"summary": summary, "error": None}

    except Exception as e:
        logger.error(f"Error during Gemini summarization: {e}")
        return {"summary": None, "error": str(e)}

# Example of how to use (for testing, assuming GOOGLE_GENAI_API_KEY is set)
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG) # Enable debug logging for this test

    if not IS_GEMINI_CONFIGURED:
        print("Please set the GOOGLE_GENAI_API_KEY environment variable to test ai_analyst.py.")
    else:
        print("Gemini API is configured.")
        sample_news_positive = {
            "headline": "Bitcoin Skyrockets Past $100,000 Mark After Major Institutional Investment",
            "body": "Bitcoin (BTC) has seen an unprecedented surge today, breaking the psychological $100,000 barrier. The rally is largely attributed to a multi-billion dollar investment by a leading tech conglomerate, signaling growing mainstream adoption. Market analysts are optimistic this could trigger a wider bull run across the crypto sphere."
        }
        full_text_positive = f"{sample_news_positive['headline']}\n\n{sample_news_positive['body']}"

        sample_news_negative = {
            "headline": "Major Exchange Halts Withdrawals Amidst Security Breach Fears",
            "body": "Popular cryptocurrency exchange 'CoinSecure' has abruptly halted all user withdrawals and trading activities. While the company cites 'unscheduled maintenance,' rumors are circulating about a significant security breach and potential loss of funds. This has sent ripples of fear across the market, with Bitcoin and Ethereum prices tumbling."
        }
        full_text_negative = f"{sample_news_negative['headline']}\n\n{sample_news_negative['body']}"

        sample_news_neutral = {
            "headline": "Blockchain Developer Conference Focuses on Scalability Solutions",
            "body": "The annual 'Future of Blockchain' conference concluded today, with a primary focus on layer-2 scalability solutions and cross-chain interoperability. Developers showcased various projects aimed at improving transaction speeds and reducing costs. While no immediate market-moving announcements were made, the long-term implications for the ecosystem are considered significant by attendees."
        }
        full_text_neutral = f"{sample_news_neutral['headline']}\n\n{sample_news_neutral['body']}"


        print("\n--- Testing Sentiment Analysis (Positive News) ---")
        sentiment_result_pos = analyze_sentiment_gemini(full_text_positive, target_cryptos=["Bitcoin"])
        if sentiment_result_pos:
            print(f"Sentiment: {sentiment_result_pos.get('sentiment')}")
            print(f"Reasoning: {sentiment_result_pos.get('reasoning')}")
            if sentiment_result_pos.get('error'):
                print(f"Error: {sentiment_result_pos.get('error')}")

        print("\n--- Testing Sentiment Analysis (Negative News) ---")
        sentiment_result_neg = analyze_sentiment_gemini(full_text_negative, target_cryptos=["Bitcoin", "Ethereum"])
        if sentiment_result_neg:
            print(f"Sentiment: {sentiment_result_neg.get('sentiment')}")
            print(f"Reasoning: {sentiment_result_neg.get('reasoning')}")
            if sentiment_result_neg.get('error'):
                print(f"Error: {sentiment_result_neg.get('error')}")

        print("\n--- Testing Sentiment Analysis (Neutral News) ---")
        sentiment_result_neutral = analyze_sentiment_gemini(full_text_neutral)
        if sentiment_result_neutral:
            print(f"Sentiment: {sentiment_result_neutral.get('sentiment')}")
            print(f"Reasoning: {sentiment_result_neutral.get('reasoning')}")
            if sentiment_result_neutral.get('error'):
                print(f"Error: {sentiment_result_neutral.get('error')}")

        print("\n--- Testing Summarization ---")
        summary_result = summarize_text_gemini(full_text_positive, max_length=50)
        if summary_result:
            print(f"Summary: {summary_result.get('summary')}")
            if summary_result.get('error'):
                print(f"Error: {summary_result.get('error')}")

        print("\n--- Testing with Empty Content ---")
        empty_sentiment = analyze_sentiment_gemini("")
        print(f"Empty Sentiment Result: {empty_sentiment}")
        empty_summary = summarize_text_gemini("")
        print(f"Empty Summary Result: {empty_summary}")

        # Test case for when prompt might be blocked
        print("\n--- Testing Sentiment Analysis (Potentially Blocked Content) ---")
        # This is a generic example, actual blocking depends on model's fine-tuning
        potentially_problematic_text = "This news article discusses illegal activities related to cryptocurrency."
        sentiment_result_problematic = analyze_sentiment_gemini(potentially_problematic_text)
        if sentiment_result_problematic:
            print(f"Sentiment: {sentiment_result_problematic.get('sentiment')}")
            print(f"Reasoning: {sentiment_result_problematic.get('reasoning')}")
            if sentiment_result_problematic.get('error'):
                print(f"Error: {sentiment_result_problematic.get('error')}")

    # Add a reminder for the user about the API Key
    print("\nReminder: Ensure the GOOGLE_GENAI_API_KEY environment variable is set for these tests to connect to the API.")
    print("The output above will show 'API not configured' or connection errors if the key is missing or invalid.")
    print("Mocked tests will be added in test_ai_analyst.py for automated testing without a live API key.")
import re # Added for parsing
