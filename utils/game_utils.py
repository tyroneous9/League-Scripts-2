import keyboard
import time
import numpy as np
import cv2
import logging
from core.constants import SCREEN_CENTER
import random
from utils.config_utils import load_settings
from utils.general_utils import click_percent, find_text_location, get_screenshot


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

_keybinds, _general = load_settings()

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
    click_percent(x, y, 0, -60, "left")
    click_percent(x, y, 15, -25, "right")
    click_percent(x, y, 15, -25, "right")
    click_percent(x, y, 15, -25, "right")

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
    keyboard.send(ally_key)
    # Move randomly near ally
    offset_x = random.randint(-15, 15)  # percent offset
    offset_y = random.randint(-15, 15)  # percent offset
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1], offset_x, offset_y, "right")


def retreat_to_ally():
    """
    Moves the player to the specified ally position and randomly presses summoner spell keys.
    Sometimes presses only one, both, or none for added randomness.
    """
    # Move to ally position
    move_to_ally()
    time.sleep(0.1)

    # Randomly use summoner spells
    press_sum_1 = random.choice([True, False])
    press_sum_2 = random.choice([True, False])

    if press_sum_1:
        sum_1_key = _keybinds.get("sum_1")
        if sum_1_key:
            keyboard.send(sum_1_key)
            time.sleep(0.1)
    if press_sum_2:
        sum_2_key = _keybinds.get("sum_2")
        if sum_2_key:
            keyboard.send(sum_2_key)
            time.sleep(0.1)
    move_to_ally()


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
    click_percent(x, y, offset_x, offset_y, "right")


def get_distance(coord1, coord2):
    """
    Calculates the Euclidean distance between two (x, y) coordinates.
    Args:
        coord1 (tuple): (x1, y1)
        coord2 (tuple): (x2, y2)
    Returns:
        float: Distance between the two points.
    """
    x1, y1 = coord1
    x2, y2 = coord2
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5



