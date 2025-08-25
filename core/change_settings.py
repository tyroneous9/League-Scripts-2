from utils.config_utils import load_config, load_default_config, save_config
from utils.general_utils import get_champions_map
import tkinter as tk
import keyboard  # Requires local install

def launch_keybind_gui():
    config = load_config()
    keybinds = config.get("Keybinds", {})
    general = config.get("General", {})
    preferred_champion = general.get("preferred_champion", "")

    champions_map = get_champions_map()
    champ_names = sorted(champions_map.keys())

    root = tk.Tk()
    root.title("Edit Script Settings")

    champ_var = tk.StringVar(
        value=preferred_champion if preferred_champion in champ_names else (champ_names[0] if champ_names else "")
    )

    # Main horizontal frame
    main_frame = tk.Frame(root)
    main_frame.pack(padx=10, pady=10, fill="both", expand=True)

    # Left: Keybinds
    left_frame = tk.Frame(main_frame)
    left_frame.pack(side="left", fill="y", padx=(0, 20))

    tk.Label(left_frame, text="Keybinds (click box, then press key):").pack(pady=5)

    vars = {}
    entries = {}
    current_hook = {"id": None, "entry": None}

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

    # Buttons at the bottom
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="Save and Close", command=lambda: save_and_exit(vars, entries, keybinds, config, champ_var, root)).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Reset to Default", command=lambda: reset_to_default(vars, entries, champ_listbox, champ_names, champ_var)).pack(side="left", padx=5)

    root.update_idletasks()
    width = left_frame.winfo_reqwidth() + right_frame.winfo_reqwidth() + 80
    height = max(left_frame.winfo_reqheight(), right_frame.winfo_reqheight()) + 120
    root.geometry(f"{width}x{height}")

    root.mainloop()

def save_and_exit(vars, entries, keybinds, config, champ_var, root):
    for key in vars:
        keybinds[key] = vars[key].get().strip()
    config["Keybinds"] = keybinds
    config.setdefault("General", {})
    config["General"]["preferred_champion"] = champ_var.get()
    save_config(config)
    root.destroy()

def reset_to_default(vars, entries, champ_listbox, champ_names, champ_var):
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