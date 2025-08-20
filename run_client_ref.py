# ==========================================================
# League Client Automation Script
# ==========================================================

import logging
import time
import threading
import random
import subprocess
import requests
from lcu_driver import Connector
from config_utils import load_config, disable_insecure_request_warning
from constants import (
    LCU_CHAMP_SELECT_SESSION, LCU_MATCHMAKING_READY_CHECK, LCU_GAMEFLOW_PHASE,
    LIVE_CLIENT_URL, DEFAULT_API_TIMEOUT, SUPPORTED_MODES,
    LEAGUE_CLIENT_WINDOW_TITLE
)
from general_utils import click_percent_absolute
import win32gui
import win32con
from logging_config import setup_logging

# Setup logging
setup_logging()

# ===========================
# Initialization
# ===========================

disable_insecure_request_warning()

# State variables
should_click = True
in_champ_select = False
in_ready_check = False
in_game = False
connector = Connector()
champions_map = {}
summoner_id = None
picked_champion = False
game_started = False
check_game_thread_running = False

# ===========================
# Threaded Actions
# ===========================

def bring_client_to_front():
    """
    Brings the League Client window to the foreground.
    """
    hwnd = win32gui.FindWindow(None, LEAGUE_CLIENT_WINDOW_TITLE)
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.2)
    else:
        logging.warning(f"{LEAGUE_CLIENT_WINDOW_TITLE} window not found.")

def start_queue_loop():
    """
    Periodically brings the client to the front and clicks the queue button.
    """
    while True:
        bring_client_to_front()
        click_percent_absolute(40, 95)
        time.sleep(5)

def check_game_start():
    """
    Polls for game start, brings client to front, and launches the appropriate bot script.
    """
    global check_game_thread_running
    if check_game_thread_running:
        return
    check_game_thread_running = True
    logging.info("Waiting for game to start...")
    while True:
        try:
            res = requests.get(f"{LIVE_CLIENT_URL}/allgamedata", timeout=DEFAULT_API_TIMEOUT, verify=False)
            if res.status_code == 200:
                bring_client_to_front()
                logging.info("Game detected. Launching bot...")
                try:
                    config = load_config()
                    mode = config.get("General", {}).get("selected_game_mode", "").lower()
                    if mode in SUPPORTED_MODES:
                        subprocess.run(SUPPORTED_MODES[mode])
                    else:
                        logging.warning(f"Game detected but mode '{mode}' is not supported. No bot launched.")
                except Exception as e:
                    logging.error(f"Failed to launch bot: {e}")
                break
        except:
            pass
        time.sleep(2)
    check_game_thread_running = False

# ===========================
# LCU Event Listeners
# ===========================

@connector.ready
async def connect(connection):
    """
    Called when the connector is ready.
    Starts threads and fetches summoner/champion data.
    """
    global summoner_id, champions_map
    logging.info("Connected to League Client, waiting for window...")

    hwnd = None
    for _ in range(60):  # Timeout for client window
        hwnd = win32gui.FindWindow(None, LEAGUE_CLIENT_WINDOW_TITLE)
        if hwnd and win32gui.IsWindow(hwnd):
            break
        logging.info("League client window not found, retrying...")
        time.sleep(1)
    if not hwnd:
        logging.error("League client window not available. Aborting automation.")
        return

    bring_client_to_front()

    # Start queue
    threading.Thread(target=start_queue_loop, daemon=True).start()

    # Fetch summoner ID
    summoner = await connection.request('get', '/lol-summoner/v1/current-summoner')
    summoner_to_json = await summoner.json()
    summoner_id = summoner_to_json['summonerId']

    # Fetch owned champions
    temp_champions_map = {}
    champion_list = await connection.request('get', f'/lol-champions/v1/inventories/{summoner_id}/champions-minimal')
    champion_list_to_json = await champion_list.json()
    for champion in champion_list_to_json:
        temp_champions_map[champion['name']] = champion['id']
    champions_map = temp_champions_map

@connector.ws.register(LCU_CHAMP_SELECT_SESSION, event_types=('CREATE', 'UPDATE',))
async def on_champ_select(connection, event):
    """
    Handles champion selection during champ select phase.
    Picks a random owned champion if not already picked.
    """
    bring_client_to_front()
    global picked_champion
    global in_champ_select
    in_champ_select = True
    timer = event.data.get('timer', {})
    phase = timer.get('phase')
    if phase in ('BAN_PICK') and not picked_champion:
        actions = event.data.get('actions', [])
        local_cell_id = event.data.get('localPlayerCellId')

        for action_group in actions:
            for action in action_group:
                if action.get('actorCellId') == local_cell_id and action.get('type') == 'pick' and action.get('isInProgress'):
                    action_id = action.get('id')
                    if not champions_map:
                        logging.error("No champions found in champion map. Skipping pick.")
                        return

                    valid_champ_ids = [cid for cid in champions_map.values() if cid != -1]
                    if not valid_champ_ids:
                        logging.error("No valid champion IDs available.")
                        return
                    champ_id = random.choice(valid_champ_ids)
                    
                    # Find champion name from id
                    champ_name = next((name for name, cid in champions_map.items() if cid == champ_id), "Unknown")
                    await connection.request(
                        'patch',
                        f'/lol-champ-select/v1/session/actions/{action_id}',
                        data={"championId": champ_id, "completed": True}
                    )
                    picked_champion = True
                    logging.info(f"Champion picked: {champ_name} (ID: {champ_id})")
                    return
    elif phase not in ('BAN_PICK'):
        picked_champion = False  # Reset flag when not in pick phase

@connector.ws.register(LCU_MATCHMAKING_READY_CHECK, event_types=('UPDATE',))
async def on_ready_check(connection, event):
    """
    Handles ready check popups and auto-accepts if needed.
    """
    bring_client_to_front()
    global in_ready_check
    if event.data.get('state') == 'InProgress' and event.data.get('playerResponse') == 'None':
        if not in_ready_check:
            await connection.request('post', '/lol-matchmaking/v1/ready-check/accept')
            logging.info("Accepted ready check.")
            in_ready_check = True
    elif event.data.get('state') != 'InProgress':
        in_ready_check = False  # Reset flag when not in ready check

@connector.ws.register(LCU_GAMEFLOW_PHASE, event_types=('UPDATE',))
async def on_game_launch(connection, event):
    """
    Detects when the game launches and starts the bot.
    """
    global game_started
    if event.data == "InProgress":
        if not game_started:
            threading.Thread(target=check_game_start, daemon=True).start()
            game_started = True
    else:
        game_started = False  # Reset flag when not in game

@connector.close
async def disconnect(_):
    """
    Called when the League Client closes.
    """
    logging.info("League Client has been closed.")

# ===========================
# Main Entry Point
# ===========================

if __name__ == "__main__":
    # Immediately check if the game has already started
    try:
        res = requests.get(f"{LIVE_CLIENT_URL}/allgamedata", timeout=DEFAULT_API_TIMEOUT, verify=False)
        if res.status_code == 200:
            logging.info("Game already in progress. Launching bot immediately...")
            config = load_config()
            mode = config.get("General", {}).get("selected_game_mode", "").lower()
            if mode in SUPPORTED_MODES:
                subprocess.run(SUPPORTED_MODES[mode])
            else:
                logging.warning(f"Game detected but mode '{mode}' is not supported. No bot launched.")
    except Exception as e:
        logging.error(f"Immediate game check failed: {e}")

    connector.start()
