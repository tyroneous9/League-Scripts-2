# ==========================================================
# Arena Mode Automation Script
# ==========================================================

import time
import threading
import keyboard
import logging
from constants import (
    HEALTH_TICK_COLOR, ENEMY_HEALTH_BAR_COLOR, SCREEN_CENTER
)
from general_utils import click_percent_relative
from game_utils import (
    load_game_settings,
    move_random_offset,
    move_to_ally,
    poll_game_data,
    find_champion_location,
    initialize_game_script,
    buy_recommended_items,
    level_up_abilities,
    sleep_random
)

# ===========================
# Initialization
# ===========================

initialize_game_script()
_keybinds, _general = load_game_settings()
_latest_game_data = {'data': None}

# ===========================
# Arena Phase Functions
# ===========================

def shop_phase():
    """
    Handles the Arena shop phase which is detected upon level up
    """
    logging.info("Running shop phase...")
    # Click screen center in case of augment card
    click_percent_relative(SCREEN_CENTER[0], SCREEN_CENTER[1])

    # Buy recommended items
    buy_recommended_items()

    # Level up abilities
    level_up_abilities()


def combat_phase():
    """
    Handles the combat phase:
    - Finds enemy champion location and attacks w/ spells and items
    - If no enemy found, find and move toward ally
    """
    logging.info("Running combat phase...")
    center_camera_key = _keybinds.get("center_camera")
    keyboard.press(center_camera_key)
    time.sleep(0.1)
    keyboard.release(center_camera_key)

    enemy_location = find_champion_location(ENEMY_HEALTH_BAR_COLOR, HEALTH_TICK_COLOR)
    if enemy_location:
        # Move to enemy
        click_percent_relative(enemy_location[0], enemy_location[1], 0, 0, "right")
        # Use spells and items
        keyboard.send(_keybinds.get("spell_1"))
        keyboard.send(_keybinds.get("spell_2"))
        keyboard.send(_keybinds.get("spell_3"))
        keyboard.send(_keybinds.get("spell_4"))
        keyboard.send(_keybinds.get("item_1"))
        keyboard.send(_keybinds.get("item_2"))
        keyboard.send(_keybinds.get("item_3"))
        keyboard.send(_keybinds.get("item_4"))
        keyboard.send(_keybinds.get("item_5"))
        keyboard.send(_keybinds.get("item_6"))
        move_random_offset(*enemy_location, 15)
        sleep_random(0.1, 0.3)
    else:
        # Move to ally
        move_to_ally(1)
        sleep_random(0, 0.5)

# ===========================
# Main Bot Loop
# ===========================

def run_arena_bot():
    """
    Main loop for Arena bot:
    - Waits for GameStart event before starting main loop
    - Runs shop phase when the active player's level increases (phase change)
    - Otherwise runs combat phase
    """
    polling_thread = threading.Thread(target=poll_game_data, args=(_latest_game_data,), daemon=True)
    polling_thread.start()

    # Wait for GameStart event before starting main loop
    logging.info("Waiting for GameStart event...")
    while True:
        game_data = _latest_game_data.get('data')
        if game_data:
            events = game_data.get("events", {}).get("Events", [])
            if any(e.get("EventName", "").lower() == "gamestart" for e in events):
                logging.info("GameStart detected. Starting main loop.")
                break

    # Main Loop
    prev_level = 0
    while True:
        game_data = _latest_game_data.get('data')
        current_level = game_data["activePlayer"].get("level") if game_data else None

        # Run shop phase if level has increased and both are regular
        if current_level is not None and current_level > prev_level:
            time.sleep(3)
            for _ in range(current_level - prev_level):
                shop_phase()

        # Update the level tracker according to successful API data
        prev_level = current_level if current_level is not None else prev_level

        combat_phase()


# ===========================
if __name__ == "__main__":
    logging.info("Arena bot started.")
    run_arena_bot()



