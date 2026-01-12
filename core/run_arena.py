
""" 
Arena Mode Automation Script

Compatibility: Arena

Setup: Optionally set preferred champion in settings
"""

import time
import threading
import logging
from core.constants import SCREEN_CENTER
from core.live_client_manager import LiveClientManager
from core.screen_manager import ScreenManager
from utils.config_utils import load_settings
from utils.cv_utils import find_arena_exit_location_template, find_augment_location_template, find_enemy_locations, find_player_location
from utils.game_utils import (
    attack_enemy,
    buy_items_list,
    buy_recommended_items,
    get_game_distance,
    is_game_ended,
    is_game_started,
    level_up_abilities,
    move_random_offset,
    pan_to_ally,
    vote_surrender,
)
from utils.general_utils import click_percent, move_mouse_percent, send_keybind


# ===========================
# Main Bot Loop
# ===========================

def run_game_loop(stop_event):
    """
    Main loop called by the connector
    """

    # Initialization
    game_data_lock = threading.Lock()
    latest_game_data = {}
    live_client_manager = LiveClientManager(stop_event, game_data_lock)
    live_client_manager.start_polling_thread(latest_game_data)

    screen_manager = ScreenManager()
    screen_manager.start_camera(target_fps=60)

    # Wait for game start
    while True:
        if stop_event.is_set(): 
            return
        if is_game_started(latest_game_data) == True:
            break
        time.sleep(1)

    logging.info("Game loop has started.")
    _keybinds, _general = load_settings()
    attack_range = latest_game_data["activePlayer"]["championStats"]["attackRange"]
    target_ally_number = 1
    prev_level = 0
    prev_gold = 0
    start_time = time.time()
    time.sleep(5)

    # Main game loop
    while True:
        # Fetch data
        with game_data_lock:
            current_level = latest_game_data["activePlayer"]["level"]
            gold = latest_game_data["activePlayer"]["currentGold"]
            game_ended = is_game_ended(latest_game_data)

        # Exits loop on game_ended or shutdown
        exit_button = find_arena_exit_location_template(screen_manager.get_latest_frame())
        if exit_button:
            click_percent(exit_button[0], exit_button[1])
            game_ended = True
        if game_ended or stop_event.is_set():
            live_client_manager.stop_polling_thread()
            screen_manager.stop_camera()
            logging.info("Game loop has ended.")

            elapsed = int(time.time() - start_time)
            hrs = elapsed // 3600
            mins = (elapsed % 3600) // 60
            secs = elapsed % 60
            logging.info("Game loop duration: %02d:%02d:%02d", hrs, mins, secs)
            return


        # Shop phase triggered on level up or by gold increase of >=500g
        if gold > prev_gold + 500 or current_level > prev_level:
            time.sleep(5)
            end_time = 20 + time.monotonic()
            while not game_ended and not stop_event.is_set():
                augment = find_augment_location_template(screen_manager.get_latest_frame())
                if augment:
                    click_percent(augment[0], augment[1])
                if buy_recommended_items(screen_manager) == True:
                    break
                elif time.monotonic() > end_time:
                    break
                time.sleep(1)
            if current_level > prev_level:
                level_up_abilities()
                prev_level = current_level
            time.sleep(2)
            augment = find_augment_location_template(screen_manager.get_latest_frame())
            if augment:
                click_percent(augment[0], augment[1])
            prev_gold = gold
            vote_surrender()
        
            
        # Combat phase
        enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
        if enemy_locations:
            send_keybind("evtCameraSnap", _keybinds, press_time=0.2)
            enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
            player_location = find_player_location(screen_manager.get_latest_frame())
            if player_location:
                for enemy_location in enemy_locations: 
                    if attack_enemy(player_location, enemy_location, attack_range) == True:
                        break
        else:
            # Move to ally
            pan_to_ally(target_ally_number, press_time=0.2)
            move_random_offset(SCREEN_CENTER, 15)
            send_keybind("evtPlayerAttackMoveClick", _keybinds)
            time.sleep(0.2)