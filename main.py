# python -m core.main

import asyncio
import threading
import time
import random
import importlib
from utils.config_utils import (
    disable_insecure_request_warning, get_selected_game_mode, set_selected_game_mode, load_config
)
from core.constants import (
    SUPPORTED_MODES,
    LCU_GAMEFLOW_PHASE,
    LCU_CHAMP_SELECT_SESSION,
    LEAGUE_CLIENT_WINDOW_TITLE,
    GAMEFLOW_PHASES,
    CHAMP_SELECT_SUBPHASES
)
from utils.general_utils import listen_for_exit_key, enable_logging, get_champions_map
from core.change_settings import launch_keybind_gui
from lcu_driver import Connector
import logging
import win32gui

connector = Connector()

# State variables
last_phase = None
game_end_event = threading.Event()

# Thread references
game_loop_thread = None

def run_game_loop(stop_event):
    """
    Runs the correct bot loop for the selected game mode.
    The loop should exit when stop_event is set (signaled by EndOfGame phase).
    """
    selected_game_mode = get_selected_game_mode()
    mode_info = SUPPORTED_MODES.get(selected_game_mode)
    module_name = mode_info.get("module")
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        logging.error(f"Could not import module '{module_name}': {e}")
        return
    if hasattr(module, "run_game_loop"):
        module.run_game_loop(stop_event)
    elif hasattr(module, "main"):
        module.main()
    else:
        logging.error(f"No entry point found for '{selected_game_mode}'.")

# ===========================
# LCU Event Listeners
# ===========================

@connector.ready
async def connect(connection):
    """
    Handler for when the connector is ready and connected to the League Client.
    Waits for the client window, then triggers the initial gameflow phase logic.
    """
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
    """
    Handles changes in the overall gameflow phase (lobby, matchmaking, champ select, game start, etc.).
    Manages lobby creation, queueing, ready check, bot thread lifecycle, and play-again requests.
    """
    global last_phase, game_loop_thread
    phase = event.data
    if phase == last_phase:
        return
    last_phase = phase

    # Create a lobby
    if phase == GAMEFLOW_PHASES["NONE"]:
        selected_game_mode = get_selected_game_mode()
        mode_info = SUPPORTED_MODES.get(selected_game_mode)
        queue_id = mode_info.get("queue_id")
        try:
            await connection.request('post', '/lol-lobby/v2/lobby', data={"queueId": queue_id})
            logging.info(f"{selected_game_mode.capitalize()} lobby created.")
        except Exception as e:
            logging.error(f"Failed to create {selected_game_mode} lobby: {e}")

    # Start queue
    if phase == GAMEFLOW_PHASES["LOBBY"]:
        try:
            await connection.request('post', '/lol-lobby/v2/lobby/matchmaking/search')
            logging.info("[EVENT] Starting queue.")
        except Exception as e:
            logging.error(f"Failed to start queue: {e}")

    # Accept ready check
    if phase == GAMEFLOW_PHASES["READY_CHECK"]:
        try:
            await connection.request('post', '/lol-matchmaking/v1/ready-check/accept')
            logging.info("Accepted ready check.")
        except Exception as e:
            logging.error(f"Failed to accept ready check: {e}")

    # Log champion select phase
    if phase == GAMEFLOW_PHASES["CHAMP_SELECT"]:
        logging.info("[EVENT] In champion select.")

    # Start bot loop thread on game start
    if phase == GAMEFLOW_PHASES["GAME_START"]:
        logging.info("[EVENT] Game started.")
        game_end_event.clear()
        # Start the game loop thread if not already running
        if game_loop_thread is None or not game_loop_thread.is_alive():
            game_loop_thread = threading.Thread(target=run_game_loop, args=(game_end_event,), daemon=True)
            game_loop_thread.start()

    # Log in-progress phase
    if phase == GAMEFLOW_PHASES["IN_PROGRESS"]:
        logging.info("[EVENT] Game in progress.")

    # Clean up bot thread and send play-again request on end of game
    if phase == GAMEFLOW_PHASES["END_OF_GAME"]:
        logging.info("[EVENT] Game ended.")
        game_end_event.set()
        if game_loop_thread is not None:
            game_loop_thread.join()
            game_loop_thread = None
        # Play again (recreate lobby)
        try:
            await connection.request('post', '/lol-lobby/v2/play-again')
            logging.info("Sent play-again request.")
        except Exception as e:
            logging.error(f"Failed to send play-again request: {e}")

@connector.ws.register(LCU_CHAMP_SELECT_SESSION, event_types=('CREATE', 'UPDATE',))
async def on_champ_select_session(connection, event):
    """
    Handles champ select session updates, including subphase changes.
    Picks a champion during the BAN_PICK subphase.
    """
    session_data = event.data
    timer = session_data.get('timer', {})
    champ_phase = timer.get('phase')
    actions = session_data.get('actions', [])
    local_cell_id = session_data.get('localPlayerCellId')

    # Only pick during BAN_PICK subphase
    if champ_phase == CHAMP_SELECT_SUBPHASES["BAN_PICK"]:
        config = load_config()
        preferred_champion = config.get("General", {}).get("preferred_champion", "").strip()
        champions_map = get_champions_map()

        # Try to get the preferred champion ID
        preferred_champ_id = champions_map.get(preferred_champion) if preferred_champion else None

        for action_group in actions:
            for action in action_group:
                if action.get('actorCellId') == local_cell_id and action.get('type') == 'pick'  and action.get('isInProgress'):
                    action_id = action.get('id')
                    # Attempt to pick preferred champion first
                    if preferred_champion != "":
                        preferred_champ_id = champions_map.get(preferred_champion)
                        await connection.request(
                            'patch',
                            f'/lol-champ-select/v1/session/actions/{action_id}',
                            data={"championId": preferred_champ_id, "completed": True}
                        )
                        await asyncio.sleep(0.5)

                    # Pick Bravery for arena
                    await connection.request(
                        'patch',
                        f'/lol-champ-select/v1/session/actions/{action_id}',
                        data={"championId": -3, "completed": True}
                    )
                    await asyncio.sleep(0.5)

                    # Pick a random champion if preferred not set or failed
                    valid_champ_ids = [cid for cid in champions_map.values() if cid != -1]
                    champ_id = random.choice(valid_champ_ids)
                    await connection.request(
                        'patch',
                        f'/lol-champ-select/v1/session/actions/{action_id}',
                        data={"championId": champ_id, "completed": True}
                    )
                    return

@connector.close
async def disconnect(_):
    """
    Handler for when the League Client is closed.
    Logs the disconnect event.
    """
    logging.info("[INFO] League Client has been closed.")

# ===========================
# Main Entry Point
# ===========================

if __name__ == "__main__":
    """
    Main entry point for the League Bot Launcher.
    Handles menu navigation and starts the connector.
    """
    disable_insecure_request_warning()
    enable_logging()
    threading.Thread(target=listen_for_exit_key, daemon=True).start()
    while True:
        selected_game_mode = get_selected_game_mode()
        print("=== INTAI Menu ===")
        print("0. Exit")
        print("1. Run Script")
        print(f"2. Change gamemode from [{selected_game_mode}]")
        print("3. Change Settings")
        print("4. Run tests")
        choice = input("Select an option: ").strip()
        if choice == "0":
            break
        elif choice == "1":
            logging.info("Starting Script. Waiting for client...")
            connector.start()
        elif choice == "2":
            print("Available game modes:")
            for idx, mode in enumerate(SUPPORTED_MODES.keys(), start=1):
                print(f"{idx}. {mode}")
            mode_choice = input("Select game mode: ").strip()
            try:
                mode_idx = int(mode_choice) - 1
                mode_list = list(SUPPORTED_MODES.keys())
                if 0 <= mode_idx < len(mode_list):
                    set_selected_game_mode(mode_list[mode_idx])
                    logging.info(f"Game mode set to '{mode_list[mode_idx]}'.")
                else:
                    logging.warning("Invalid selection. Please try again.")
            except ValueError:
                logging.warning("Invalid input. Please enter a number.")
        elif choice == "3":
            launch_keybind_gui()
        elif choice == "4":
            logging.info("Running tests...")
            time.sleep(1)
            run_game_loop(game_end_event)
        else:
            logging.warning("Invalid selection. Please try again.")
