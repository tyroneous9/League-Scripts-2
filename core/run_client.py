import time
import threading
import random
import subprocess
import keyboard
import os
import requests
from lcu_driver import Connector
from config_utils import load_config, disable_insecure_request_warning
from constants import LCU_CHAMP_SELECT_SESSION, LCU_MATCHMAKING_READY_CHECK, LCU_GAMEFLOW_PHASE, LIVE_CLIENT_URL, DEFAULT_API_TIMEOUT, SUPPORTED_MODES
from utils import get_league_window, click_percent, listen_for_exit_key

disable_insecure_request_warning()

# Data
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

# Threads
def start_queue_loop():
    while True:
        hwnd = get_league_window()
        click_percent(hwnd, 40, 95)
        time.sleep(5)

def check_game_start():
    global check_game_thread_running
    if check_game_thread_running:
        return
    check_game_thread_running = True
    print("[INFO] Waiting for game to start...")
    while True:
        try:
            res = requests.get(f"{LIVE_CLIENT_URL}/allgamedata", timeout=DEFAULT_API_TIMEOUT, verify=False)
            if res.status_code == 200:
                print("[INFO] Game detected. Launching bot...")
                try:
                    config = load_config()
                    mode = config.get("General", {}).get("mode", "").lower()
                    if mode in SUPPORTED_MODES:
                        subprocess.run(SUPPORTED_MODES[mode])
                    else:
                        print(f"[ABORTED] Game detected but mode '{mode}' is not supported. No bot launched.")
                except Exception as e:
                    print(f"[ERROR] Failed to launch bot: {e}")
                break
        except:
            pass
        time.sleep(2)
    check_game_thread_running = False

# Event listeners
@connector.ready
async def connect(connection):
    global summoner_id, champions_map
    print("Connected to League Client, starting queue.")

    # Start threads
    threading.Thread(target=listen_for_exit_key, daemon=True).start()
    threading.Thread(target=check_game_start, daemon=True).start()
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
                        print("[ERROR] No champions found in champion map. Skipping pick.")
                        return

                    valid_champ_ids = [cid for cid in champions_map.values() if cid != -1]
                    if not valid_champ_ids:
                        print("[ERROR] No valid champion IDs available.")
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
                    print(f"[INFO] Champion picked: {champ_name} (ID: {champ_id})")
                    return
    elif phase not in ('BAN_PICK'):
        picked_champion = False  # Reset flag when not in pick phase

@connector.ws.register(LCU_MATCHMAKING_READY_CHECK, event_types=('UPDATE',))
async def on_ready_check(connection, event):
    global in_ready_check
    if event.data.get('state') == 'InProgress' and event.data.get('playerResponse') == 'None':
        if not in_ready_check:
            await connection.request('post', '/lol-matchmaking/v1/ready-check/accept')
            print("[INFO] Accepted ready check.")
            in_ready_check = True
    elif event.data.get('state') != 'InProgress':
        in_ready_check = False  # Reset flag when not in ready check

@connector.ws.register(LCU_GAMEFLOW_PHASE, event_types=('UPDATE',))
async def on_game_launch(connection, event):
    global game_started
    if event.data == "InProgress":
        if not game_started:
            threading.Thread(target=check_game_start, daemon=True).start()
            game_started = True
    else:
        game_started = False  # Reset flag when not in game

@connector.close
async def disconnect(_):
    print("League Client has been closed.")

# Start the connector
if __name__ == "__main__":
    connector.start()
