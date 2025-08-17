import requests
import time
import threading
import os
import keyboard
import win32api
import win32con
from config_utils import load_config, disable_insecure_request_warning, load_settings
from constants import LIVE_CLIENT_URL, DEFAULT_API_TIMEOUT, KEY_PRESS_DELAY
from utils import poll_game_data, click_league_client 

disable_insecure_request_warning()

keybinds, general = load_settings()
latest_game_data = None

def shop_phase():
    # Level up abilities
    hold_key = keybinds.get("hold_to_level")
    if hold_key and all(keybinds.get(f"spell_{i}") for i in range(1, 5)):
        for i in range(1, 5):
            combo = f"{hold_key}+{keybinds.get(f'spell_{i}')}"

            keyboard.send(combo)
            time.sleep(0.1)

    # Shopping
    keyboard.send(keybinds.get("shop"))
    time.sleep(0.5)

    # Buy recommended item
    click_league_client(50, 70) 
    time.sleep(0.5)

    # Optionally, buy random legendary item 
    click_league_client(67, 67)  
    time.sleep(0.5)

    # Close shop
    keyboard.send(keybinds.get("shop"))
    time.sleep(0.5)

def run_arena_bot():
    # Start polling thread for game data
    polling_thread = threading.Thread(target=poll_game_data, daemon=True)
    polling_thread.start()

    try:
        while True:
            # Example: Use latest_game_data if needed
            # print(latest_game_data)

            shop_phase()
            time.sleep(1)  # Main loop interval
    except KeyboardInterrupt:
        print("Arena bot stopped.")

if __name__ == "__main__":
    run_arena_bot()
