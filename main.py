import asyncio
import threading
import time
import random
import tkinter as tk
from tkinter import ttk
from utils.config_utils import (
    disable_insecure_request_warning, get_selected_game_mode, set_selected_game_mode
)
from core.constants import SUPPORTED_MODES, LCU_GAMEFLOW_PHASE, LCU_CHAMP_SELECT_SESSION, LCU_MATCHMAKING_READY_CHECK, LEAGUE_CLIENT_WINDOW_TITLE
from utils.general_utils import listen_for_exit_key, enable_logging
from core.change_settings import launch_keybind_gui
from lcu_driver import Connector
import logging
import win32gui
import importlib

connector = Connector()

# State variables
last_phase = None
game_end_event = threading.Event()
game_loop_thread = None

def show_menu():
    selected_game_mode = get_selected_game_mode()
    print("=== League Bot Launcher ===")
    print("0. Exit")
    print("1. Run Script")
    print(f"2. Change gamemode from [{selected_game_mode}]")
    print("3. Change Settings")
    return input("Select an option: ").strip()

def change_settings():
    launch_keybind_gui()

def set_game_mode():
    def on_select():
        selected = mode_var.get()
        set_selected_game_mode(selected)
        root.destroy()
        logging.info(f"Game mode set to '{selected}'.")

    selected_game_mode = get_selected_game_mode()

    root = tk.Tk()
    root.title("Set Game Mode")

    tk.Label(root, text=f"Current mode: {selected_game_mode}").pack(pady=(10, 0))
    tk.Label(root, text="Select a new game mode:").pack(pady=5)

    mode_var = tk.StringVar(value=selected_game_mode)
    dropdown = ttk.Combobox(root, textvariable=mode_var, values=list(SUPPORTED_MODES.keys()), state="readonly")
    dropdown.pack(pady=5)

    tk.Button(root, text="Save", command=on_select).pack(pady=10)

    root.mainloop()

def run_game_loop(stop_event):
    """
    Dynamically imports and runs the correct bot loop for the selected game mode.
    The loop should exit when stop_event is set (signaled by EndOfGame phase).
    """
    selected_game_mode = get_selected_game_mode().lower()
    mode_info = SUPPORTED_MODES.get(selected_game_mode)
    module_name = mode_info.get("module")
    if not module_name:
        logging.error(f"No module defined for game mode '{selected_game_mode}'.")
        return
    try:
        module_script = importlib.import_module(module_name)
        # Pass stop_event to the bot loop so it can exit when signaled
        module_script.run_game_loop(stop_event)
    except Exception as e:
        logging.error(f"Failed to run script for '{selected_game_mode}': {e}")

# ===========================
# LCU Event Listeners
# ===========================

@connector.ready
async def connect(connection):
    logging.info("Connected to League Client, waiting for window...")

    # Make sure client window is available
    hwnd = None
    for _ in range(60):
        hwnd = win32gui.FindWindow(None, LEAGUE_CLIENT_WINDOW_TITLE)
        if hwnd:
            break
        logging.info("League client window not found, retrying...")
        time.sleep(1)
    if not hwnd:
        logging.error("League client window not available. Aborting script.")
        return

    # Read the gameflow phase
    phase_resp = await connection.request('get', '/lol-gameflow/v1/gameflow-phase')
    current_phase = await phase_resp.json()
    await on_gameflow_phase(connection, type('Event', (object,), {'data': current_phase})())

@connector.ws.register(LCU_GAMEFLOW_PHASE, event_types=('UPDATE',))
async def on_gameflow_phase(connection, event):
    global last_phase, game_loop_thread
    phase = event.data
    if phase == last_phase:
        return
    last_phase = phase
    logging.info(f"Gameflow phase changed to: {phase}")

    # Create a lobby
    if phase == "None":
        selected_game_mode = get_selected_game_mode()
        mode_info = SUPPORTED_MODES.get(selected_game_mode.lower())
        queue_id = mode_info.get("queue_id")
        try:
            await connection.request('post', '/lol-lobby/v2/lobby', data={"queueId": queue_id})
            logging.info(f"{selected_game_mode.capitalize()} lobby created (queueId={queue_id}).")
        except Exception as e:
            logging.error(f"Failed to create {selected_game_mode} lobby: {e}")

    # Start queue
    if phase == "Lobby" or phase == "EndOfGame":
        try:
            await connection.request('post', '/lol-lobby/v2/lobby/matchmaking/search')
            logging.info("[EVENT] Starting queue.")
        except Exception as e:
            logging.error(f"Failed to start queue: {e}")

    # Accept ready check
    if phase == "ReadyCheck":
        try:
            await connection.request('post', '/lol-matchmaking/v1/ready-check/accept')
            logging.info("Accepted ready check.")
        except Exception as e:
            logging.error(f"Failed to accept ready check: {e}")

    # Handle champion select phase
    if phase == "ChampSelect":
        try:
            session = await connection.request('get', '/lol-champ-select/v1/session')
            session_data = await session.json()
            actions = session_data.get('actions', [])
            local_cell_id = session_data.get('localPlayerCellId')

            summoner = await connection.request('get', '/lol-summoner/v1/current-summoner')
            summoner_to_json = await summoner.json()
            summoner_id = summoner_to_json['summonerId']

            champion_list = await connection.request('get', f'/lol-champions/v1/inventories/{summoner_id}/champions-minimal')
            champion_list_to_json = await champion_list.json()
            champions_map = {champion['name']: champion['id'] for champion in champion_list_to_json}

            for action_group in actions:
                for action in action_group:
                    if action.get('actorCellId') == local_cell_id and action.get('type') == 'pick' and action.get('isInProgress'):
                        action_id = action.get('id')

                        # Pick Bravery for arena
                        await connection.request(
                            'patch',
                            f'/lol-champ-select/v1/session/actions/{action_id}',
                            data={"championId": -3, "completed": True}
                        )
                        await asyncio.sleep(0.5)

                        # Pick a random champion
                        if not champions_map:
                            logging.error("No champions found for your account.")
                            return

                        valid_champ_ids = [cid for cid in champions_map.values() if cid != -1]
                        champ_id = random.choice(valid_champ_ids)
                        champ_name = next((name for name, cid in champions_map.items() if cid == champ_id), "Unknown")
                        logging.info(f"Picking champion: {champ_name}")
                        await connection.request(
                            'patch',
                            f'/lol-champ-select/v1/session/actions/{action_id}',
                            data={"championId": champ_id, "completed": True}
                        )
                        return
        except Exception as e:
            logging.error(f"Failed to pick champion: {e}")

    if phase == "GameStart":
        logging.info("[EVENT] Game started.")
        game_end_event.clear()
        # Start the game loop thread if not already running
        if game_loop_thread is None or not game_loop_thread.is_alive():
            game_loop_thread = threading.Thread(target=run_game_loop, args=(game_end_event,), daemon=True)
            game_loop_thread.start()

    if phase == "InProgress":
        logging.info("[EVENT] Game in progress.")
        # No need to do anything here; game loop keeps running

    if phase == "EndOfGame":
        logging.info("[EVENT] Game ended. Cleanup or exit logic here.")
        game_end_event.set()
        if game_loop_thread is not None:
            game_loop_thread.join()
            game_loop_thread = None

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
            logging.info("Starting Script. Waiting for client...")
            connector.start()
        elif choice == "2":
            set_game_mode()
        elif choice == "3":
            change_settings()
        else:
            logging.warning("Invalid selection. Please try again.")
