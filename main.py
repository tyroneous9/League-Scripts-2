import subprocess
import tkinter as tk
from tkinter import ttk
from core.config_utils import load_config, save_config
from core.constants import LOG_FILE_NAME, SUPPORTED_MODES
import logging

AVAILABLE_MODES = list(SUPPORTED_MODES.keys()) 


def show_menu():
    config = load_config()
    selected_game_mode = config.get("General", {}).get("selected_game_mode", AVAILABLE_MODES[0])
    print("=== League Bot Launcher ===")
    print("1. Run Script")
    print(f"2. Change gamemode from [{selected_game_mode}]")
    print("3. Change Settings")
    # Removed: print("0. Exit")
    return input("Select an option: ").strip()

def run_script():
    print("\n[INFO] Starting Script. Waiting for client...\n")
    subprocess.run(["python", "core/run_client.py"])


def change_settings():
    subprocess.Popen(["python", "core/change_settings.py"])


def set_game_mode():
    def on_select():
        selected = mode_var.get()
        config = load_config()
        config["General"]["selected_game_mode"] = selected
        save_config(config)
        root.destroy()
        print(f"Game mode set to '{selected}'.")

    config = load_config()
    selected_game_mode = config.get("General", {}).get("selected_game_mode", AVAILABLE_MODES[0])

    root = tk.Tk()
    root.title("Set Game Mode")

    tk.Label(root, text=f"Current mode: {selected_game_mode}").pack(pady=(10, 0))
    tk.Label(root, text="Select a new game mode:").pack(pady=5)

    mode_var = tk.StringVar(value=selected_game_mode)
    dropdown = ttk.Combobox(root, textvariable=mode_var, values=AVAILABLE_MODES, state="readonly")
    dropdown.pack(pady=5)

    tk.Button(root, text="Save", command=on_select).pack(pady=10)

    root.mainloop()


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE_NAME),
            logging.StreamHandler()
        ]
    )


if __name__ == "__main__":
    setup_logging()
    print("Press Ctrl+C to exit script, or END key to exit while ingame.")
    while True:
        choice = show_menu()
        if choice == "1":
            run_script()
        elif choice == "2":
            set_game_mode()
        elif choice == "3":
            change_settings()
        else:
            print("Invalid selection. Please try again.")
