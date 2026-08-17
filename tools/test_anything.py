
import logging
import os
import sys

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import time
import keyboard
from core.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from core.screen_manager import ScreenManager
from utils.cv_utils import find_arena_exit_location, find_arena_exit_location_template, find_attached_ally_location, find_augment_location_template, find_enemy_locations, find_player_location, find_shop_location, find_shop_location_template, load_template_cache
from utils.game_utils import get_game_distance, tether_offset
from utils.general_utils import move_mouse_percent

screen_manager = ScreenManager()
screen_manager.start_camera()

while True:
    keyboard.wait('v')
    img = screen_manager.get_latest_frame()
    load_template_cache()
    # player_location = find_player_location(img)
    # enemy_locations = find_enemy_locations(img)
    # if player_location and enemy_locations:
    #     enemy = enemy_locations[0]

    # element = find_arena_exit_location(screen_manager.get_latest_frame())
    # if element:
    #     move_mouse_percent(element[0], element[1])

    test = find_shop_location_template(img)
    if test:
        move_mouse_percent(test[0], test[1])

    
    time.sleep(0.5)