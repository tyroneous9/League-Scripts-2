import time
import threading
import keyboard
import win32api
import win32con
import logging
from config_utils import disable_insecure_request_warning, load_settings
from constants import (
    HEALTH_TICK_COLOR, PLAYER_HEALTH_BAR_COLOR, ENEMY_HEALTH_BAR_COLOR,
    ALLY_HEALTH_BAR_COLOR, SCREEN_CENTER
)
from utils import click_percent_relative, find_text_location, poll_game_data, click_percent, get_screenshot, find_champion_location
from logging_config import setup_logging


setup_logging()
disable_insecure_request_warning()

keybinds, general = load_settings()
latest_game_data = None


def shop_phase():
    # Level up abilities
    # hold_key = keybinds.get("hold_to_level")
    # if hold_key and all(keybinds.get(f"spell_{i}") for i in range(1, 5)):
    #     for i in range(1, 5):
    #         combo = f"{hold_key}+{keybinds.get(f'spell_{i}')}"

    #         keyboard.send(combo)
    #         time.sleep(0.1)

    # Open shop
    keyboard.send(keybinds.get("shop"))
    time.sleep(0.5)

    # Find shop menu location and click it before buying
    shop_location = find_text_location("SELL")
    if shop_location:
        x, y = shop_location[:2]
    else:
        return

    # Buy recommended item
    click_percent_relative(x, y, 15, -25,"right")
    time.sleep(0.5)

    # Close shop
    keyboard.send(keybinds.get("shop"))
    time.sleep(0.5)


def combat_phase():
    # Try to find enemy champion location
    enemy_location = find_champion_location(ENEMY_HEALTH_BAR_COLOR, HEALTH_TICK_COLOR)
    if enemy_location:
        # Move cursor to enemy and attack
        win32api.SetCursorPos(enemy_location)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, enemy_location[0], enemy_location[1], 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, enemy_location[0], enemy_location[1], 0, 0)
        keyboard.send(keybinds.get("spell_1"))
        keyboard.send(keybinds.get("spell_2"))
        keyboard.send(keybinds.get("spell_3"))
        keyboard.send(keybinds.get("spell_4"))
        keyboard.send(keybinds.get("item_1"))
        keyboard.send(keybinds.get("item_2"))
        keyboard.send(keybinds.get("item_3"))
        keyboard.send(keybinds.get("item_4"))
        keyboard.send(keybinds.get("item_5"))
        keyboard.send(keybinds.get("item_6"))
        logging.info(f"Attacked enemy at {enemy_location}")
    else:
        logging.info("No enemy found. Attempting to select ally.")
        # Pan camera to ally 1 (MAY NEED TO SEARCH ALLY POSITION)
        ally_key = keybinds.get("select_ally_1")
        if ally_key:
            keyboard.send(ally_key)
            time.sleep(0.1)
        # Move to ally
        win32api.SetCursorPos(SCREEN_CENTER)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, SCREEN_CENTER[0], SCREEN_CENTER[1], 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, SCREEN_CENTER[0], SCREEN_CENTER[1], 0, 0)


def run_arena_bot():
    # Start polling thread for game data
    polling_thread = threading.Thread(target=poll_game_data, args=({'data': None},), daemon=True)
    polling_thread.start()
    time.sleep(2)
    try:
        while True:
            # Main loop logic here
            shop_phase()
            

            time.sleep(2)  # Main loop interval
    except KeyboardInterrupt:
        logging.info("Arena bot stopped.")


if __name__ == "__main__":
    run_arena_bot()



