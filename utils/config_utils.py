import json
import os
import urllib3

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "config_default.json")

def load_config(path=CONFIG_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing config at {path}")
    with open(path, "r") as f:
        return json.load(f)

def load_default_config():
    return load_config(DEFAULT_CONFIG_PATH)

def save_config(config, path=CONFIG_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=4)

def get_config_paths():
    return CONFIG_PATH, DEFAULT_CONFIG_PATH

def disable_insecure_request_warning():
    """Disable urllib3 InsecureRequestWarning for unverified HTTPS requests."""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_settings():
    config = load_config()
    return config.get("Keybinds", {}), config.get("General", {})

def get_selected_game_mode():
    config = load_config()
    return config.get("General", {}).get("selected_game_mode").lower()

def set_selected_game_mode(mode):
    config = load_config()
    config["General"]["selected_game_mode"] = mode
    save_config(config)
