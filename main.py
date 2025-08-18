import threading
import time
import random
import tkinter as tk
from tkinter import ttk
from utils.config_utils import load_config, save_config, disable_insecure_request_warning
from core.constants import SUPPORTED_MODES, LCU_GAMEFLOW_PHASE, LCU_CHAMP_SELECT_SESSION, LCU_MATCHMAKING_READY_CHECK, LEAGUE_CLIENT_WINDOW_TITLE
from utils.general_utils import listen_for_exit_key, click_percent_absolute
from utils.logging_utils import setup_logging
from core.change_settings import launch_keybind_gui
from core.run_arena import run_arena_bot
from lcu_driver import Connector
import win32gui
import win32con
from pynput import keyboard
import sys

processes = []
connector = Connector()

# State variables
should_click = True
in_champ_select = False
in_ready_check = False
in_game = False
champions_map = {}
summoner_id = None
picked_champion = False
game_started = False

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
        print(f"[WARNING] {LEAGUE_CLIENT_WINDOW_TITLE} window not found.")

def start_queue_loop():
    """
    Periodically brings the client to the front and clicks the queue button.
    """
    while True:
        bring_client_to_front()
        click_percent_absolute(40, 95)
        time.sleep(5)

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
    print("\n[INFO] Starting Script. Waiting for client...\n")
    disable_insecure_request_warning()
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
        print(f"Game mode set to '{selected}'.")

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
    """
    Event: League Client found.
    Purpose: Fetch summoner data and start queue loop.
    """
    global summoner_id, champions_map
    print("[INFO] Connected to League Client, waiting for window...")

    hwnd = None
    for _ in range(60):  # Timeout for client window
        hwnd = win32gui.FindWindow(None, LEAGUE_CLIENT_WINDOW_TITLE)
        if hwnd and win32gui.IsWindow(hwnd):
            break
        print("[INFO] League client window not found, retrying...")
        time.sleep(1)
    if not hwnd:
        print("[ERROR] League client window not available. Aborting script.")
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
    Event: Champion Select session created or updated.
    Purpose: Attempt to pick Bravery, then a random champion.
    """
    global picked_champion, champions_map, summoner_id
    timer = event.data.get('timer', {})
    phase = timer.get('phase')

    if phase in ('BAN_PICK'):
        actions = event.data.get('actions', [])
        local_cell_id = event.data.get('localPlayerCellId')

        for action_group in actions:
            for action in action_group:
                if action.get('actorCellId') == local_cell_id and action.get('type') == 'pick' and action.get('isInProgress'):
                    action_id = action.get('id')

                    # Attempt to pick championId -3 (Bravery)
                    print("[INFO] Attempting to pick championId -3 (Bravery)...")
                    await connection.request(
                        'patch',
                        f'/lol-champ-select/v1/session/actions/{action_id}',
                        data={"championId": -3, "completed": True}
                    )
                    time.sleep(0.5)
                    session = await connection.request('get', '/lol-champ-select/v1/session')
                    session_data = await session.json()
                    my_team = session_data.get("myTeam", [])
                    picked_bravery = False
                    for member in my_team:
                        if member.get("cellId") == local_cell_id and member.get("championId") == -3:
                            picked_bravery = True
                            break
                    if picked_bravery:
                        print("[INFO] Successfully picked Bravery.")
                        return

                    # Fallback to picking a random champion from your pool...
                    print("[INFO] Attempting to pick a random champion from your pool...")
                    if not champions_map:
                        print("[ERROR] No champions found in champion map. Skipping pick.")
                        return

                    valid_champ_ids = [cid for cid in champions_map.values() if cid != -1]
                    if not valid_champ_ids:
                        print("[ERROR] No valid champion IDs available.")
                        return
                    champ_id = random.choice(valid_champ_ids)
                    champ_name = next((name for name, cid in champions_map.items() if cid == champ_id), "Unknown")
                    await connection.request(
                        'patch',
                        f'/lol-champ-select/v1/session/actions/{action_id}',
                        data={"championId": champ_id, "completed": True}
                    )
                    print(f"[INFO] Champion picked: {champ_name} (ID: {champ_id})")
                    return
    else:
        picked_champion = False

@connector.ws.register(LCU_MATCHMAKING_READY_CHECK, event_types=('UPDATE',))
async def on_ready_check(connection, event):
    """
    Event: Ready Check pops up.
    Purpose: Automatically accept ready check when it appears.
    """
    bring_client_to_front()
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
    """
    Event: Gameflow phase updated.
    Purpose: Start bot when game begins, handle cleanup when game ends.
    """
    global game_started
    phase = event.data
    print(f"[EVENT] Gameflow phase: {phase}")
    if phase == "InProgress":
        game_started = True
        print("[EVENT] Game started. Running bot...")
        run_arena_bot()
    else:
        game_started = False  # Reset flag when not in game
        if phase == "EndOfGame":
            print("[EVENT] Game ended. Cleanup or exit logic here.")

@connector.close
async def disconnect(_):
    """
    Event: League Client exited.
    Purpose: Notify user that the client has closed.
    """
    print("[INFO] League Client has been closed.")



if __name__ == "__main__":
    setup_logging()
    print("Press END key to exit anytime.")
    threading.Thread(target=listen_for_exit_key, daemon=True).start()
    while True:
        choice = show_menu()
        if choice == "0":
            connector.stop()
            break
        elif choice == "1":
            run_script()
        elif choice == "2":
            set_game_mode()
        elif choice == "3":
            change_settings()
        else:
            print("Invalid selection. Please try again.")
