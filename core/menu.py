import time
import logging
from utils.config_utils import get_selected_game_mode, set_selected_game_mode
from core.constants import LEAGUE_GAME_WINDOW_TITLE, SUPPORTED_MODES
from core.change_settings import launch_keybind_gui # Adjusted import                                                                                                                                                   

def show_menu(connector):
    selected_game_mode = get_selected_game_mode()
    print("=== INTAI Menu ===")
    print("0. Exit")
    print("1. Run Script")
    print(f"2. Change gamemode from [{selected_game_mode}]")
    print("3. Change Settings")
    print("4. Run tests")       
    choice = input("Select an option: ").strip()
    if choice == "0":
        return
    elif choice == "1":
        logging.info("Starting Script. Waiting for client...")
        connector.start()
        return
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
        # Show menu again after changing gamemode
        show_menu(connector)
    elif choice == "3":
        launch_keybind_gui()
        # Show menu again after changing settings
        show_menu(connector)
    elif choice == "4":
        logging.info("Running tests...")
        time.sleep(2)
    else:
        logging.warning("Invalid selection. Please try again.")
        show_menu(connector)