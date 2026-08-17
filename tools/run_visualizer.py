"""
Screenshot visualizer for the color-adjacency detectors in `utils/cv_utils.py`.

Captures a single screenshot, runs every registered detector against it, and
draws a generic bounding box at each detected location -- the drawing step
has no idea what a given detector was looking for, it just marks wherever a
detector returned a coordinate. The annotated screenshot is written to
`data/visualizations/`. Purely observational -- reads the screen only, never
moves the mouse or sends input.
"""

import os
import sys
import logging
from datetime import datetime

import cv2

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from core.screen_manager import ScreenManager
from utils.cv_utils import (
    find_player_location,
    find_ally_locations,
    find_enemy_locations,
    find_attached_ally_location,
    find_augment_location,
    find_shop_location,
    find_arena_exit_location,
)

logging.basicConfig(level=logging.INFO)

OUT_DIR = os.path.join(_repo_root, "data", "visualizations")

MARKER_COLOR = (0, 255, 0)
BOX_HALF_SIZE = 22

# Every detector to run. Each returns a single (x, y), a list of (x, y), or a
# falsy value if nothing was found -- the caller doesn't need to know which.
DETECTORS = [
    find_player_location,
    find_ally_locations,
    find_enemy_locations,
    find_attached_ally_location,
    find_augment_location,
    find_shop_location,
    find_arena_exit_location,
]


def _as_points(result):
    """Normalize a detector's return value into a list of (x, y) points."""
    if not result:
        return []
    if isinstance(result[0], (int, float)):
        return [result]
    return list(result)


def draw_detection(frame, x, y):
    """Marks a detected location with a generic box + crosshair, regardless of what was found."""
    cv2.rectangle(frame, (x - BOX_HALF_SIZE, y - BOX_HALF_SIZE), (x + BOX_HALF_SIZE, y + BOX_HALF_SIZE), MARKER_COLOR, 2)
    cv2.drawMarker(frame, (x, y), MARKER_COLOR, markerType=cv2.MARKER_CROSS, markerSize=12, thickness=1)


def main():
    sm = ScreenManager()
    frame = sm.grab()
    if frame is None:
        logging.error("Failed to capture a screenshot.")
        return

    annotated = frame.copy()
    total_hits = 0

    for finder in DETECTORS:
        try:
            result = finder(frame)
        except Exception:
            logging.exception("Detector '%s' failed", finder.__name__)
            continue

        points = _as_points(result)
        for x, y in points:
            draw_detection(annotated, int(x), int(y))
        total_hits += len(points)
        logging.info("%s: %d detection(s)", finder.__name__, len(points))

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"visualization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    cv2.imwrite(out_path, annotated)

    logging.info("Saved %d total detection(s) to %s", total_hits, out_path)


if __name__ == "__main__":
    main()
