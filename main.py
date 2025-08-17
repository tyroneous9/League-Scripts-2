import subprocess
import tkinter as tk
from tkinter import ttk
import os
from core.config_utils import load_config, save_config
from core.constants import SUPPORTED_MODES  # Import modularized modes

AVAILABLE_MODES = list(SUPPORTED_MODES.keys())  # Use keys from SUPPORTED_MODES


def show_menu():
    config = load_config()
    current_mode = config.get("General", {}).get("mode", AVAILABLE_MODES[0])
    print("=== League Bot Launcher ===")
    print("1. Run Script")
    print(f"2. Change gamemode from [{current_mode}]")
    print("3. Change Settings")
    print("0. Exit")
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
        config["General"]["mode"] = selected
        save_config(config)
        root.destroy()
        print(f"Game mode set to '{selected}'.")

    config = load_config()
    current_mode = config.get("General", {}).get("mode", AVAILABLE_MODES[0])

    root = tk.Tk()
    root.title("Set Game Mode")

    tk.Label(root, text=f"Current mode: {current_mode}").pack(pady=(10, 0))
    tk.Label(root, text="Select a new game mode:").pack(pady=5)

    mode_var = tk.StringVar(value=current_mode)
    dropdown = ttk.Combobox(root, textvariable=mode_var, values=AVAILABLE_MODES, state="readonly")
    dropdown.pack(pady=5)

    tk.Button(root, text="Save", command=on_select).pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    while True:
        choice = show_menu()
        if choice == "1":
            run_script()
        elif choice == "2":
            set_game_mode()
        elif choice == "3":
            change_settings()
        elif choice == "0":
            exit(0)
        else:
            print("Invalid selection. Please try again.")
