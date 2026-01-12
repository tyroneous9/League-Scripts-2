"""Template preparation GUI.

Provides a small Tkinter app to pick a source image, choose a target
resolution (or custom), compute an optimal blur kernel and apply grayscale, and save it.

Usage:
  python tools/prepare_template_gui.py
"""
import json
import os
import re
import sys
from typing import Tuple, Dict, Any, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2

# ensure repo root is on sys.path so imports work when launching from tools/
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.cv_utils import get_grayscale, get_blurred

PRESET_RESOLUTIONS = [
    (1920, 1080),
    (1600, 900),
    (1366, 768),
    (1280, 720),
    (1024, 576),
]


def sanitize_id(s: Optional[str]) -> Optional[str]:
    """Sanitize a template id or filename base for safe filesystem use.

    Returns None if input is falsy.
    """
    if not s:
        return None
    s = s.strip()
    # remove path separators and illegal characters, replace spaces with underscores
    s = s.replace(os.path.sep, "_")
    s = re.sub(r"[^A-Za-z0-9._-]", "_", s)
    # collapse multiple underscores
    s = re.sub(r"_+", "_", s)
    return s

def prepare_template(src_path: str, templates_dir: str = "templates", resolution: Tuple[int, int] = (1920, 1080), blur_amount=0, template_id: Optional[str] = None) -> str:
    """Prepare a template by saving the original image and updating index.json.

    The original file is written to `templates/{width}x{height}/{name}_{width}x{height}.png`.

    The `blur_amount` is recorded in the index but NOT applied to the saved image.
    Returns: written file path (relative to repo) as a string.
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"source template not found: {src_path}")
    img = cv2.imread(src_path)
    if img is None:
        raise ValueError(f"could not load image: {src_path}")

    width, height = resolution
    out_dir = os.path.join(templates_dir, f"{width}x{height}")
    os.makedirs(out_dir, exist_ok=True)

    # determine template id using file name (or user-provided override)
    if template_id:
        template_id_base = os.path.splitext(os.path.basename(template_id))[0]
    else:
        template_id_base = os.path.splitext(os.path.basename(src_path))[0]
    # Do NOT apply preprocessing here. Save the original image as-is (preserve color).
    filename = f"{template_id_base}_{width}x{height}.png"
    out_path = os.path.join(out_dir, filename)
    # write original image without applying grayscale/blur
    cv2.imwrite(out_path, img)

    # Update single index.json file with metadata so runtime matchers know
    # how the template was preprocessed (blur kernel, grayscale, resolution)
    entry_info = {
        "path": os.path.join(f"{width}x{height}", filename),
        "blur": int(blur_amount)
    }
    _update_templates_index(template_id_base, entry_info, templates_dir)
    return out_path


def _update_templates_index(template_id: str, entry_info: Dict[str, Any], templates_dir: str = "templates", index_name: str = "index.json") -> str:
    """Add or update a template entry in `templates/index.json`.

    New format: per-resolution mapping: resolution -> { id: {path, blur} }
    `entry_info` should contain `path` (relative under templates/) and `blur`.
    Returns the index path that was written.
    """
    index_path = os.path.join(templates_dir, index_name)
    index = {}
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
        except Exception:
            index = {}

    rel_path = entry_info.get("path", "")
    if not rel_path:
        raise ValueError("entry_info.path is required")
    key = rel_path.split(os.path.sep)[0]
    if key not in index or not isinstance(index[key], dict):
        index[key] = {}

    # set/replace id mapping
    index[key][template_id] = entry_info

    os.makedirs(templates_dir, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    return index_path
    

# unified blur recommendation implemented locally in this file


class TemplatePrepGUI:
    def __init__(self, root: tk.Tk):
        self.MAX_BLUR = 10
        self.root = root
        self.root.title("Prepare Template — Template Prep")

        self.src_path = tk.StringVar()
        self.res_var = tk.StringVar(value=f"{PRESET_RESOLUTIONS[0][0]}x{PRESET_RESOLUTIONS[0][1]}")
        # initialize blur variable and set recommended value
        self.blur_var = tk.IntVar(value=1)
        self.set_blur_auto(None, PRESET_RESOLUTIONS[0])

        self.img_orig = None
        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=8)
        frm.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        row = 0
        ttk.Label(frm, text="Source image:").grid(row=row, column=0, sticky="w")
        e = ttk.Entry(frm, textvariable=self.src_path, width=60)
        e.grid(row=row, column=1, sticky="we", padx=4)
        ttk.Button(frm, text="Browse…", command=self.browse_file).grid(row=row, column=2)

        row += 1
        # Template ID (used as the stored id and filename base)
        ttk.Label(frm, text="Template ID:").grid(row=row, column=0, sticky="w")
        self.template_id_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.template_id_var, width=40).grid(row=row, column=1, sticky="w", padx=4)

        row += 1
        ttk.Label(frm, text="Resolution:").grid(row=row, column=0, sticky="w")
        res_combo = ttk.Combobox(frm, textvariable=self.res_var, values=[f"{w}x{h}" for w, h in PRESET_RESOLUTIONS])
        res_combo.grid(row=row, column=1, sticky="w")
        # update recommended blur when user selects a preset resolution
        res_combo.bind('<<ComboboxSelected>>', lambda e: self.set_blur_auto(None, self._get_target_resolution()))
        ttk.Button(frm, text="Custom…", command=self.set_custom_resolution).grid(row=row, column=2)

        row += 1
        ttk.Label(frm, text="Blur:").grid(row=row, column=0, sticky="w")
        # Use tk.Scale for integer steps and visible value
        blur_scale = tk.Scale(frm, from_=1, to=self.MAX_BLUR, orient="horizontal", variable=self.blur_var, command=self._on_blur_change, showvalue=False, resolution=1)
        blur_scale.set(self.blur_var.get())
        blur_scale.grid(row=row, column=1, sticky="we")
        # display current blur value and auto button
        self.blur_value_label = ttk.Label(frm, text=str(self.blur_var.get()))
        self.blur_value_label.grid(row=row, column=2, sticky="w")
        ttk.Button(frm, text="Auto", command=lambda: self.set_blur_auto(self.img_orig, None)).grid(row=row, column=3, padx=4)

        row += 1
        row += 1
        btn_frm = ttk.Frame(frm)
        btn_frm.grid(row=row, column=0, columnspan=3, sticky="e")
        ttk.Button(btn_frm, text="Prepare and Save", command=self.prepare_and_save).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frm, text="View Templates", command=self._open_index_view).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frm, text="Close", command=self.root.destroy).grid(row=0, column=2)

    def browse_file(self):
        p = filedialog.askopenfilename(title="Select image file", filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff"), ("All files", "*")])
        if not p:
            return
        self.src_path.set(p)
        # set default template id to input basename if not set
        try:
            base = os.path.splitext(os.path.basename(p))[0]
            if getattr(self, 'template_id_var', None) and not self.template_id_var.get():
                self.template_id_var.set(base)
        except Exception:
            print(f"warning: failed to set template id from basename: {p}", file=sys.stderr)
        self._load_image(p)

    def set_custom_resolution(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Custom resolution")

        w_var = tk.IntVar(value=1920)
        h_var = tk.IntVar(value=1080)

        ttk.Label(dlg, text="Width:").grid(row=0, column=0)
        ttk.Entry(dlg, textvariable=w_var).grid(row=0, column=1)
        ttk.Label(dlg, text="Height:").grid(row=1, column=0)
        ttk.Entry(dlg, textvariable=h_var).grid(row=1, column=1)

        def apply_custom():
            try:
                w = int(w_var.get()); h = int(h_var.get())
                self.set_blur_auto(None, (w, h))
            except ValueError as e:
                messagebox.showerror("Invalid", f"Invalid resolution: {e}")
                return
            dlg.destroy()
        ttk.Button(dlg, text="Apply", command=apply_custom).grid(row=2, column=0, columnspan=2)

    def _load_image(self, path):
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Error", f"Could not load image: {path}")
            return
        self.img_orig = img
        try:
            w, h = img.shape[1], img.shape[0]
            self.set_blur_auto(img, None)
        except Exception:
            print(f"warning: failed to compute auto blur for {path}", file=sys.stderr)

    def _on_blur_change(self, v):
        try:
            iv = int(float(v))
            if iv < 1:
                iv = 1
            self.blur_var.set(iv)
            # update label
            if hasattr(self, 'blur_value_label'):
                self.blur_value_label.config(text=str(iv))
        except Exception:
            pass

    def _get_target_resolution(self):
        val = self.res_var.get()
        if 'x' in val:
            parts = val.split('x')
            try:
                w = int(parts[0]); h = int(parts[1])
                return (w, h)
            except Exception:
                return PRESET_RESOLUTIONS[0]
        return PRESET_RESOLUTIONS[0]


    def prepare_and_save(self):
        src = self.src_path.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "Please choose a valid source image first.")
            return
        target_res = self._get_target_resolution()
        blur_amt = int(self.blur_var.get())
        try:
            tid = None
            if getattr(self, 'template_id_var', None):
                raw = self.template_id_var.get().strip() or None
                tid = sanitize_id(raw)
            out = prepare_template(src, templates_dir="templates", resolution=target_res, blur_amount=blur_amt, template_id=tid)
            messagebox.showinfo("Saved", f"Prepared template saved: {out}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to prepare template: {e}")


    def set_blur_auto(self, img: Optional[Any] = None, resolution: Optional[tuple] = None, max_kernel: Optional[int] = None, target_ratio: float = 0.7) -> int:
        """Compute an optimal blur kernel and set `self.blur_var`.

        If `img` is provided, an image-driven heuristic finds the smallest odd
        kernel that reduces edge count to the target ratio. Otherwise falls
        back to a resolution-based heuristic. The computed kernel is applied
        to `self.blur_var` and the visible label is updated.
        """
        import numpy as _np
        if max_kernel is None:
            max_kernel = self.MAX_BLUR

        # If an image is provided and templates are small, cap max_kernel
        # relative to the image (template) size so we don't over-smooth small templates.
        if img is not None:
            try:
                h, w = img.shape[0], img.shape[1]
                min_dim = min(w, h)
                # Allow kernel up to ~min_dim/10 (minimum 1 for templates)
                scaled_max = max(1, int(min_dim // 10))
                if scaled_max < max_kernel:
                    max_kernel = scaled_max
            except Exception:
                pass

        # resolution-only heuristic (fallback)
        if img is None:
            if resolution is None:
                resolution = (1920, 1080)
            w, h = resolution
            m = min(w, h)
            if m >= 1000:
                k = 7
            elif m >= 600:
                k = 5
            elif m >= 300:
                k = 3
            else:
                k = 1
            self.blur_var.set(k)
            if hasattr(self, 'blur_value_label'):
                self.blur_value_label.config(text=str(k))
            return k

        # image-driven heuristic
        gray = get_grayscale(img)

        def edge_count(im):
            v = _np.median(im)
            low = int(max(0, 0.66 * v))
            high = int(min(255, 1.33 * v))
            edges = cv2.Canny(im, low, high)
            return int((edges > 0).sum())

        orig_edges = edge_count(gray) or 1
        best_k = 1
        best_ratio = 1.0
        # consider odd kernels 1,3,5...
        for k in range(1, max_kernel + 1, 2):
            blurred = cv2.GaussianBlur(gray, (k, k), 0)
            cnt = edge_count(blurred)
            ratio = cnt / orig_edges
            if ratio <= target_ratio:
                self.blur_var.set(k)
                if hasattr(self, 'blur_value_label'):
                    self.blur_value_label.config(text=str(k))
                return k
            if ratio < best_ratio:
                best_ratio = ratio
                best_k = k

        self.blur_var.set(best_k)
        if hasattr(self, 'blur_value_label'):
            self.blur_value_label.config(text=str(best_k))
        return best_k


    # _auto_blur removed; use set_blur_auto directly
    # --- Index management helpers and UI ---
    def _load_index(self, templates_dir: str = "templates") -> dict:
        index_path = os.path.join(templates_dir, "index.json")
        if not os.path.exists(index_path):
            return {}
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_index(self, index: dict, templates_dir: str = "templates") -> None:
        os.makedirs(templates_dir, exist_ok=True)
        index_path = os.path.join(templates_dir, "index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def _delete_template_entry(self, entry: dict, templates_dir: str = "templates") -> bool:
        # attempt to remove file and entry from index
        rel_path = entry.get("path")
        if not rel_path:
            return False
        full_path = os.path.join(templates_dir, rel_path)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
        except Exception:
            pass

        index = self._load_index(templates_dir)
        # find key (resolution folder)
        key = rel_path.split(os.path.sep)[0]
        if key in index and isinstance(index[key], dict):
            tid = entry.get("id")
            if tid in index[key]:
                index[key].pop(tid, None)
                self._save_index(index, templates_dir)
                return True
        return False

    def _open_index_view(self):
        # create a simple dialog listing templates and allow deletion
        idx = self._load_index()
        dlg = tk.Toplevel(self.root)
        dlg.title("Templates Index")
        dlg.geometry("720x420")
        dlg.minsize(520, 300)

        # make dialog resizable and configure grid
        dlg.columnconfigure(0, weight=1)
        dlg.columnconfigure(1, weight=0)
        dlg.rowconfigure(0, weight=1)

        # listbox with vertical scrollbar
        listbox = tk.Listbox(dlg, width=60, height=14)
        listbox.grid(row=0, column=0, padx=(8, 0), pady=8, sticky="nsew")
        vsb = ttk.Scrollbar(dlg, orient="vertical", command=listbox.yview)
        vsb.grid(row=0, column=1, sticky="ns", padx=(4, 8), pady=8)
        listbox.config(yscrollcommand=vsb.set)

        entries = []
        for key in sorted(idx.keys()):
            # per-resolution value is a dict mapping id->info
            val = idx.get(key, {})
            if isinstance(val, dict):
                for tid, info in val.items():
                    e = {"id": tid, "path": info.get("path"), "blur": info.get("blur"), "resolution": key}
                    entries.append(e)

        for i, e in enumerate(entries):
            listbox.insert(tk.END, f"{e.get('id')}   ({e.get('resolution')})")

        detail_lbl = ttk.Label(dlg, text="Select a template to see details", anchor="w", wraplength=640)
        detail_lbl.grid(row=1, column=0, columnspan=2, padx=8, sticky="we")

        def on_select(evt):
            sel = listbox.curselection()
            if not sel:
                detail_lbl.config(text="Select a template to see details")
                return
            e = entries[sel[0]]
            detail_lbl.config(text=f"id: {e.get('id')}  path: {e.get('path')}  blur: {e.get('blur')}")

        listbox.bind('<<ListboxSelect>>', on_select)

        def on_delete():
            sel = listbox.curselection()
            if not sel:
                return
            e = entries[sel[0]]
            ok = self._delete_template_entry(e)
            if ok:
                listbox.delete(sel[0])
                entries.pop(sel[0])
                detail_lbl.config(text="Deleted")
            else:
                messagebox.showerror("Error", "Failed to delete template")

        btn_frm = ttk.Frame(dlg)
        btn_frm.grid(row=2, column=0, columnspan=2, sticky="we", padx=8, pady=8)
        btn_frm.columnconfigure(0, weight=1)
        btn_frm.columnconfigure(1, weight=1)
        del_btn = ttk.Button(btn_frm, text="Delete", command=on_delete)
        del_btn.grid(row=0, column=0, sticky="w")
        close_btn = ttk.Button(btn_frm, text="Close", command=dlg.destroy)
        close_btn.grid(row=0, column=1, sticky="e")


def main():
    root = tk.Tk()
    app = TemplatePrepGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
