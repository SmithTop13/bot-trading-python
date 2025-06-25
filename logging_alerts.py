import logging
import sys
import config

def setup_logging():
    """Configures the logging system for the bot."""
    logger = logging.getLogger('TradingBot')

    # Set overall minimum logging level (can be overridden by handlers)
    log_level_str = getattr(config, 'LOG_LEVEL', 'INFO').upper()
    numeric_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(numeric_level)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s')

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    log_file = getattr(config, 'LOG_FILE', 'bot.log')
    try:
        file_handler = logging.FileHandler(log_file, mode='a') # Append mode
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except IOError as e:
        logger.error(f"Could not open log file {log_file} for writing: {e}", exc_info=True)
        # Fallback to console only if file logging fails
        print(f"WARNING: Failed to initialize file logging. Logging to console only. Error: {e}")


    # Initial log message
    logger.info(f"Logging configured. Level: {log_level_str}. Log file: {log_file if 'file_handler' in locals() else 'N/A'}")
    return logger

# --- Alerting ---
# For Phase 1, alerts are simple print statements or logs.
# Future phases might integrate email, SMS, etc.

def critical_alert(logger_instance, message):
    """Logs a critical message and prints it for immediate attention."""
    if logger_instance:
        logger_instance.critical(message)
    # In a real system, this might also send an email or push notification.
    print(f"CRITICAL ALERT: {message}")

def error_alert(logger_instance, message, exc_info=False):
    """Logs an error message."""
    if logger_instance:
        logger_instance.error(message, exc_info=exc_info)
    print(f"ERROR ALERT: {message}")


if __name__ == '__main__':
    # --- Test Logging and Alerts ---
    # This requires config.py to be in the same directory or Python path
    print("--- Logging & Alerts Test ---")

    # Attempt to load config for LOG_LEVEL and LOG_FILE
    # If config.py is not found or variables are missing, defaults will be used by setup_logging
    try:
        import config
        print(f"Config loaded. LOG_LEVEL: {config.LOG_LEVEL}, LOG_FILE: {config.LOG_FILE}")
    except ImportError:
        print("config.py not found. Using default logging settings.")
    except AttributeError:
        print("LOG_LEVEL or LOG_FILE not found in config.py. Using default logging settings.")

    # Setup logging
    bot_logger = setup_logging()

    # Test log messages
    bot_logger.debug("This is a debug message.")
    bot_logger.info("This is an info message.")
    bot_logger.warning("This is a warning message.")
    bot_logger.error("This is an error message.")
    bot_logger.critical("This is a critical message.")

    # Test alerts
    critical_alert(bot_logger, "Test critical alert! System is going down hypothetically.")
    error_alert(bot_logger, "Test error alert! Something went wrong.")
    error_alert(bot_logger, "Test error alert with exception info.", exc_info=True)

    print("--- End Logging & Alerts Test ---")
    print(f"Check '{getattr(config, 'LOG_FILE', 'bot.log')}' for file output (if file logging was successful).")
