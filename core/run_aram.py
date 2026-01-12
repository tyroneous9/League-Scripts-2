""" 
ARAM Mode Automation Script

Compatibility: ARAM, ARAM Mayhem

Setup: No special setup required
"""


import time
import threading
import logging
from core.constants import AFK_TIMEOUT, SCREEN_CENTER
from core.live_client_manager import LiveClientManager
from core.screen_manager import ScreenManager
from utils.config_utils import load_settings
from utils.general_utils import click_percent, move_mouse_percent, send_keybind, send_keybind
from utils.game_utils import (
    attack_enemy,
    buy_recommended_items,
    is_game_ended,
    is_game_started,
    move_random_offset,
    pan_to_ally,
    level_up_abilities,
    tether_offset,
    vote_surrender,
)
from utils.cv_utils import find_ally_locations, find_augment_location_template, find_enemy_locations, find_player_location

# ===========================
# Main Bot Loop
# ===========================

def run_game_loop(stop_event):
    """
    Main loop called by the connector
    """

    # Telemetry initialization
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

    # Game start initialization
    logging.info("Game loop has started")
    _keybinds, _general = load_settings()
    attack_range = latest_game_data["activePlayer"]["championStats"]["attackRange"]
    ally_priority_list = [1,2,3,4] # Adaptive order to follow most active allies
    prev_level = 0
    start_time = time.time()
    last_afk_check_time = time.time()
    time.sleep(5)

    # Main game loop
    while True:
        # Fetch data
        with game_data_lock:
            game_ended = is_game_ended(latest_game_data)
            current_level = latest_game_data["activePlayer"]["level"]
            current_hp = latest_game_data["activePlayer"]["championStats"]["currentHealth"]
            max_hp = latest_game_data["activePlayer"]["championStats"]["maxHealth"]

        # Exits loop on game end or shutdown
        if game_ended or stop_event.is_set():
            live_client_manager.stop_polling_thread()
            screen_manager.stop_camera()
            elapsed = int(time.time() - start_time)
            hrs = elapsed // 3600
            mins = (elapsed % 3600) // 60
            secs = elapsed % 60
            logging.info("Game loop duration: %02d:%02d:%02d", hrs, mins, secs)
            return

        # Check for AFK frequently to prevent following an AFK ally. This timer is also reset when enemies are detected.
        if time.time() - last_afk_check_time >= 20:
            ally_priority_list.append(ally_priority_list.pop(0))
            last_afk_check_time = time.time()

        # Check for augment
        augment = find_augment_location_template(screen_manager.get_latest_frame())
        if augment:
            click_percent(augment[0], augment[1])
            time.sleep(0.5)
            buy_recommended_items(screen_manager)
            time.sleep(0.5)

        # Level up
        if current_level > prev_level:
            level_up_abilities()
            prev_level = current_level

        # Shop if dead, continue otherwise
        if current_hp == 0:
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
            vote_surrender()
            continue

        # Combat phase
        ally_locations = find_ally_locations(screen_manager.get_latest_frame())
        enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())

        if ally_locations and enemy_locations: #TT
            last_afk_check_time = time.time()
            # move around ally
            move_random_offset(ally_locations[0], 5)
            time.sleep(0.2)
            # fight enemy
            send_keybind("evtCameraSnap", _keybinds, press_time=0.2)
            enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
            player_location = find_player_location(screen_manager.get_latest_frame())
            if player_location:
                for enemy_location in enemy_locations:
                    if attack_enemy(player_location, enemy_location, attack_range) == True:
                        break
            

        elif ally_locations and not enemy_locations: #TF
            # follow the most active ally
            pan_to_ally(ally_priority_list[0], press_time=0.2)
            move_random_offset(SCREEN_CENTER, 10)
            send_keybind("evtPlayerAttackMoveClick", _keybinds)


        elif not ally_locations and enemy_locations: #FT
            # kite away from enemy, and fight if too close
            send_keybind("evtCameraSnap", _keybinds, press_time=0.2)
            enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
            player_location = find_player_location(screen_manager.get_latest_frame())
            if player_location:
                for enemy_location in enemy_locations:
                    tether_offset(player_location, enemy_location, 1000)
                    break
            

        else: #FF
            # look for current ally (highest-priority is at front)
            pan_to_ally(ally_priority_list[0], press_time=0.2)
            move_mouse_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
            # not found, try other allies — move found ally to front for faster future hits
            if not find_ally_locations(screen_manager.get_latest_frame()):
                n = len(ally_priority_list)
                # probe remaining allies in order after the front
                for offset in range(1, n):
                    i = offset
                    ally = ally_priority_list[i]
                    pan_to_ally(ally, press_time=0.3)
                    if find_ally_locations(screen_manager.get_latest_frame()):
                        ally_priority_list.insert(0, ally_priority_list.pop(i))
                        break
        
        time.sleep(0.01) 
        