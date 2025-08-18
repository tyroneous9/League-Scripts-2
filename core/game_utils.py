import keyboard
import requests
import time
import numpy as np
import cv2
import logging
from constants import DEFAULT_API_TIMEOUT, LIVE_CLIENT_URL
import random
from config_utils import disable_insecure_request_warning, load_settings
from general_utils import click_percent_relative, find_text_location, get_screenshot
import threading
from general_utils import listen_for_exit_key
from constants import SCREEN_CENTER
from logging_config import setup_logging


# ===========================
# Game Settings Utilities
# ===========================

def load_game_settings():
    """
    Loads keybinds and general settings for use in game utility functions.
    Returns:
        tuple: (keybinds dict, general settings dict)
    """
    keybinds, general = load_settings()
    logging.info("Keybinds and general settings loaded.")
    return keybinds, general

def initialize_game_script():
    """
    Performs all game-related initialization
    """
    setup_logging()
    disable_insecure_request_warning()
    threading.Thread(target=listen_for_exit_key, daemon=True).start()
    logging.info("Game utilities initialized.")


# ===========================
# API Data Retrieval
# ===========================

# Retrieve all game data from the live client API
def retrieve_game_data():
    """
    Retrieves all game data from the League client API.
    Returns:
        dict or None: Game data if successful, else None.
    """
    try:
        res = requests.get(f"{LIVE_CLIENT_URL}/allgamedata", timeout=DEFAULT_API_TIMEOUT, verify=False)
        if res.status_code == 200:
            return res.json()
        else:
            print("[ERROR] Game data request failed.")
            return None
    except Exception as e:
        print(f"[ERROR] Game data request failed: {e}")
        return None

# Poll game data at a regular interval and update the provided container
def poll_game_data(latest_game_data_container, poll_time=5):
    """
    Continuously polls game data and updates the provided container.
    Args:
        latest_game_data_container (dict): Container to store latest data.
        poll_time (int): Poll interval in seconds.
    """
    while True:
        latest_game_data_container['data'] = retrieve_game_data()
        time.sleep(poll_time)


# ===========================
# Game Data Retrieval
# ===========================

# Find the location of a champion by searching for health bar and tick colors
def find_champion_location(health_bar_bgr, health_tick_bgr, tolerance=2):
    """
    Finds the champion location by searching for health bar and tick colors in the screenshot.
    Args:
        health_bar_bgr (tuple): BGR color of health bar.
        health_tick_bgr (tuple): BGR color of health tick.
        tolerance (int): Color tolerance.
    Returns:
        tuple or None: (x, y) location if found, else None.
    """
    img = get_screenshot()

    lower_health_bar = np.array([max(c - tolerance, 0) for c in health_bar_bgr], dtype=np.uint8)
    upper_health_bar = np.array([min(c + tolerance, 255) for c in health_bar_bgr], dtype=np.uint8)
    mask_health_bar = cv2.inRange(img, lower_health_bar, upper_health_bar)

    lower_health_tick = np.array([max(c - tolerance, 0) for c in health_tick_bgr], dtype=np.uint8)
    upper_health_tick = np.array([min(c + tolerance, 255) for c in health_tick_bgr], dtype=np.uint8)
    mask_health_tick = cv2.inRange(img, lower_health_tick, upper_health_tick)

    search_size_x = 100
    height, width = mask_health_bar.shape

    for y in range(height):
        for x in range(width):
            if mask_health_bar[y, x] > 0:
                for dx in range(0, search_size_x + 1):
                    nx = x + dx
                    if nx < width and mask_health_tick[y, nx] > 0:
                        champion_location = (x, y+160)
                        return champion_location

    logging.debug("Health bar color not detected on screen or no valid champion location found.")
    return None


# ===========================
# Game Control Utilities
# ===========================

_keybinds, _general = load_game_settings()

def sleep_random(min_seconds, max_seconds):
    """
    Sleeps for a random duration between min_seconds and max_seconds.
    Args:
        min_seconds (float): Minimum sleep time in seconds.
        max_seconds (float): Maximum sleep time in seconds.
    """
    duration = random.uniform(min_seconds, max_seconds)
    time.sleep(duration)

def level_up_abilities(order=("R", "Q", "W", "E")):
    """
    Levels up all abilities using the cached keybinds in the specified order.
    Always levels 'R' first by default.
    Args:
        order (tuple): The order in which to level up spells. Default is ("R", "Q", "W", "E").
    """
    time.sleep(0.5)  # Wait a moment to ensure level up is available
    hold_key = _keybinds.get("hold_to_level")
    spell_keys = {
        "Q": _keybinds.get("spell_1"),
        "W": _keybinds.get("spell_2"),
        "E": _keybinds.get("spell_3"),
        "R": _keybinds.get("spell_4"),
    }
    if hold_key and all(spell_keys.values()):
        for key in order:
            key = key.upper()
            if key not in spell_keys:
                logging.error(f"Invalid spell key: {key}. Must be 'Q', 'W', 'E', or 'R'.")
                continue
            keyboard.send(f"{hold_key}+{spell_keys[key]}")
            time.sleep(0.1)

def buy_recommended_items():
    """
    Finds the shop location and performs recommended item purchases.
    Opens the shop if not already open.
    """
    time.sleep(0.5)  # Wait a moment to ensure shop is open
    shop_location = find_text_location("SELL")
    if not shop_location:
        # Open shop if not already open
        keyboard.send(_keybinds.get("shop"))
        time.sleep(0.5)
        shop_location = find_text_location("SELL")
        if not shop_location:
            logging.warning("Shop location could not be found after opening shop.")
            return

    x, y = shop_location[:2]

    # Buy recommended item
    click_percent_relative(x, y, 0, -60, "left")
    click_percent_relative(x, y, 15, -25, "right")
    click_percent_relative(x, y, 15, -25, "right")
    click_percent_relative(x, y, 15, -25, "right")

    # Close shop
    keyboard.send(_keybinds.get("shop"))

def move_to_ally(ally_number=1):
    """
    Pans camera to the specified ally and moves cursor to their location.
    Args:
        ally_number (int): The ally number to select (e.g., 1, 2, 3, 4).
    """
    ally_keys = {
        1: _keybinds.get("select_ally_1"),
        2: _keybinds.get("select_ally_2"),
        3: _keybinds.get("select_ally_3"),
        4: _keybinds.get("select_ally_4"),
    }
    ally_key = ally_keys.get(ally_number)
    if ally_key:
        keyboard.send(ally_key)
    # Move randomly near ally
    offset_x = random.randint(-15, 15)  # percent offset
    offset_y = random.randint(-15, 15)  # percent offset
    click_percent_relative(SCREEN_CENTER[0], SCREEN_CENTER[1], offset_x, offset_y, "right")

def move_random_offset(x, y, max_offset=15):
    """
    Moves a random distance offset from the given (x, y) location using percent-based relative click.
    Args:
        x (int): X coordinate of the base location.
        y (int): Y coordinate of the base location.
        max_offset (int): Maximum percent screen distance in any direction.
    """
    offset_x = random.randint(-max_offset, max_offset)  # percent offset
    offset_y = random.randint(-max_offset, max_offset)  # percent offset
    click_percent_relative(x, y, offset_x, offset_y, "right")
