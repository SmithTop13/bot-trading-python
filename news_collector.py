# news_collector.py
# This module will be responsible for collecting and preprocessing news data.

import os
import requests
import re
from html import unescape

NEWS_API_BASE_URL = "https://newsapi.org/v2/everything"

def fetch_crypto_news(api_key: str, query: str, num_articles: int = 10, language: str = "en", sort_by: str = "publishedAt"):
    """
    Fetches cryptocurrency news articles from NewsAPI.org.

    Args:
        api_key: The NewsAPI.org API key.
        query: The search query (e.g., "Bitcoin", "Ethereum", "cryptocurrency").
        num_articles: The number of articles to fetch (max 100 for NewsAPI free/dev tier).
        language: The language of the articles (e.g., "en").
        sort_by: How to sort articles ('relevancy', 'popularity', 'publishedAt').

    Returns:
        A list of dictionaries, where each dictionary represents an article
        with keys: 'headline', 'body', 'timestamp', 'source', 'url'.
        Returns an empty list if an error occurs or no articles are found.
    """
    if not api_key:
        print("Error: NEWS_API_KEY not provided.")
        return []

    params = {
        "q": query,
        "apiKey": api_key,
        "pageSize": min(num_articles, 100),  # Max 100 for developer plan
        "language": language,
        "sortBy": sort_by,
    }

    try:
        response = requests.get(NEWS_API_BASE_URL, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()

        if data.get("status") == "ok":
            articles_out = []
            for article_data in data.get("articles", []):
                headline = article_data.get("title")
                # Use content if available, otherwise description. Content is often truncated.
                body = article_data.get("content") if article_data.get("content") else article_data.get("description")
                timestamp = article_data.get("publishedAt")
                source_name = article_data.get("source", {}).get("name")
                url = article_data.get("url")

                if headline and body and timestamp and source_name: # Ensure essential fields are present
                    articles_out.append({
                        "headline": clean_text(headline),
                        "body": clean_text(body),
                        "timestamp": timestamp,
                        "source": source_name,
                        "url": url
                    })
            return articles_out
        else:
            print(f"Error fetching news: {data.get('message')}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"RequestException fetching news: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred fetching news: {e}")
        return []

def clean_text(text: str) -> str:
    """
    Basic text cleaning: removes HTML tags, decodes HTML entities,
    removes special characters (keeps basic punctuation), and normalizes whitespace.
    """
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = unescape(text)
    # Remove special characters, keeping alphanumeric, spaces, and basic punctuation.
    # This regex can be adjusted based on what needs to be preserved for sentiment analysis.
    text = re.sub(r'[^a-zA-Z0-9\s.,!?-]', '', text)
    # Normalize whitespace (replace multiple spaces/newlines with a single space)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

if __name__ == '__main__':
    # This is for basic testing.
    # You need to set the NEWS_API_KEY environment variable to run this.
    print("Attempting to fetch news (ensure NEWS_API_KEY is set)...")
    news_api_key = os.getenv("NEWS_API_KEY")
    if not news_api_key:
        print("Please set the NEWS_API_KEY environment variable to test news_collector.py directly.")
    else:
        print("\nFetching 'Bitcoin' news:")
        btc_articles = fetch_crypto_news(news_api_key, "Bitcoin", num_articles=3)
        if btc_articles:
            for art in btc_articles:
                print(f"  Headline: {art['headline']}")
                print(f"  Body (snippet): {art['body'][:100]}...")
                print(f"  Source: {art['source']}, Timestamp: {art['timestamp']}")
                print(f"  URL: {art['url']}")
                print("-" * 20)
        else:
            print("No Bitcoin articles found or error occurred.")

        print("\nFetching 'Ethereum' news:")
        eth_articles = fetch_crypto_news(news_api_key, "Ethereum", num_articles=3)
        if eth_articles:
            for art in eth_articles:
                print(f"  Headline: {art['headline']}")
                print(f"  Body (snippet): {art['body'][:100]}...")
                print(f"  Source: {art['source']}, Timestamp: {art['timestamp']}")
                print(f"  URL: {art['url']}")
                print("-" * 20)
        else:
            print("No Ethereum articles found or error occurred.")

        print("\nTesting clean_text:")
        test_html = "<p>This is <b>bold</b> &amp; has  лишние символы. Extra   spaces.</p>"
        cleaned = clean_text(test_html)
        print(f"Original: {test_html}")
        print(f"Cleaned: {cleaned}")
