import keyboard
import time
import logging
import requests
import random
import math
from core.constants import DATA_DRAGON_DEFAULT_LOCALE, DATA_DRAGON_VERSIONS_URL, SCREEN_HEIGHT, SCREEN_WIDTH, GAME_DISTANCE_PARAMS
from utils.config_utils import load_settings
from utils.cv_utils import find_shop_location, find_player_location, find_shop_location_template
from utils.general_utils import click_percent, send_keybind, move_mouse_percent
_keybinds, _general = load_settings()


# ===========================
# Data Dragon Utilities
# ===========================


def fetch_data_dragon_data(endpoint, version=None, locale=DATA_DRAGON_DEFAULT_LOCALE):
    """
    Fetches static data from Riot Data Dragon.
    Args:
        endpoint (str): The endpoint, e.g. "champion".
        version (str, optional): Patch version. If None, fetches latest.
        locale (str): Language code, default from constants.
    Returns:
        dict: The JSON data from Data Dragon, or {} on failure.
    """
    try:
        if not version:
            versions = requests.get(DATA_DRAGON_VERSIONS_URL, timeout=5).json()
            version = versions[0]
        url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/{locale}/{endpoint}.json"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error(f"Failed to fetch Data Dragon data for endpoint '{endpoint}': {e}")
        return {}


def get_champions_map():
    """
    Fetches champion data from Riot Data Dragon and returns a {id: name} mapping.
    Returns:
        dict: {champion_id: champion_name}
    """
    data = fetch_data_dragon_data("champion")
    champions_map = {}
    for champ in data.get("data", {}).values():
        try:
            cid = int(champ.get("key"))
        except Exception:
            continue
        champions_map[cid] = champ.get("name")
    return champions_map


# ===========================
# Game Data Utilities
# ===========================


def is_game_started(game_data):
    """
    Returns (bool):
        True if the GameStart event is present in live client data.
    """
    if not game_data:
        return False
    events = game_data.get("events", {}).get("Events", [])
    for event in events:
        if event.get("EventName") == "GameStart":
            return True
    return False


def is_game_ended(game_data):
    """
    Checks if the game has ended based on live client data. Does not lock the game data.
    Returns (bool):
        True if the GameEnd event is present in live client data or there is no more game data.
    
    """
    if not game_data:
        return True
    events = game_data["events"]["Events"]
    for event in events:
        if event["EventName"] == "GameEnd":
            return True
    return False


def log_game_data(game_data):
    """
    Logs key game data for debugging purposes.
    Args:
        game_data (dict): Live client game data.
    """
    if not game_data:
        logging.info("No game data available.")
        return

    def _format_obj(obj, indent=0):
        pad = '  ' * indent
        if isinstance(obj, dict):
            lines = []
            for k, v in obj.items():
                lines.append(f"{pad}{k}: {_format_obj(v, indent+1)}")
            return "\n".join(lines)
        if isinstance(obj, list):
            lines = []
            for i, item in enumerate(obj):
                lines.append(f"{pad}- {_format_obj(item, indent+1)}")
            return "\n".join(lines)
        return str(obj)
    
    current_hp = game_data["activePlayer"]["championStats"]["currentHealth"]
    max_hp = game_data["activePlayer"]["championStats"]["maxHealth"]
    current_level = game_data["activePlayer"]["level"]
    events = game_data.get("events", {})

    logging.info(f"Player Level: {current_level}")
    logging.info(f"Current HP: {current_hp} / {max_hp}")

    try:
        logging.info("Events:\n%s", _format_obj(events))
    except Exception:
        logging.exception("Failed formatting events; logging raw repr.")
        logging.info("Events: %s", repr(events))


# ===========================
# Helper Utilities
# ===========================

def sleep_random(min_seconds, max_seconds):
    """
    Sleeps for a random duration between min_seconds and max_seconds.
    Args:
        min_seconds (float): Minimum sleep time in seconds.
        max_seconds (float): Maximum sleep time in seconds.
    """
    duration = random.uniform(min_seconds, max_seconds)
    time.sleep(duration)


def get_pixel_distance(coord1, coord2):
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


def get_game_distance(coord1, coord2):
    """Estimate in-game distance (units) between two screen coordinates.

    Uses hardcoded anisotropic parameters and bias (no config lookups).
    Returns a single float: estimated game units.
    """

    px, py = float(coord1[0]), float(coord1[1])
    tx, ty = float(coord2[0]), float(coord2[1])

    unit_scale = GAME_DISTANCE_PARAMS["unit_scale"]
    vertical_factor_top = GAME_DISTANCE_PARAMS["v_top"]
    vertical_factor_bottom = GAME_DISTANCE_PARAMS["v_bottom"]
    wiggle_coeff = GAME_DISTANCE_PARAMS.get("wiggle_coeff", 0.0)

    dx = px - tx
    dy = py - ty
    pixel_dist = math.hypot(dx, dy)
    if pixel_dist == 0:
        return 0.0

    # Determine normalized player Y position in [-1,1].
    # Use the player's screen Y (coord1) only: -1 = top, +1 = bottom.
    norm_y = (py - (SCREEN_HEIGHT / 2.0)) / (SCREEN_HEIGHT / 2.0)
    norm_y = max(-1.0, min(1.0, norm_y))

    # Interpolate vertical factor smoothly between top and bottom using player Y.
    t = (norm_y + 1.0) / 2.0
    v = vertical_factor_top * (1.0 - t) + vertical_factor_bottom * t

    # small cubic 'wiggle' to soften the curve
    wiggle = wiggle_coeff * (norm_y ** 3)

    # Position-based multiplier: interpolate top->bottom (v already interpolated)
    # so top (v negative) reduces multiplier and bottom (v positive) increases it.
    pos_multiplier = 1.0 + v + wiggle
    pos_multiplier = max(GAME_DISTANCE_PARAMS["pos_multiplier_min"], pos_multiplier)

    # Separation-based correction: boost distance when separation is mostly vertical.
    # sep_ratio = abs(dy) / pixel_dist  (0..1)
    # sep_multiplier = 1 + k * sep_ratio
    # Clamp to avoid runaway scaling.
    k_sep = GAME_DISTANCE_PARAMS["k_sep"]
    max_sep_mult = GAME_DISTANCE_PARAMS["max_sep_mult"]
    sep_ratio = abs(dy) / pixel_dist
    sep_multiplier = 1.0 + (k_sep * sep_ratio)
    sep_multiplier = min(max_sep_mult, sep_multiplier)

    units = pixel_dist * unit_scale * pos_multiplier * sep_multiplier
    return float(units)

# ===========================
# Game Control Utilities
# ===========================

def move_random_offset(coord, max_offset=15):
    """
    Moves a random distance offset from the given coordinate using percent-based relative click.

    Args:
        coord (tuple): (x, y) coordinate of the base location.
        max_offset (int): Maximum percent screen distance in any direction.
    """
    x, y = int(coord[0]), int(coord[1])
    offset_x = random.randint(-max_offset, max_offset)  # percent offset
    offset_y = random.randint(-max_offset, max_offset)  # percent offset
    click_percent(x, y, offset_x, offset_y, "right")
    time.sleep(0.1)


def level_up_abilities(order=('R', 'Q', 'W', 'E')):
    """
    Levels up all abilities in the specified order.
    Always levels 'R' first by default.
    Args:
        order (tuple): The order in which to level up spells. Default is ('R', 'Q', 'W', 'E').
    """
    event_map = {
        'Q': 'evtLevelSpell1',
        'W': 'evtLevelSpell2',
        'E': 'evtLevelSpell3',
        'R': 'evtLevelSpell4',
    }
    for key in order:
        k = key.upper()
        evt = event_map.get(k)
        if not evt:
            logging.error(f"Invalid key parameter: {k}. Must be Q, W, E, or R.")
            continue
        send_keybind(evt, _keybinds)


def level_up_ability(ability='R'):
    """
    Levels up a single ability.
    Always levels 'R' first by default.
    Args:
        ability (char): The ability to level up. Default is 'R'.
    """
    event_map = {
        'Q': 'evtLevelSpell1',
        'W': 'evtLevelSpell2',
        'E': 'evtLevelSpell3',
        'R': 'evtLevelSpell4',
    }
    k = ability.upper()
    evt = event_map.get(k)
    if not evt:
        logging.error(f"Invalid ability parameter: {ability}. Must be Q, W, E, or R.")
        return
    send_keybind(evt, _keybinds)


def buy_recommended_items(screen_manager):
    """
    Finds the shop location and performs recommended item purchases.
    Opens the shop if not already open.
    Returns true if shop was successfully opened and also closed after purchase.
    Args:
        screen_manager (ScreenManager): The screen manager instance.
    NOTE:
        Augment popups will automatically close the shop and also nullify interaction with it.
    """
    shop_location = find_shop_location_template(screen_manager.get_latest_frame())
    
    # Open shop if not already open
    if not shop_location:
        send_keybind("evtOpenShop", _keybinds)
        time.sleep(0.5)
        shop_location = find_shop_location_template(screen_manager.get_latest_frame())
        if not shop_location:
            send_keybind("evtOpenShop", _keybinds)
            time.sleep(0.5)
            return False

    # Shop found, now buy items
    x, y = shop_location[:2]
    click_percent(x, y, 0, -64, "left")
    time.sleep(0.5)
    click_percent(x, y, 15, -25, "right")
    click_percent(x, y, 15, -25, "right")
    time.sleep(0.5)

    # Ensure shop is closed
    send_keybind("evtOpenShop", _keybinds)
    time.sleep(0.5)
    if find_shop_location_template(screen_manager.get_latest_frame()):
        return False
    return True


def buy_items_list(screen_manager, item_list):
    """
    Buys a list of items by opening the shop, searching for each item, and attempting to buy it.
    Args:
        item_names (list of str): List of item names to buy.
    NOTE: Shop CANNOT be obstructed (by augment popups or other UI elements) or else chat will be opened instead.
    """
    shop_location = find_shop_location(screen_manager.get_latest_frame())
        
    # Open shop if not already open
    if not shop_location:
        send_keybind("evtOpenShop", _keybinds)
        time.sleep(0.5)
        shop_location = find_shop_location(screen_manager.get_latest_frame())
        if not shop_location:
            time.sleep(0.5)
            send_keybind("evtOpenShop", _keybinds)
            return False

    # Shop found, now buy items
    for item in item_list:
        send_keybind("evtShopFocusSearch", _keybinds)
        time.sleep(0.5)
        keyboard.write(item)
        time.sleep(0.5)
        keyboard.send("enter")
        time.sleep(0.5)

    # Ensure shop is closed
    send_keybind("evtOpenShop", _keybinds)
    time.sleep(0.5)
    if find_shop_location(screen_manager.get_latest_frame()):
        return False
    return True


def pan_to_ally(ally_number=1, press_time=0.01):
    """
    Pans camera to the specified ally and moves cursor to their location.
    Args:
        ally_number (int): The ally number to select (e.g., 1, 2, 3, 4).
        press_time (float): Duration to hold the key press. Default is 0.01 seconds.
    """
    if ally_number == 1:
        send_keybind("evtSelectAlly1", _keybinds, press_time=press_time)
    elif ally_number == 2:
        send_keybind("evtSelectAlly2", _keybinds, press_time=press_time)
    elif ally_number == 3:
        send_keybind("evtSelectAlly3", _keybinds, press_time=press_time)
    elif ally_number == 4:
        send_keybind("evtSelectAlly4", _keybinds, press_time=press_time)
    else:
        logging.error(f"Invalid ally number: {ally_number}. Must be 1, 2, 3, or 4.")
    

def retreat(current_coords, threat_coords):
    """
    Moves the player away from the threat location by a distance proportional to the
    current separation multiplied by `retreat_distance_modifier`.

    Args:
        current_coords (tuple): Current (x, y) coordinates of the player.
        threat_coords (tuple): (x, y) coordinates of the threat/enemy.
        retreat_distance_modifier (float): Multiplier applied to the current distance
            between player and threat to compute how far to move away. For example,
            a value of 1.2 will move to 120% of the current separation in the
            opposite direction. (Default: 1.0)
    """
    length = get_game_distance(current_coords, threat_coords)
    if length == 0:
        logging.error("Cannot retreat: current coordinates are the same as threat coordinates.")
        return

    dx = float(current_coords[0]) - float(threat_coords[0])
    dy = float(current_coords[1]) - float(threat_coords[1])

    # Unit direction away from threat
    vec_len = math.hypot(dx, dy)
    if vec_len == 0:
        logging.error("Cannot retreat: zero-length direction vector.")
        return
    ux = dx / vec_len
    uy = dy / vec_len

    # Screen-inset bounds (pixels) - final click will be at most this far along the ray
    margin = 50
    min_x = margin
    max_x = SCREEN_WIDTH - margin
    min_y = margin
    max_y = SCREEN_HEIGHT - margin

    cx = float(current_coords[0])
    cy = float(current_coords[1])

    # Compute t values where the ray (cx,cy) + t*(ux,uy) intersects the four inset boundaries
    t_candidates = []
    eps = 1e-8
    if abs(ux) > eps:
        if ux > 0:
            t_candidates.append((max_x - cx) / ux)
        else:
            t_candidates.append((min_x - cx) / ux)
    if abs(uy) > eps:
        if uy > 0:
            t_candidates.append((max_y - cy) / uy)
        else:
            t_candidates.append((min_y - cy) / uy)

    # Keep only positive intersection distances
    t_pos = [t for t in t_candidates if t > 0]
    if not t_pos:
        logging.error("Retreat direction does not intersect screen bounds; aborting retreat.")
        return

    # First intersection is where the ray exits the inset rectangle; that's the farthest valid point
    t_hit = min(t_pos)

    click_x = int(round(cx + ux * t_hit))
    click_y = int(round(cy + uy * t_hit))

    # Clamp to be safe
    click_x = max(min_x, min(max_x, click_x))
    click_y = max(min_y, min(max_y, click_y))

    click_percent(click_x, click_y, 0, 0, "right")
    send_keybind("evtSelfCastAvatarSpell1", _keybinds)
    send_keybind("evtSelfCastAvatarSpell2", _keybinds)
    time.sleep(0.5)


def tether_offset(player_coords, target_coords, tether_distance):
    """Move player to be at `tether_distance` (in game units) from target_coords.

    Simplified: computes the pixel vector for the requested tether distance
    using hardcoded anisotropic parameters. `tether_distance` must be provided.
    """

    px, py = float(player_coords[0]), float(player_coords[1])
    tx, ty = float(target_coords[0]), float(target_coords[1])

    # Use the same player-Y based position multiplier and separation-based
    # correction as `get_game_distance`, then invert to find required pixel
    # offset for the requested `tether_distance`.
    vertical_factor_top = GAME_DISTANCE_PARAMS["v_top"]
    vertical_factor_bottom = GAME_DISTANCE_PARAMS["v_bottom"]
    wiggle_coeff = GAME_DISTANCE_PARAMS.get("wiggle_coeff", 0.0)
    unit_scale = GAME_DISTANCE_PARAMS["unit_scale"]

    dx = px - tx
    dy = py - ty
    pixel_dist = math.hypot(dx, dy)
    if pixel_dist == 0:
        return

    # player Y based multiplier
    norm_y = (py - (SCREEN_HEIGHT / 2.0)) / (SCREEN_HEIGHT / 2.0)
    norm_y = max(-1.0, min(1.0, norm_y))
    t = (norm_y + 1.0) / 2.0
    v = vertical_factor_top * (1.0 - t) + vertical_factor_bottom * t
    wiggle = wiggle_coeff * (norm_y ** 3)
    pos_multiplier = 1.0 + v + wiggle
    pos_multiplier = max(GAME_DISTANCE_PARAMS["pos_multiplier_min"], pos_multiplier)

    # separation-based correction (based on current orientation)
    k_sep = GAME_DISTANCE_PARAMS["k_sep"]
    max_sep_mult = GAME_DISTANCE_PARAMS["max_sep_mult"]
    sep_ratio = abs(dy) / pixel_dist
    sep_multiplier = 1.0 + (k_sep * sep_ratio)
    sep_multiplier = min(max_sep_mult, sep_multiplier)

    # desired pixel distance from the target along the direction to player
    pixel_needed = float(tether_distance) / (unit_scale * pos_multiplier * sep_multiplier)
    if not math.isfinite(pixel_needed) or pixel_needed <= 0:
        return

    theta = math.atan2(py - ty, px - tx)
    ux = math.cos(theta)
    uy = math.sin(theta)
    pv = (pixel_needed * ux, pixel_needed * uy)

    click_x = int(tx + pv[0])
    click_y = int(ty + pv[1])
    click_percent(click_x, click_y, 0, 0, "right")

    # Estimate how long the player will take to move to the final position
    current_game_distance = get_game_distance((px, py), (tx, ty))
    travel_distance = float(tether_distance)
    travel_units = abs(current_game_distance - travel_distance)
    # player average speed in game units per second
    player_speed = 350.0
    # base duration (seconds) plus small safety margin
    duration = travel_units / player_speed
    # clamp reasonable bounds so we don't sleep too little or too long
    duration = max(0.05, min(duration, 0.5))
    time.sleep(duration)
    return


def attack_enemy(player_location, enemy_location, attack_range=550):
    """
    Attacks the enemy according to the champion's strengths.
    Args:
        player_location (tuple): (x, y) coordinates of the player.
        enemy_location (tuple): (x, y) coordinates of the enemy.
        attack_range (int): The champion's attack range in game units.
    Returns:
        bool: True if enemy in range was attacked, False otherwise.
    """
    
    distance_to_enemy = get_game_distance(player_location, enemy_location)

    # Ranged champions are considered 350+ range, otherwise melee
    if attack_range > 350:
        if distance_to_enemy < 200:
            retreat(player_location, enemy_location)
        elif distance_to_enemy > attack_range:
            return False
        else:
            tether_offset(player_location, enemy_location, attack_range)
            move_mouse_percent(enemy_location[0], enemy_location[1])
    else:
        if distance_to_enemy > attack_range + 400:
            return False
        # Flash range engage
        elif distance_to_enemy <= attack_range + 400 and distance_to_enemy > attack_range + 350:
            move_mouse_percent(enemy_location[0], enemy_location[1])
            send_keybind("evtPlayerAttackMoveClick", _keybinds)
            send_keybind("evtSelfCastAvatarSpell1", _keybinds)
            send_keybind("evtSelfCastAvatarSpell2", _keybinds)
            send_keybind("evtCastSpell4", _keybinds)
            send_keybind("evtCastSpell1", _keybinds)
            send_keybind("evtCastSpell2", _keybinds)
            send_keybind("evtCastSpell3", _keybinds)
            time.sleep(0.2)
            send_keybind("evtCastSpell4", _keybinds)
            send_keybind("evtCastSpell1", _keybinds)
            send_keybind("evtCastSpell2", _keybinds)
            send_keybind("evtCastSpell3", _keybinds)
            return True
    move_mouse_percent(enemy_location[0], enemy_location[1])
    spell = random.choice(['evtCastSpell1', 'evtCastSpell2', 'evtCastSpell3', 'evtCastSpell4'])
    send_keybind(spell, _keybinds)
    send_keybind("evtUseItem1", _keybinds)
    send_keybind("evtUseItem2", _keybinds)
    send_keybind("evtUseItem3", _keybinds)
    send_keybind("evtUseItem4", _keybinds)
    send_keybind("evtUseItem5", _keybinds)
    send_keybind("evtUseItem6", _keybinds)
    if distance_to_enemy <= attack_range + 100:
        send_keybind("evtPlayerAttackMoveClick", _keybinds)
        time.sleep(0.25)
    
    return True


def vote_surrender():
    """
    Votes to surrender by typing the surrender command in chat.
    Only proceeds if 'surrender' is set to True in the config.
    """
    if not _general.get("surrender", False):
        return

    time.sleep(1)
    keyboard.send("enter")
    time.sleep(0.5)
    keyboard.write("/ff")
    time.sleep(1)
    keyboard.send("enter")
    time.sleep(0.5)


