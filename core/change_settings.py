from utils.config_utils import load_config, load_default_config, save_config
import tkinter as tk
import keyboard  # Requires local install

def launch_keybind_gui():
    config = load_config()
    keybinds = config.get("Keybinds", {})

    root = tk.Tk()
    root.title("Edit Keybinds")

    tk.Label(root, text="Click a box, then press the desired key").pack(pady=5)

    vars = {}
    entries = {}
    current_hook = {"id": None, "entry": None}  # Track key hook and active entry

    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True, padx=10, pady=5)

    def capture_key(entry_widget, var):
        # Always stop any previous hook
        if current_hook["id"]:
            keyboard.unhook(current_hook["id"])
            current_hook["id"] = None

        # Re-enable previous entry if needed
        if current_hook["entry"]:
            current_hook["entry"].config(state="readonly", bg="SystemButtonFace")

        entry_widget.config(state="disabled", bg="#ffd966")  # Highlight color
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
        row = tk.Frame(frame)
        row.pack(fill="x", pady=4)

        tk.Label(row, text=key, width=20, anchor="w").pack(side="left")

        var = tk.StringVar(value=str(val))
        entry = tk.Entry(row, textvariable=var, width=20, state="readonly")
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Button-1>", lambda e, w=entry, v=var: capture_key(w, v))

        vars[key] = var
        entries[key] = entry

    def save_and_exit():
        for key in vars:
            keybinds[key] = vars[key].get().strip()
        config["Keybinds"] = keybinds
        save_config(config)
        root.destroy()

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

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="Save and Close", command=save_and_exit).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Reset to Default", command=reset_to_default).pack(side="left", padx=5)

    # Resize window to fit content dynamically
    root.update_idletasks()
    width = frame.winfo_reqwidth() + 40
    height = frame.winfo_reqheight() + 130
    root.geometry(f"{width}x{height}")

    root.mainloop()