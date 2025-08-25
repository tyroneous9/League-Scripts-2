# ==========================================================
# Arena Mode Automation Script
# ==========================================================

import time
import threading
import keyboard
import logging
from core.constants import (
    HEALTH_TICK_COLOR, ENEMY_HEALTH_BAR_COLOR, SCREEN_CENTER
)
from utils.general_utils import click_percent, poll_live_client_data
from utils.game_utils import (
    load_game_settings,
    move_random_offset,
    move_to_ally,
    find_champion_location,
    buy_recommended_items,
    level_up_abilities,
    retreat_to_ally,
    sleep_random,
)

# ===========================
# Initialization
# ===========================

_keybinds, _general = load_game_settings()
_latest_game_data = {'data': None}


# ===========================
# Arena Phase Functions
# ===========================

def shop_phase():
    """
    Handles the Arena shop phase which is detected upon level up
    """
    # Click screen center in case of augment card
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])

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

    center_camera_key = _keybinds.get("center_camera")
    keyboard.press(center_camera_key)
    time.sleep(0.1)
    keyboard.release(center_camera_key)

    enemy_location = find_champion_location(ENEMY_HEALTH_BAR_COLOR, HEALTH_TICK_COLOR)
    if enemy_location:
        # Move to enemy
        click_percent(enemy_location[0], enemy_location[1], 0, 0, "right")
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
        # Self preservation
        if _latest_game_data['data']:
            current_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("currentHealth")
            max_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("maxHealth")
            hp_percent = (current_hp / max_hp)
            if hp_percent < .3:
                retreat_to_ally()
                if(hp_percent == 0):
                    return
    else:
        # Move to ally
        move_to_ally(1)
        sleep_random(0, 0.5)

# ===========================
# Main Bot Loop
# ===========================

def run_game_loop(stop_event):
    """
    Main loop for Arena bot:
    - Waits for GameStart event before starting main loop
    - Runs shop phase when the active player's level increases (phase change)
    - Otherwise runs combat phase
    - Exits when monitor_game_end detects game end
    """

    # Game initialization
    polling_thread = threading.Thread(target=poll_live_client_data, args=(_latest_game_data, stop_event), daemon=True)
    polling_thread.start()
    prev_level = 0
    logging.info("Bot has started.")

    while not stop_event.is_set():

        if _latest_game_data['data']:
            current_level = _latest_game_data['data']["activePlayer"].get("level")
            if current_level > prev_level:
                time.sleep(3)
                for _ in range(current_level - prev_level):
                    shop_phase()
                prev_level = current_level if current_level else prev_level
        else:
            logging.warning("No game data available.")

        combat_phase()

# For testing purposes
# python -m core.run_arena
if __name__ == "__main__":
    time.sleep(2)
    stop_event = threading.Event()
    run_game_loop(stop_event)
