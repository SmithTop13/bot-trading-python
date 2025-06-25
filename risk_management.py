# risk_management.py
# This module will handle risk assessment for proposed trades.

import logging

logger = logging.getLogger(__name__)

# --- Risk Parameters (Hardcoded for now, can be moved to config) ---
MAX_CAPITAL_PER_TRADE_PERCENTAGE = 0.02  # Max 2% of total capital on a single trade
MAX_CONCURRENT_OPEN_TRADES = 3          # Max 3 open trades at any time
DEFAULT_STOP_LOSS_PERCENTAGE = 0.05     # Default 5% conceptual stop-loss
MIN_USD_BALANCE_AFTER_TRADE = 10.0      # Minimum USD balance to maintain after a trade (example)
# For crypto assets, minimum balance might be defined per asset if needed

def check_position_size(
    proposed_trade_value_usd: float,
    total_capital_usd: float,
    max_capital_percentage: float = MAX_CAPITAL_PER_TRADE_PERCENTAGE
) -> tuple[bool, str]:
    """
    Checks if the proposed trade value is within the allowed percentage of total capital.

    Args:
        proposed_trade_value_usd: The USD value of the proposed trade.
        total_capital_usd: The total available trading capital in USD.
        max_capital_percentage: The maximum percentage of capital to risk per trade.

    Returns:
        A tuple (is_valid, reason_if_not_valid).
    """
    if total_capital_usd <= 0:
        return False, "Total capital is zero or negative."

    allowed_trade_value = total_capital_usd * max_capital_percentage
    if proposed_trade_value_usd > allowed_trade_value:
        reason = (
            f"Proposed trade value ${proposed_trade_value_usd:.2f} exceeds "
            f"max allowed ${allowed_trade_value:.2f} ({max_capital_percentage*100}% of total capital)."
        )
        return False, reason
    return True, "Position size is acceptable."

def check_max_open_positions(
    current_open_trades: int,
    max_open_trades_allowed: int = MAX_CONCURRENT_OPEN_TRADES
) -> tuple[bool, str]:
    """
    Checks if opening a new trade would exceed the maximum number of concurrent open trades.

    Args:
        current_open_trades: The current number of active open trades.
        max_open_trades_allowed: The maximum number of concurrent trades allowed.

    Returns:
        A tuple (is_valid, reason_if_not_valid).
    """
    if current_open_trades >= max_open_trades_allowed:
        reason = (
            f"Opening new trade would exceed max {max_open_trades_allowed} open positions "
            f"(currently {current_open_trades})."
        )
        return False, reason
    return True, "Max open positions check passed."

def calculate_conceptual_stop_loss(
    entry_price: float,
    side: str, # "BUY" or "SELL"
    stop_loss_percentage: float = DEFAULT_STOP_LOSS_PERCENTAGE
) -> float | None:
    """
    Calculates a conceptual stop-loss price.

    Args:
        entry_price: The entry price of the trade.
        side: The side of the trade ('BUY' or 'SELL').
        stop_loss_percentage: The percentage below/above entry for stop-loss.

    Returns:
        The calculated stop-loss price, or None if side is invalid.
    """
    if entry_price <= 0:
        logger.warning("Entry price must be positive to calculate stop-loss.")
        return None

    if side.upper() == "BUY":
        return entry_price * (1 - stop_loss_percentage)
    elif side.upper() == "SELL": # For short selling, not primary focus now
        return entry_price * (1 + stop_loss_percentage)
    else:
        logger.error(f"Invalid trade side '{side}' for stop-loss calculation.")
        return None

def check_minimum_balance(
    current_balance_of_asset_to_spend: float,
    amount_of_asset_to_spend: float,
    min_required_balance_after_trade: float = 0.0 # Could be asset specific
) -> tuple[bool, str]:
    """
    Checks if the account will have a minimum required balance of the asset being spent
    after the trade. For BUY orders, this is typically USD. For SELL orders, it's the crypto asset.

    Args:
        current_balance_of_asset_to_spend: Current available balance of the asset that will be spent.
        amount_of_asset_to_spend: The amount of that asset proposed to be spent.
        min_required_balance_after_trade: The minimum amount of that asset to keep after the trade.

    Returns:
        A tuple (is_valid, reason_if_not_valid).
    """
    if current_balance_of_asset_to_spend < amount_of_asset_to_spend:
        reason = (
            f"Insufficient balance of asset to spend. Available: {current_balance_of_asset_to_spend}, "
            f"Proposed to spend: {amount_of_asset_to_spend}."
        )
        return False, reason

    if (current_balance_of_asset_to_spend - amount_of_asset_to_spend) < min_required_balance_after_trade:
        reason = (
            f"Trade would leave balance of asset below minimum required {min_required_balance_after_trade}. "
            f"Available: {current_balance_of_asset_to_spend}, Spending: {amount_of_asset_to_spend}."
        )
        return False, reason
    return True, "Minimum balance check passed."


def is_trade_approved(
    trade_proposal: dict,
    total_capital_usd: float,
    current_open_positions_count: int,
    # Balances should be specific to the assets involved in the trade
    # For a BUY of BTCUSD: available_usd_balance would be primary.
    # For a SELL of BTCUSD: available_btc_balance would be primary.
    available_balance_of_asset_to_be_spent: float,
    asset_symbol_being_spent: str # e.g. "USD" for a BUY, "BTC" for a SELL
) -> tuple[bool, str, float | None]:
    """
    Evaluates a trade proposal against defined risk management rules.

    Args:
        trade_proposal: A dictionary describing the trade. Expected keys:
            'action': 'BUY' or 'SELL'
            'symbol': e.g., 'BTCUSD'
            'amount_crypto': The amount of crypto to buy/sell (e.g., 0.1 BTC)
            'price': The price at which to trade (e.g., 50000 USD for BTC)
            'estimated_value_usd': The total USD value of the trade (amount_crypto * price)
        total_capital_usd: Current total trading capital in USD.
        current_open_positions_count: Number of currently active trades.
        available_balance_of_asset_to_be_spent: Current available balance of the asset that will be debited.
                                                (e.g. USD for a BUY, BTC for a SELL)
        asset_symbol_being_spent: Symbol of the asset being spent (e.g., "USD", "BTC").

    Returns:
        A tuple: (is_approved: bool, reason: str, conceptual_stop_loss_price: float | None)
    """
    action = trade_proposal.get('action', '').upper()
    # symbol = trade_proposal.get('symbol') # Not directly used in generic checks yet
    price = trade_proposal.get('price')
    estimated_value_usd = trade_proposal.get('estimated_value_usd')
    amount_crypto_to_trade = trade_proposal.get('amount_crypto')


    if not all([action, price, estimated_value_usd, amount_crypto_to_trade is not None]): # amount_crypto can be 0 for HOLD
        logger.error(f"Trade proposal is missing essential fields: {trade_proposal}")
        return False, "Trade proposal incomplete.", None

    if action not in ["BUY", "SELL"]:
        # HOLD actions don't need risk approval in this context, or are handled differently
        return False, f"Invalid action '{action}' for risk approval.", None

    # 1. Check Position Size
    pos_size_ok, pos_size_reason = check_position_size(estimated_value_usd, total_capital_usd)
    if not pos_size_ok:
        return False, pos_size_reason, None
    logger.debug(f"Position size check: {pos_size_reason}")

    # 2. Check Max Open Positions (only if it's a new trade, not closing an existing one)
    #    This logic might need refinement if distinguishing new vs closing trades. Assuming new for now.
    max_open_ok, max_open_reason = check_max_open_positions(current_open_positions_count)
    if not max_open_ok:
        return False, max_open_reason, None
    logger.debug(f"Max open positions check: {max_open_reason}")

    # 3. Check Minimum Balance of Asset to be Spent
    asset_to_spend_amount = 0
    min_balance_threshold = 0

    if action == "BUY":
        asset_to_spend_amount = estimated_value_usd # Spending USD
        # Assuming asset_symbol_being_spent is "USD" if passed correctly from main
        min_balance_threshold = MIN_USD_BALANCE_AFTER_TRADE if asset_symbol_being_spent == "USD" else 0.0
    elif action == "SELL":
        asset_to_spend_amount = amount_crypto_to_trade # Spending Crypto
        # For crypto, min balance could be 0 or a dust threshold
        min_balance_threshold = 0.0 # Defaulting to 0 for crypto assets for now

    min_balance_ok, min_balance_reason = check_minimum_balance(
        available_balance_of_asset_to_be_spent,
        asset_to_spend_amount,
        min_balance_threshold
    )
    if not min_balance_ok:
        return False, min_balance_reason, None
    logger.debug(f"Minimum balance check: {min_balance_reason}")

    # 4. Calculate Conceptual Stop-Loss
    stop_loss_price = calculate_conceptual_stop_loss(price, action)
    if stop_loss_price is None: # Should not happen if action is BUY/SELL and price > 0
        logger.warning(f"Could not calculate stop-loss for {action} @ {price}")
        # Decide if this is a failure condition. For now, let's say it's not critical if other checks pass.

    logger.info(f"Trade approved. Proposal: {trade_proposal}, Conceptual SL: {stop_loss_price}")
    return True, "Trade approved by risk management.", stop_loss_price


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Testing Risk Management Module...")

    # Example Usage:
    sample_total_capital = 10000  # USD
    sample_open_trades = 1
    sample_available_usd = 5000
    sample_available_btc = 0.5

    # Test Case 1: Approved BUY
    buy_proposal_ok = {
        'action': 'BUY',
        'symbol': 'BTCUSD',
        'amount_crypto': 0.002, # Value = 0.002 * 50000 = 100 USD
        'price': 50000,
        'estimated_value_usd': 100.00
    }
    approved, reason, sl = is_trade_approved(
        buy_proposal_ok, sample_total_capital, sample_open_trades, sample_available_usd, "USD"
    )
    print(f"\nTest BUY OK: Approved: {approved}, Reason: {reason}, Stop-Loss: {sl}")
    assert approved

    # Test Case 2: Denied BUY - Too large position size
    buy_proposal_too_large = {
        'action': 'BUY',
        'symbol': 'BTCUSD',
        'amount_crypto': 0.01, # Value = 0.01 * 50000 = 500 USD (5% of 10k, default max is 2%)
        'price': 50000,
        'estimated_value_usd': 500.00
    }
    approved, reason, sl = is_trade_approved(
        buy_proposal_too_large, sample_total_capital, sample_open_trades, sample_available_usd, "USD"
    )
    print(f"Test BUY Too Large: Approved: {approved}, Reason: {reason}, Stop-Loss: {sl}")
    assert not approved
    assert "exceeds max allowed" in reason

    # Test Case 3: Denied BUY - Max open trades
    approved, reason, sl = is_trade_approved(
        buy_proposal_ok, sample_total_capital, MAX_CONCURRENT_OPEN_TRADES, sample_available_usd, "USD"
    )
    print(f"Test BUY Max Open: Approved: {approved}, Reason: {reason}, Stop-Loss: {sl}")
    assert not approved
    assert "exceed max" in reason

    # Test Case 4: Denied BUY - Insufficient USD balance
    buy_proposal_expensive = {
        'action': 'BUY',
        'symbol': 'BTCUSD',
        'amount_crypto': 0.002,
        'price': 500000, # Price makes it 1000 USD
        'estimated_value_usd': 1000.00
    }
    approved, reason, sl = is_trade_approved(
        buy_proposal_expensive, sample_total_capital, sample_open_trades, 500, "USD" # Only 500 USD available
    )
    print(f"Test BUY Insufficient USD: Approved: {approved}, Reason: {reason}, Stop-Loss: {sl}")
    assert not approved
    assert "Insufficient balance" in reason


    # Test Case 5: Approved SELL
    sell_proposal_ok = {
        'action': 'SELL',
        'symbol': 'BTCUSD',
        'amount_crypto': 0.01, # Selling 0.01 BTC
        'price': 50000,
        'estimated_value_usd': 500.00 # Will receive 500 USD
    }
    approved, reason, sl = is_trade_approved(
        sell_proposal_ok, sample_total_capital, sample_open_trades, sample_available_btc, "BTC" # 0.5 BTC available
    )
    print(f"Test SELL OK: Approved: {approved}, Reason: {reason}, Stop-Loss: {sl}")
    assert approved

    # Test Case 6: Denied SELL - Insufficient BTC balance
    approved, reason, sl = is_trade_approved(
        sell_proposal_ok, sample_total_capital, sample_open_trades, 0.005, "BTC" # Only 0.005 BTC available
    )
    print(f"Test SELL Insufficient BTC: Approved: {approved}, Reason: {reason}, Stop-Loss: {sl}")
    assert not approved
    assert "Insufficient balance" in reason

    # Test Case 7: Incomplete proposal
    incomplete_proposal = {'action': 'BUY', 'symbol': 'BTCUSD'}
    approved, reason, sl = is_trade_approved(
        incomplete_proposal, sample_total_capital, sample_open_trades, sample_available_usd, "USD"
    )
    print(f"Test Incomplete Proposal: Approved: {approved}, Reason: {reason}, Stop-Loss: {sl}")
    assert not approved
    assert "Trade proposal incomplete" in reason

    print("\nIndividual function tests:")
    print(check_position_size(100, 10000))
    print(check_position_size(300, 10000))
    print(check_max_open_positions(2))
    print(check_max_open_positions(3))
    print(calculate_conceptual_stop_loss(50000, "BUY"))
    print(calculate_conceptual_stop_loss(50000, "SELL"))
    print(check_minimum_balance(1000, 500, 10)) # Spending USD
    print(check_minimum_balance(1000, 995, 10)) # Spending USD, will go below min
    print(check_minimum_balance(0.5, 0.1, 0)) # Spending BTC
    print(check_minimum_balance(0.5, 0.6, 0)) # Spending BTC, insufficient

    logger.info("Risk Management Module testing finished.")
