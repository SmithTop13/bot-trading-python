from abc import ABC, abstractmethod

class Exchange(ABC):
    """
    Abstract base class for an exchange interface.
    Defines the common methods that all exchange connectors should implement.
    """

    @abstractmethod
    def connect(self, api_key: str, api_secret: str) -> None:
        """
        Connects to the exchange using the provided API key and secret.

        Args:
            api_key: The API key for authentication.
            api_secret: The API secret for authentication.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Disconnects from the exchange.
        """
        pass

    @abstractmethod
    def get_account_balance(self) -> dict:
        """
        Retrieves the account balance from the exchange.

        Returns:
            A dictionary representing the account balance (e.g., {'BTC': 0.5, 'USD': 10000}).
        """
        pass

    @abstractmethod
    def get_market_data(self, symbol: str) -> dict:
        """
        Retrieves market data for a specific trading symbol.

        Args:
            symbol: The trading symbol (e.g., 'BTC/USD').

        Returns:
            A dictionary containing market data (e.g., {'bid': 50000, 'ask': 50001, 'last_price': 50000.5}).
        """
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float = None) -> str:
        """
        Places a new order on the exchange.

        Args:
            symbol: The trading symbol (e.g., 'BTC/USD').
            side: The order side ('buy' or 'sell').
            type: The order type (e.g., 'limit', 'market').
            amount: The quantity of the asset to trade.
            price: The price for limit orders (optional for market orders).

        Returns:
            The order ID of the placed order.
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancels an existing order on the exchange.

        Args:
            order_id: The ID of the order to cancel.

        Returns:
            True if the order was successfully cancelled, False otherwise.
        """
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> dict:
        """
        Retrieves the status of a specific order.

        Args:
            order_id: The ID of the order to check.

        Returns:
            A dictionary containing the order status information (e.g., {'status': 'filled', 'executed_amount': 0.1}).
        """
        pass
