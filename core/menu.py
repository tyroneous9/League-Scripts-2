import logging
import tkinter as tk
from tkinter import messagebox
import keyboard  # Requires local install
from utils.config_utils import (
    get_selected_game_mode, set_selected_game_mode,
    load_config, load_default_config, save_config
)
from utils.general_utils import get_champions_map
from core.constants import SUPPORTED_MODES

def show_menu(run_script_callback):
    root = tk.Tk()
    root.title("INTAI Menu")
    root.geometry("500x400")

    # --- Frames for each "page" ---
    menu_frame = tk.Frame(root)
    settings_frame = tk.Frame(root)
    gamemode_frame = tk.Frame(root)

    def show_frame(frame):
        frame.tkraise()
        root.update_idletasks()
        # Resize window to fit current frame
        width = frame.winfo_reqwidth() + 20
        height = frame.winfo_reqheight() + 20
        root.geometry(f"{width}x{height}")

    # --- MENU PAGE ---
    def run_script():
        root.destroy()
        run_script_callback(testing=False)
        

    def run_tests():
        root.destroy()
        logging.info("Running tests...")
        run_script_callback(testing=True)

    def change_gamemode():
        # Clear previous widgets in gamemode_frame
        for widget in gamemode_frame.winfo_children():
            widget.destroy()

        # Top left "Back to Menu" button
        top_frame = tk.Frame(gamemode_frame)
        top_frame.pack(fill="x", pady=(5, 0))
        tk.Button(top_frame, text="← Back to Menu", command=lambda: show_frame(menu_frame)).pack(side="left", padx=5)

        tk.Label(gamemode_frame, text="Select Game Mode:", font=("Arial", 14)).pack(pady=10)
        mode_var = tk.IntVar(value=0)
        mode_list = list(SUPPORTED_MODES.keys())
        for idx, mode in enumerate(mode_list):
            tk.Radiobutton(gamemode_frame, text=mode, variable=mode_var, value=idx).pack(anchor="w", padx=20)

        def set_mode():
            idx = mode_var.get()
            if 0 <= idx < len(mode_list):
                set_selected_game_mode(mode_list[idx])
                logging.info(f"Game mode set to '{mode_list[idx]}'.")
                refresh_menu()
                show_frame(menu_frame)
            else:
                messagebox.showwarning("Invalid Selection", "Please select a valid game mode.")

        tk.Button(gamemode_frame, text="Set Mode", command=set_mode).pack(pady=10)
        show_frame(gamemode_frame)


    def refresh_menu():
        selected_game_mode = get_selected_game_mode()
        game_mode_label.config(text=f"Current Game Mode: {selected_game_mode}")

    # --- SETTINGS PAGE ---
    def change_settings():
        config = load_config()
        keybinds = config.get("Keybinds", {})
        general = config.get("General", {})
        preferred_champion = general.get("preferred_champion", "")

        champions_map = get_champions_map()
        champ_names = sorted(champions_map.keys())
        champ_var = tk.StringVar(
            value=preferred_champion if preferred_champion in champ_names else (champ_names[0] if champ_names else "")
        )

        # Clear previous widgets in settings_frame
        for widget in settings_frame.winfo_children():
            widget.destroy()

        # Top left "Back to Menu" button
        top_frame = tk.Frame(settings_frame)
        top_frame.pack(fill="x", pady=(5, 0))
        tk.Button(top_frame, text="← Back to Menu", command=lambda: show_frame(menu_frame)).pack(side="left", padx=5)

        # Main horizontal frame
        main_frame = tk.Frame(settings_frame)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Left: Keybinds
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side="left", fill="y", padx=(0, 20))

        tk.Label(left_frame, text="Keybinds (click box, then press key):").pack(pady=5)

        vars = {}
        entries = {}
        current_hook = {"id": None, "entry": None}

        def capture_key(entry_widget, var):
            if current_hook["id"]:
                keyboard.unhook(current_hook["id"])
                current_hook["id"] = None
            if current_hook["entry"]:
                current_hook["entry"].config(state="readonly", bg="SystemButtonFace")
            entry_widget.config(state="disabled", bg="#ffd966")
            current_hook["entry"] = entry_widget

            def on_key(e):
                var.set(e.name)
                entry_widget.config(state="normal")
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, e.name)
                entry_widget.config(state="readonly", bg="SystemButtonFace")
                if current_hook["id"]:
                    keyboard.unhook(current_hook["id"])
                    current_hook["id"] = None
                current_hook["entry"] = None

            current_hook["id"] = keyboard.hook(on_key)

        for key, val in keybinds.items():
            row = tk.Frame(left_frame)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=key, width=20, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(val))
            entry = tk.Entry(row, textvariable=var, width=20, state="readonly")
            entry.pack(side="left", fill="x", expand=True)
            entry.bind("<Button-1>", lambda e, w=entry, v=var: capture_key(w, v))
            vars[key] = var
            entries[key] = entry

        # Right: Champion selection
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="left", fill="y")

        tk.Label(right_frame, text="Preferred Champion:").pack(anchor="w", pady=(0, 5))
        listbox_frame = tk.Frame(right_frame)
        listbox_frame.pack(fill="y")

        champ_listbox = tk.Listbox(listbox_frame, height=15, exportselection=False)
        champ_listbox.pack(side="left", fill="y")

        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=champ_listbox.yview)
        scrollbar.pack(side="left", fill="y")
        champ_listbox.config(yscrollcommand=scrollbar.set)

        for name in champ_names:
            champ_listbox.insert(tk.END, name)
        # Set initial selection
        if champ_var.get() in champ_names:
            champ_listbox.selection_set(champ_names.index(champ_var.get()))
            champ_listbox.see(champ_names.index(champ_var.get()))
        else:
            champ_listbox.selection_set(0)

        def on_champ_select(event):
            selection = champ_listbox.curselection()
            if selection:
                champ_var.set(champ_listbox.get(selection[0]))

        champ_listbox.bind("<<ListboxSelect>>", on_champ_select)

        def save_and_exit():
            for key in vars:
                keybinds[key] = vars[key].get().strip()
            config["Keybinds"] = keybinds
            config.setdefault("General", {})
            config["General"]["preferred_champion"] = champ_var.get()
            save_config(config)
            show_frame(menu_frame)

        def reset_to_default():
            default_config = load_default_config()
            default_keybinds = default_config.get("Keybinds", {})
            for key in vars:
                val = default_keybinds.get(key, "")
                vars[key].set(val)
                entries[key].config(state="normal")
                entries[key].delete(0, tk.END)
                entries[key].insert(0, val)
                entries[key].config(state="readonly", bg="SystemButtonFace")
            champ_listbox.selection_clear(0, tk.END)
            champ_var.set("")  # Set preferred champion to empty

        # Buttons at the bottom (no "Back to Menu" here)
        btn_frame = tk.Frame(settings_frame)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Save and Close", command=save_and_exit).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Reset to Default", command=reset_to_default).pack(side="left", padx=5)

        settings_frame.update_idletasks()
        show_frame(settings_frame)

    # --- Build MENU FRAME ---
    menu_frame.place(relwidth=1, relheight=1)
    tk.Label(menu_frame, text="INTAI Menu", font=("Arial", 16)).pack(pady=10)
    game_mode_label = tk.Label(menu_frame, text=f"Current Game Mode: {get_selected_game_mode()}", font=("Arial", 12))
    game_mode_label.pack(pady=5)
    tk.Button(menu_frame, text="Run Script", width=20, command=run_script).pack(pady=5)
    tk.Button(menu_frame, text="Change Game Mode", width=20, command=change_gamemode).pack(pady=5)
    tk.Button(menu_frame, text="Change Settings", width=20, command=change_settings).pack(pady=5)
    tk.Button(menu_frame, text="Run Tests", width=20, command=run_tests).pack(pady=5)
    tk.Button(menu_frame, text="Exit", width=20, command=root.destroy).pack(pady=10)

    # --- Build SETTINGS FRAME ---
    settings_frame.place(relwidth=1, relheight=1)
    # --- Build GAMEMODE FRAME ---
    gamemode_frame.place(relwidth=1, relheight=1)

    # --- Start with menu frame ---
    menu_frame.tkraise()

    root.mainloop()