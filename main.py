import asyncio
import threading
import time
import random
import tkinter as tk
from tkinter import ttk
from utils.config_utils import load_config, save_config, disable_insecure_request_warning
from core.constants import SUPPORTED_MODES, LCU_GAMEFLOW_PHASE, LCU_CHAMP_SELECT_SESSION, LCU_MATCHMAKING_READY_CHECK, LEAGUE_CLIENT_WINDOW_TITLE
from utils.general_utils import bring_window_to_front, listen_for_exit_key, enable_logging, start_queue_loop
from core.change_settings import launch_keybind_gui
from core.run_arena import run_arena_bot
from lcu_driver import Connector
import logging

connector = Connector()

# State variables
champions_map = {}
summoner_id = None
picked_champion = False
in_ready_check = False
game_started = False
last_phase = None

def show_menu():
    config = load_config()
    selected_game_mode = config.get("General", {}).get("selected_game_mode", list(SUPPORTED_MODES.keys())[0])
    print("=== League Bot Launcher ===")
    print("0. Exit")
    print("1. Run Script")
    print(f"2. Change gamemode from [{selected_game_mode}]")
    print("3. Change Settings")
    return input("Select an option: ").strip()

def run_script():
    logging.info("Starting Script. Waiting for client...")
    connector.start()

def change_settings():
    launch_keybind_gui()

def set_game_mode():
    def on_select():
        selected = mode_var.get()
        config = load_config()
        config["General"]["selected_game_mode"] = selected
        save_config(config)
        root.destroy()
        logging.info(f"Game mode set to '{selected}'.")

    config = load_config()
    selected_game_mode = config.get("General", {}).get("selected_game_mode", list(SUPPORTED_MODES.keys())[0])

    root = tk.Tk()
    root.title("Set Game Mode")

    tk.Label(root, text=f"Current mode: {selected_game_mode}").pack(pady=(10, 0))
    tk.Label(root, text="Select a new game mode:").pack(pady=5)

    mode_var = tk.StringVar(value=selected_game_mode)
    dropdown = ttk.Combobox(root, textvariable=mode_var, values=list(SUPPORTED_MODES.keys()), state="readonly")
    dropdown.pack(pady=5)

    tk.Button(root, text="Save", command=on_select).pack(pady=10)

    root.mainloop()

# ===========================
# LCU Event Listeners
# ===========================

@connector.ready
async def connect(connection):
    global summoner_id, champions_map
    logging.info("Connected to League Client, waiting for window...")

    hwnd = None
    for _ in range(60):  # Timeout for when client is connected, but window is not found
        hwnd = bring_window_to_front(LEAGUE_CLIENT_WINDOW_TITLE)
        if hwnd:
            break
        logging.info("League client window not found, retrying...")
        time.sleep(1)
    if not hwnd:
        logging.error("League client window not available. Aborting script.")
        return

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
    bring_window_to_front(LEAGUE_CLIENT_WINDOW_TITLE)
    timer = event.data.get('timer', {})
    phase = timer.get('phase')
    if phase == 'BAN_PICK' and not picked_champion:
        actions = event.data.get('actions', [])
        local_cell_id = event.data.get('localPlayerCellId')

        for action_group in actions:
            for action in action_group:
                if action.get('actorCellId') == local_cell_id and action.get('type') == 'pick' and action.get('isInProgress'):
                    action_id = action.get('id')

                    # Try to pick Bravery
                    logging.info("Attempting to pick championId -3 (Bravery)...")
                    await connection.request(
                        'patch',
                        f'/lol-champ-select/v1/session/actions/{action_id}',
                        data={"championId": -3, "completed": True}
                    )
                    await asyncio.sleep(0.5)
                    session = await connection.request('get', '/lol-champ-select/v1/session')
                    session_data = await session.json()
                    my_team = session_data.get("myTeam", [])
                    picked_bravery = any(
                        member.get("cellId") == local_cell_id and member.get("championId") == -3
                        for member in my_team
                    )
                    if picked_bravery:
                        logging.info("Successfully picked Bravery.")
                        picked_champion = True
                        return

                    # Fallback to random champion
                    logging.info("Attempting to pick a random champion from your pool...")
                    if not champions_map:
                        logging.error("No champions found in champion map. Skipping pick.")
                        return

                    valid_champ_ids = [cid for cid in champions_map.values() if cid != -1]
                    if not valid_champ_ids:
                        logging.error("No valid champion IDs available.")
                        return
                    champ_id = random.choice(valid_champ_ids)
                    champ_name = next((name for name, cid in champions_map.items() if cid == champ_id), "Unknown")
                    await connection.request(
                        'patch',
                        f'/lol-champ-select/v1/session/actions/{action_id}',
                        data={"championId": champ_id, "completed": True}
                    )
                    logging.info(f"Champion picked: {champ_name} (ID: {champ_id})")
                    picked_champion = True
                    return
    elif phase != 'BAN_PICK':
        picked_champion = False  # Reset flag when not in pick phase

@connector.ws.register(LCU_MATCHMAKING_READY_CHECK, event_types=('UPDATE',))
async def on_ready_check(connection, event):
    global in_ready_check
    bring_window_to_front(LEAGUE_CLIENT_WINDOW_TITLE)
    if event.data.get('state') == 'InProgress' and event.data.get('playerResponse') == 'None':
        if not in_ready_check:
            await connection.request('post', '/lol-matchmaking/v1/ready-check/accept')
            logging.info("Accepted ready check.")
            in_ready_check = True
    elif event.data.get('state') != 'InProgress':
        in_ready_check = False  # Reset flag when not in ready check

@connector.ws.register(LCU_GAMEFLOW_PHASE, event_types=('UPDATE',))
async def on_gameflow_phase(connection, event):
    global game_started, last_phase
    phase = event.data
    if phase == last_phase:
        return
    last_phase = phase
    logging.info(f"[EVENT] Gameflow phase: {phase}")

    if phase == "Lobby":
        threading.Thread(target=start_queue_loop, daemon=True).start()
        logging.info("[EVENT] Starting queue.")

    if phase == "InProgress":
        if not game_started:
            game_started = True
            logging.info("[EVENT] Game started. Running bot...")
            run_arena_bot()
    else:
        if game_started:
            game_started = False
            if phase == "EndOfGame":
                logging.info("[EVENT] Game ended. Cleanup or exit logic here.")

@connector.close
async def disconnect(_):
    logging.info("[INFO] League Client has been closed.")

# ===========================
# Main Entry Point
# ===========================

if __name__ == "__main__":
    disable_insecure_request_warning()
    enable_logging()
    logging.info("Press END key to exit anytime.")
    threading.Thread(target=listen_for_exit_key, daemon=True).start()
    while True:
        choice = show_menu()
        if choice == "0":
            break
        elif choice == "1":
            run_script()
        elif choice == "2":
            set_game_mode()
        elif choice == "3":
            change_settings()
        else:
            logging.warning("Invalid selection. Please try again.")
