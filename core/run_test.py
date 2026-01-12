""" 
ARAM Mode Automation Script

Compatibility: ARAM, ARAM Mayhem

Setup: No special setup required
"""


import time
import threading
import logging
from core.constants import SCREEN_CENTER
from core.live_client_manager import LiveClientManager
from core.screen_manager import ScreenManager
from utils.config_utils import load_settings
from utils.general_utils import click_percent, move_mouse_percent, send_keybind, send_keybind
from utils.game_utils import (
    attack_enemy,
    buy_items_list,
    buy_recommended_items,
    get_pixel_distance,
    is_game_ended,
    is_game_started,
    move_random_offset,
    pan_to_ally,
    level_up_abilities,
    retreat,
    tether_offset,
    vote_surrender,
)
from utils.cv_utils import find_ally_locations, find_augment_location, find_enemy_locations, find_player_location, find_test_location


    

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

    logging.info("Game loop has started")
    _keybinds, _general = load_settings()
    attack_range = latest_game_data["activePlayer"]["championStats"]["attackRange"]
    
    # Main game loop
    while True:
        # Fetch data
        with game_data_lock:
            current_level = latest_game_data["activePlayer"]["level"]
            current_hp = latest_game_data["activePlayer"]["championStats"]["currentHealth"]
            max_hp = latest_game_data["activePlayer"]["championStats"]["maxHealth"]
            game_ended = is_game_ended(latest_game_data)

        # Exits loop on game end or shutdown
        if game_ended or stop_event.is_set():
            live_client_manager.stop_polling_thread()
            screen_manager.stop_camera()
            return
        
        # enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
        # player_location = find_player_location(screen_manager.get_latest_frame())
        # if player_location:
        #     for enemy_location in enemy_locations:
        #         attack_enemy(player_location, enemy_location, attack_range)
        
        # buy_recommended_items(screen_manager)

        loc = find_test_location(screen_manager.get_latest_frame())
        if loc:
            move_mouse_percent(loc[0], loc[1])
        time.sleep(1)
