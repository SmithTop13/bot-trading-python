import configparser
import os

def load_config(config_file_path: str = 'config.ini') -> configparser.ConfigParser:
    """
    Loads configuration settings from an INI file.

    Args:
        config_file_path: The path to the configuration file.
                          Defaults to 'config.ini' in the current working directory.

    Returns:
        A ConfigParser object containing the loaded configuration.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        KeyError: If an expected section or key is missing from the file.
    """
    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"Configuration file not found: {config_file_path}")

    config = configparser.ConfigParser()
    config.read(config_file_path)

    if 'binance' not in config:
        raise KeyError("Missing 'binance' section in the configuration file.")

    if 'api_key' not in config['binance']:
        raise KeyError("Missing 'api_key' in the 'binance' section.")

    if 'api_secret' not in config['binance']:
        raise KeyError("Missing 'api_secret' in the 'binance' section.")

    return config

def get_binance_credentials(config_file_path: str = 'config.ini') -> tuple[str, str]:
    """
    Retrieves Binance API key and secret from the configuration file.

    Args:
        config_file_path: The path to the configuration file.
                          Defaults to 'config.ini' in the current working directory.

    Returns:
        A tuple containing the API key and API secret.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        KeyError: If an expected section or key is missing from the file.
    """
    config = load_config(config_file_path)
    api_key = config['binance']['api_key']
    api_secret = config['binance']['api_secret']
    return api_key, api_secret

if __name__ == '__main__':
    # Example usage:
    try:
        # Assuming config.ini is in the same directory as this script when run directly
        # For the main application, the path might need to be adjusted e.g., '../config.ini'
        # or an absolute path.

        # Determine the correct path to config.ini relative to this script's location
        # This is important because this script is in core/ and config.ini is in the root.
        script_dir = os.path.dirname(__file__) # core
        root_dir = os.path.dirname(script_dir) # <repository_root>
        config_path = os.path.join(root_dir, 'config.ini')


        binance_api_key, binance_api_secret = get_binance_credentials(config_path)
        print(f"Binance API Key: {binance_api_key}")
        print(f"Binance API Secret: {binance_api_secret}")

        # Example of loading the full config
        full_config = load_config(config_path)
        print(f"Full Binance config section: {dict(full_config['binance'])}")

    except (FileNotFoundError, KeyError) as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
