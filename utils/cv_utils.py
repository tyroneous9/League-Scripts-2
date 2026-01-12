import numpy as np
import cv2
import os
import json
from pathlib import Path
from typing import Dict, Optional
from core.constants import ALLY_HEALTH_RIGHT_COLOR, ARENA_EXIT_LOWER_COLOR, ARENA_EXIT_UPPER_COLOR, ATTACHED_ALLY_LEFT_COLOR, ATTACHED_ALLY_LEFT_COLOR, ATTACHED_ALLY_RIGHT_COLOR, AUGMENT_LOWER_COLOR, AUGMENT_UPPER_COLOR, ENEMY_HEALTH_RIGHT_COLOR, HEALTH_LEFT_COLOR, PLAYER_HEALTH_RIGHT_COLOR, SHOP_LOWER_COLOR, SHOP_UPPER_COLOR, TEMPLATES_INDEX_PATH, THRESHHOLD, SCREEN_WIDTH, SCREEN_HEIGHT, TEMPLATES_DIR


# ===========================
# Basic Utils
# ===========================


def get_color_mask(img, color_bgr, tolerance=0):
    """Return a binary mask where pixels within `tolerance` of `color_bgr` are 255.

    Args:
        img (np.ndarray): BGR image.
        color_bgr (tuple/list/np.ndarray): BGR color to match.
        tolerance (int or tuple): scalar or per-channel tolerance.

    Returns:
        np.ndarray: single-channel mask (dtype=uint8) with binary values.
    """

    col = np.array(color_bgr, dtype=np.int16)
    lower = np.clip(col - np.array(tolerance, dtype=np.int16), 0, 255).astype(np.uint8)
    upper = np.clip(col + np.array(tolerance, dtype=np.int16), 0, 255).astype(np.uint8)
    return cv2.inRange(img, lower, upper)


def save_color_mask(img, color_bgr, tolerance=0, out_path: Optional[str] = None):
    """Compute a color mask and save it to disk.

    Args:
        img (np.ndarray): BGR image.
        color_bgr (tuple): BGR color to match.
        tolerance (int): scalar tolerance per channel.

    Returns:
        str: full path to written mask image.
    """
    mask = get_color_mask(img, color_bgr, tolerance=tolerance)
    return save_image(mask, out_path)


def get_grayscale(img: np.ndarray) -> np.ndarray:
    """Return a grayscale copy of `img`.

    Works for BGR or already-grayscale images.
    """
    if len(img.shape) == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def save_grayscale(img: np.ndarray, out_path: Optional[str] = None) -> str:
    """Save a grayscale version of `img` to `out_path` and return the path.

    If `out_path` is None the image will be written to `temp/temp_img.png`.
    """
    gray = get_grayscale(img)
    return save_image(gray, out_path)


def get_blurred(img: np.ndarray, blur_amount=3) -> np.ndarray:
    """Return a blurred copy of `img` using a Gaussian kernel.
    """
    k = max(1, int(blur_amount)) | 1
    ksize = (k, k)
    return cv2.GaussianBlur(img, ksize, 0)


def save_blurred(img: np.ndarray, out_path: Optional[str] = None, blur_amount=5) -> str:
    """Apply Gaussian blur to `img` and save to `out_path`. Returns the path.

    If `out_path` is None the image will be written to `temp/temp_img.png`.
    """
    blurred = get_blurred(img, blur_amount=blur_amount)
    return save_image(blurred, out_path)


def save_image(img: np.ndarray, out_path: Optional[str] = None) -> str:
    """Save `img` to `out_path` and return the full path.

    If `out_path` is not provided, saves to `temp/temp_img.png`.
    """
    if out_path is None:
        out_dir = os.path.join("temp")
        out_path = os.path.join(out_dir, "temp_img.png")
    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    # Use cv2.imwrite which handles single-channel or multi-channel images.
    success = cv2.imwrite(out_path, img)
    if not success:
        raise IOError(f"Failed to write image to {out_path}")
    return out_path


# -------------------------
# Pattern matching utils
# -------------------------

# Caches MUST be loaded before use of template matching functions
_INDEX_CACHE: Dict[str, Dict[str, Dict]] = {}
_INDEX_LOADED: bool = False
_TEMPLATE_IMAGE_CACHE: Dict[str, np.ndarray] = {}


def load_index() -> Dict[str, Dict[str, Dict]]:
    """
    Return the in-memory index cache.
    """
    global _INDEX_CACHE, _INDEX_LOADED
    if not _INDEX_LOADED:
        raise RuntimeError("Templates index not loaded. Call load_template_cache() at startup.")
    return _INDEX_CACHE


def load_template_image(entry: Dict) -> Optional[np.ndarray]:
    """Load the template image from cache or disk.
    """
    base_dir = Path(TEMPLATES_DIR)
    path = base_dir / entry.get("path")
    key = str(path)
    img = _TEMPLATE_IMAGE_CACHE[key]
    return img


def load_template_cache() -> None:
    """Cache loader: read index and preload grayscale templates.
    """
    global _INDEX_CACHE, _INDEX_LOADED, _TEMPLATE_IMAGE_CACHE

    with TEMPLATES_INDEX_PATH.open("r", encoding="utf-8") as fh:
        full_idx = json.load(fh)

    resolution_key = f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}"
    entries = full_idx[resolution_key]

    _INDEX_CACHE = {resolution_key: entries}
    _TEMPLATE_IMAGE_CACHE.clear()

    base_dir = Path(TEMPLATES_DIR)
    for tid, entry in entries.items():
        rel = entry.get("path")
        tpl_path = base_dir / rel
        key = str(tpl_path)
        # Read original raw template (no preprocessing)
        img_orig = cv2.imread(str(tpl_path), cv2.IMREAD_UNCHANGED)
        if img_orig is None:
            raise IOError(f"Failed to read template image for id {tid!r}: {tpl_path}")
        # Apply preprocessing before loading to cache
        img_gray = get_grayscale(img_orig)
        blur_amount = int(entry.get("blur"))
        img_proc = get_blurred(img_gray, blur_amount=blur_amount)
        _TEMPLATE_IMAGE_CACHE[key] = img_proc

    _INDEX_LOADED = True


def clear_template_cache() -> None:
    """Clear in-memory template and index caches."""
    global _INDEX_CACHE, _INDEX_LOADED, _TEMPLATE_IMAGE_CACHE
    _INDEX_CACHE.clear()
    _INDEX_LOADED = False
    _TEMPLATE_IMAGE_CACHE.clear()


# Primary template matching function
def find_template_match(
    img: np.ndarray,
    id: str,
    threshold: float = 0.98,
):
    """Find the best matching template using a pyramid coarse-to-fine search.
    Args:
        img (np.ndarray): BGR image to search.
        id (str): template id to search for.
        threshold (float): minimum matching score to consider a valid match.
    Returns:
        tuple: (x, y) location of top-left corner of the first match, or None
    """
    assert img is not None, "caller must provide a valid image"
    index = load_index()
    resolution_key = f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}"
    if resolution_key not in index:
        raise ValueError(f"Templates index does not contain resolution {resolution_key}")
    entries_by_id = index[resolution_key]
    if id not in entries_by_id:
        raise ValueError(f"Template id {id!r} not found for resolution {resolution_key}")
    entry = entries_by_id[id]
    
    img_gray_full = get_grayscale(img)
    blur_amount = int(entry.get("blur"))
    img_preproc = get_blurred(img_gray_full, blur_amount=blur_amount)

    tpl = load_template_image(entry)
    if tpl is None:
        raise FileNotFoundError(f"Template image for id {id!r} not found at path {entry.get('path')}")
    
    res = cv2.matchTemplate(img_preproc, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    score = float(max_val)
    if score >= threshold:
        return (int(max_loc[0]), int(max_loc[1]))
    return None


# Color adjacency pattern matching function 
def _find_adjacent_colors(
    img,
    bgr_1,      
    bgr_2,
    bgr_1_tolerance=0,
    bgr_2_tolerance=0,
    run_length=1,
    shift_axis='x'
):
    """
    Find all adjacent color pairs of a certain length.
    Args:
        img (np.ndarray): BGR image to search.
        bgr_1: BGR color on the adjacent left or top side, depending on shift_axis.
        bgr_2: BGR color on the adjacent right or bottom side, depending on shift_axis.
        bgr_1_tolerance: tolerance for bgr_1,
        bgr_2_tolerance: tolerance for bgr_2,
        run_length: minimum number of adjacent pixels along opposite axis of shift_axis to validate a pair.
        shift_axis: 'x' to search horizontally (adjacent columns), 'y' to search vertically (adjacent rows).
    Returns:
        list[tuple]: list of (x, y) locations (may be empty).
    """

    # Build masks for both colors
    mask_bgr_1 = get_color_mask(img, bgr_1, tolerance=bgr_1_tolerance)
    mask_bgr_2 = get_color_mask(img, bgr_2, tolerance=bgr_2_tolerance)

    if mask_bgr_1 is None or mask_bgr_2 is None:
        raise ValueError("Two colors are required")

    H, W = mask_bgr_1.shape

    found_locations = []

    shift = 1
    border_shifted = np.zeros_like(mask_bgr_1)

    if shift_axis == 'x':
        # shift columns: move bgr_1 mask right by 1 pixel
        if shift < W:
            border_shifted[:, shift:] = mask_bgr_1[:, :-shift]
    elif shift_axis == 'y':
        # shift rows: move bgr_1 mask down by 1 pixel
        if shift < H:
            border_shifted[shift:, :] = mask_bgr_1[:-shift, :]
    else:
        raise ValueError(f"Invalid shift_axis: {shift_axis}")

    hits = cv2.bitwise_and(mask_bgr_2, border_shifted)
    bin_mask = (hits > 0).astype(np.int32)

    # For vertical adjacency (shift_axis == 'y') transpose so run detection logic stays the same
    proc = bin_mask if shift_axis == "x" else bin_mask.T
    Hp, Wp = proc.shape
    if run_length > Hp:
        return []

    csum = np.vstack([np.zeros((1, Wp), dtype=np.int32), proc.cumsum(axis=0, dtype=np.int32)])
    runs = csum[run_length:] - csum[:-run_length]

    ys, xs = np.where(runs == run_length)
    for y, x in zip(ys, xs):
        if shift_axis == 'x':
            found_locations.append((int(x), int(y)))
        elif shift_axis == 'y':
            # proc is transposed: original x = y, original y = x
            found_locations.append((int(y), int(x)))

    if not found_locations:
        return []

    # De-duplicate while preserving order
    uniq = list(dict.fromkeys(found_locations))
    return uniq


# -------------------------
# Image Locators
# -------------------------

def find_ally_locations(img):
    """
    Finds the location of an ally champion by using ally health bar and border colors.
    Args:
        img (np.ndarray): BGR image to search.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, HEALTH_LEFT_COLOR, ALLY_HEALTH_RIGHT_COLOR, bgr_1_tolerance=3, bgr_2_tolerance=3, run_length=4, shift_axis='x')
    if not locations:
        return []
    return [(x + 50, y + 160) for (x, y) in locations]


def find_enemy_locations(img):
    """
    Finds the location of an enemy champion by using enemy health bar and border colors.
    Args:
        img (np.ndarray): BGR image to search.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, HEALTH_LEFT_COLOR, ENEMY_HEALTH_RIGHT_COLOR, bgr_1_tolerance=3, bgr_2_tolerance=3, run_length=4, shift_axis='x')
    if not locations:
        return []
    return [(x + 50, y + 160) for (x, y) in locations]


def find_player_location(img):
    """
    Finds the location of the player champion by using enemy health bar and border colors.
    Args:
        img (np.ndarray): BGR image to search.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, HEALTH_LEFT_COLOR, PLAYER_HEALTH_RIGHT_COLOR, bgr_1_tolerance=3, bgr_2_tolerance=3, run_length=4, shift_axis='x')
    if not locations:
        return []
    first_location = locations[0]
    return (first_location[0] + 50, first_location[1] + 160)


def find_attached_ally_location(img):
    """
    Finds the location of an enemy champion by using enemy health bar and border colors.
    Args:
        img (np.ndarray): BGR image to search.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, ATTACHED_ALLY_LEFT_COLOR, ATTACHED_ALLY_RIGHT_COLOR, bgr_1_tolerance=3, bgr_2_tolerance=3, run_length=4, shift_axis='x')
    if not locations:
        return []
    first_location = locations[0]
    return (first_location[0] + 50, first_location[1] + 160)


def find_augment_location(img):
    """
    Finds the location of the augment by using hide augment button's inner and border colors.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, AUGMENT_UPPER_COLOR, AUGMENT_LOWER_COLOR, bgr_1_tolerance=3, bgr_2_tolerance=3, run_length=4, shift_axis='y')
    if not locations:
        return []
    first_location = locations[0]
    return (first_location[0], first_location[1] - 400)


def find_shop_location(img):
    """
    Finds the location of the shop by using hide shop button's inner and border colors.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, SHOP_UPPER_COLOR, SHOP_LOWER_COLOR, bgr_1_tolerance=2, bgr_2_tolerance=5, run_length=4, shift_axis='y')
    if not locations:
        return []
    first_location = locations[0]
    return (first_location[0], first_location[1])


def find_arena_exit_location(img):
    """
    Finds the location of the shop by using hide shop button's inner and border colors.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, ARENA_EXIT_UPPER_COLOR, ARENA_EXIT_LOWER_COLOR, bgr_1_tolerance=1, bgr_2_tolerance=0, run_length=4, shift_axis='y')
    if not locations:
        return []
    first_location = locations[0]
    return (first_location[0], first_location[1])


def find_shop_location_template(img):
    """Locate the `sell_btn` using template matching and return its center (x, y) in the image.
    """
    loc = find_template_match(img, id="sell_btn", threshold=0.95)
    if loc is None:
        return None
    x, y = loc
    return (int(x), int(y))


def find_augment_location_template(img):
    """Locate the `toggle_augments_btn` using template matching and return its center (x, y) in the image.
    """
    loc = find_template_match(img, id="toggle_augments_btn", threshold=0.98)
    if loc is None:
        return None
    x, y = loc
    return (int(x), int(y) - 400)


def find_arena_exit_location_template(img):
    """Locate the `arena_exit_btn` using template matching and return its center (x, y) in the image.
    """
    loc = find_template_match(img, id="arena_exit_btn", threshold=0.95)
    if loc is None:
        return None
    x, y = loc
    return (int(x), int(y))