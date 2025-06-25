# AI-Powered Cryptocurrency Trading Bot for Gemini Exchange

This project is an automated cryptocurrency trading bot that leverages AI for market analysis and sentiment, with the goal of trading on the Gemini exchange. This README outlines the project structure, setup, and usage, starting with the foundational components built in Phase 1.

## Project Overview

The bot aims to:
1.  Collect real-time and historical market data from Gemini and other sources.
2.  Utilize AI (specifically targeting Gemini AI Studio / Google Gen AI SDK) for market trend analysis, sentiment analysis from news, and generating trading signals.
3.  Execute trades automatically on the Gemini exchange based on AI-driven decisions and risk management rules.
4.  Provide robust logging, alerting, and data storage capabilities.

## System Architecture Diagram

```mermaid
graph TD

subgraph User Interaction
A[Developer / Trader]
end

subgraph "Core Bot Logic (Python Application)"
B[Python Script: Main Bot Logic]
B --> C{Decision Engine}
C --> D[Risk Management Module]
C --> E[Order Management Module]
B --> F[Data Collection Module]
B --> G[Logging & Alerting]
end

subgraph AI Model
H[Gemini AI Studio / Google Gen AI SDK]
end

subgraph External Services
I[Gemini Exchange API]
J[Market Data Sources]
K{News Source APIs<br>(e.g., Bloomberg, Reuters, Google News Search API)}
end

subgraph Data & Storage
L["Local Data Storage (e.g., CSV, SQLite)"]
M["Database (e.g., PostgreSQL, MongoDB)"]
end

subgraph "Deployment & Monitoring (Optional but Recommended)"
N["Cloud Platform (e.g., Google Cloud, AWS, Azure)"]
O["Monitoring Tools (e.g., Grafana, Cloud Monitoring)"]
end

A -- Configures & Monitors --> B
B -- Sends Data & Prompts --> H
H -- Provides Signals/Analysis<br>(incl. Sentiment) --> C
F -- Fetches Real-time/Historical Data --> J
F -- Fetches Order Book/Ticker --> I

K -- Provides Raw News Articles/Headlines --> H
H -- Processes & Analyzes News Content<br>(e.g., Sentiment, Summarization) --> C

C -- Decides Buy/Sell/Hold --> E
D -- Applies Rules --> E
E -- Places/Manages Orders --> I
I -- Provides Trade Execution & Balances --> G
B -- Stores Logs/Data --> L
B -- Stores Data --> M
G -- Sends Alerts --> A
B -- Deployed On --> N
N -- Provides Metrics --> O
O -- Displays Dashboards --> A
```

## Phase 1 Features (Completed)

The initial phase focused on building the foundational framework:

*   **Core Bot Logic (`main.py`):** Entry point of the application, handles argument parsing (basic), and includes a graceful shutdown mechanism.
*   **Configuration Management (`config.py`):** Manages API keys (loaded from environment variables), exchange API endpoints, logging settings, and initial trading parameters.
*   **Logging & Alerting (`logging_alerts.py`):** Implements a robust logging system using Python's `logging` module, outputting to both console and a file (`bot.log`). Basic print alerts for critical events.
*   **Data Collection (`data_collector.py`):** Integrates with the Gemini Exchange API to:
    *   Fetch current ticker data.
    *   Fetch order book data.
    *   Fetch account balances (requires API key authentication).
    *   Includes basic error handling for API calls.
*   **Local Data Storage (`data_storage.py`):** Saves fetched market data (ticker, order book snapshots) to local CSV and JSON files in the `market_data/` directory, with accurate timestamps.
*   **Agent Guidance (`AGENTS.md`):** Provides instructions and context for AI agents working on this codebase.

## Setup and Installation

1.  **Prerequisites:**
    *   Python 3.8+
    *   `pip` for installing packages.

2.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

3.  **Install dependencies:**
    Currently, the main external dependency is `requests`. A `requirements.txt` will be added in future phases.
    ```bash
    pip install requests
    ```

4.  **Environment Variables:**
    For functionalities requiring authentication with the Gemini API (like fetching account balances), you need to set the following environment variables:
    *   `GEMINI_API_KEY`: Your Gemini API key.
    *   `GEMINI_API_SECRET`: Your Gemini API secret.

    It is highly recommended to use API keys from a **Gemini Sandbox account** for development and testing.

## Usage

To run the bot (Phase 1 functionality - data collection and storage):

```bash
python main.py
```

*   This will initialize the bot, attempt to fetch ticker and order book data for the default trading pair (e.g., BTCUSD from `config.py`).
*   Fetched data will be saved in the `market_data/` directory.
*   Logs will be printed to the console and saved in `bot.log`.
*   If API keys are configured, it will attempt to fetch and log account balances.

## Modules (Phase 1)

*   **`main.py`**: The main application script. Orchestrates the bot's operations.
*   **`config.py`**: Handles all configurations, including API keys, endpoints, and logging settings.
*   **`logging_alerts.py`**: Sets up and manages logging for the application.
*   **`data_collector.py`**: Responsible for all interactions with the Gemini API (fetching ticker, order book, balances).
*   **`data_storage.py`**: Handles saving data fetched by `data_collector.py` to local files.
*   **`AGENTS.md`**: Provides guidelines and context for AI developers working on this project.

## Future Development

The project will evolve through subsequent phases, including:

*   **AI Model Integration:** Connecting to Gemini AI Studio or Google Gen AI SDK for market predictions, sentiment analysis from news, and generating trading signals.
*   **Decision Engine:** Implementing logic to interpret AI signals and make trading decisions (buy/sell/hold).
*   **Risk Management:** Adding rules and modules to manage trading risks (e.g., stop-loss, position sizing).
*   **Order Execution:** Building robust mechanisms to place, monitor, and manage orders on the Gemini exchange.
*   **Advanced Alerting:** Integrating email, SMS, or push notifications for critical events.
*   **Database Integration:** Potentially moving from CSV/JSON to a more robust database (e.g., SQLite, PostgreSQL) for historical data and analysis.
*   **Backtesting Framework:** Developing tools to test trading strategies on historical data.
*   **UI/Dashboard:** A web interface for monitoring bot performance and managing settings.

Contributions and suggestions are welcome!## Project Overview

The bot aims to:
1.  Collect real-time and historical market data from Gemini and other sources.
2.  Utilize AI (specifically targeting Gemini AI Studio / Google Gen AI SDK) for market trend analysis, sentiment analysis from news, and generating trading signals.
3.  Execute trades automatically on the Gemini exchange based on AI-driven decisions and risk management rules.
4.  Provide robust logging, alerting, and data storage capabilities.

## System Architecture Diagram

```mermaid
graph TD

subgraph User Interaction
A[Developer / Trader]
end

subgraph "Core Bot Logic (Python Application)"
B[Python Script: Main Bot Logic]
B --> C{Decision Engine}
C --> D[Risk Management Module]
C --> E[Order Management Module]
B --> F[Data Collection Module]
B --> G[Logging & Alerting]
end

subgraph AI Model
H[Gemini AI Studio / Google Gen AI SDK]
end

subgraph External Services
I[Gemini Exchange API]
J[Market Data Sources]
K{News Source APIs<br>(e.g., Bloomberg, Reuters, Google News Search API)}
end

subgraph Data & Storage
L["Local Data Storage (e.g., CSV, SQLite)"]
M["Database (e.g., PostgreSQL, MongoDB)"]
end

subgraph "Deployment & Monitoring (Optional but Recommended)"
N["Cloud Platform (e.g., Google Cloud, AWS, Azure)"]
O["Monitoring Tools (e.g., Grafana, Cloud Monitoring)"]
end

A -- Configures & Monitors --> B
B -- Sends Data & Prompts --> H
H -- Provides Signals/Analysis<br>(incl. Sentiment) --> C
F -- Fetches Real-time/Historical Data --> J
F -- Fetches Order Book/Ticker --> I

K -- Provides Raw News Articles/Headlines --> H
H -- Processes & Analyzes News Content<br>(e.g., Sentiment, Summarization) --> C

C -- Decides Buy/Sell/Hold --> E
D -- Applies Rules --> E
E -- Places/Manages Orders --> I
I -- Provides Trade Execution & Balances --> G
B -- Stores Logs/Data --> L
B -- Stores Data --> M
G -- Sends Alerts --> A
B -- Deployed On --> N
N -- Provides Metrics --> O
O -- Displays Dashboards --> A
```

## Phase 1 Features (Completed)

The initial phase focused on building the foundational framework:

*   **Core Bot Logic (`main.py`):** Entry point of the application, handles argument parsing (basic), and includes a graceful shutdown mechanism.
*   **Configuration Management (`config.py`):** Manages API keys (loaded from environment variables), exchange API endpoints, logging settings, and initial trading parameters.
*   **Logging & Alerting (`logging_alerts.py`):** Implements a robust logging system using Python's `logging` module, outputting to both console and a file (`bot.log`). Basic print alerts for critical events.
*   **Data Collection (`data_collector.py`):** Integrates with the Gemini Exchange API to:
    *   Fetch current ticker data.
    *   Fetch order book data.
    *   Fetch account balances (requires API key authentication).
    *   Includes basic error handling for API calls.
*   **Local Data Storage (`data_storage.py`):** Saves fetched market data (ticker, order book snapshots) to local CSV and JSON files in the `market_data/` directory, with accurate timestamps.
*   **Agent Guidance (`AGENTS.md`):** Provides instructions and context for AI agents working on this codebase.

## Setup and Installation

1.  **Prerequisites:**
    *   Python 3.8+
    *   `pip` for installing packages.

2.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

3.  **Install dependencies:**
    Currently, the main external dependency is `requests`. A `requirements.txt` will be added in future phases.
    ```bash
    pip install requests
    ```

4.  **Environment Variables:**
    For functionalities requiring authentication with the Gemini API (like fetching account balances), you need to set the following environment variables:
    *   `GEMINI_API_KEY`: Your Gemini API key.
    *   `GEMINI_API_SECRET`: Your Gemini API secret.

    It is highly recommended to use API keys from a **Gemini Sandbox account** for development and testing.

## Usage

To run the bot (Phase 1 functionality - data collection and storage):

```bash
python main.py
```

*   This will initialize the bot, attempt to fetch ticker and order book data for the default trading pair (e.g., BTCUSD from `config.py`).
*   Fetched data will be saved in the `market_data/` directory.
*   Logs will be printed to the console and saved in `bot.log`.
*   If API keys are configured, it will attempt to fetch and log account balances.

## Modules (Phase 1)

*   **`main.py`**: The main application script. Orchestrates the bot's operations.
*   **`config.py`**: Handles all configurations, including API keys, endpoints, and logging settings.
*   **`logging_alerts.py`**: Sets up and manages logging for the application.
*   **`data_collector.py`**: Responsible for all interactions with the Gemini API (fetching ticker, order book, balances).
*   **`data_storage.py`**: Handles saving data fetched by `data_collector.py` to local files.
*   **`AGENTS.md`**: Provides guidelines and context for AI developers working on this project.

## Future Development

The project will evolve through subsequent phases, including:

*   **AI Model Integration:** Connecting to Gemini AI Studio or Google Gen AI SDK for market predictions, sentiment analysis from news, and generating trading signals.
*   **Decision Engine:** Implementing logic to interpret AI signals and make trading decisions (buy/sell/hold).
*   **Risk Management:** Adding rules and modules to manage trading risks (e.g., stop-loss, position sizing).
*   **Order Execution:** Building robust mechanisms to place, monitor, and manage orders on the Gemini exchange.
*   **Advanced Alerting:** Integrating email, SMS, or push notifications for critical events.
*   **Database Integration:** Potentially moving from CSV/JSON to a more robust database (e.g., SQLite, PostgreSQL) for historical data and analysis.
*   **Backtesting Framework:** Developing tools to test trading strategies on historical data.
*   **UI/Dashboard:** A web interface for monitoring bot performance and managing settings.

Contributions and suggestions are welcome!
