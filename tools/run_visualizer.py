"""
Live visual overlay for the color-adjacency detectors in `utils/cv_utils.py`.

Captures the screen, runs the selected detector(s) every frame, and draws a
marker at each detected location so you can see what the bot "sees" in real
time. Purely observational — reads the screen only, never moves the mouse or
sends input.

Focus the preview window and press a number key to toggle a detector:
  1 Player   2 Allies       3 Enemies     4 Attached ally
  5 Augment  6 Shop         7 Arena exit
  Q / ESC to quit.
"""

import os
import sys
import time
import logging

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

WINDOW_NAME = "INTAI Detection Visualizer"
DISPLAY_SCALE = 0.5  # shrink the captured frame before drawing/showing it

# (label, toggle key, BGR color, detector fn, "point" | "points")
DETECTORS = [
    ("Player",        ord('1'), (0, 255, 255),   find_player_location,        "point"),
    ("Allies",        ord('2'), (255, 200, 0),   find_ally_locations,         "points"),
    ("Enemies",       ord('3'), (0, 0, 255),     find_enemy_locations,        "points"),
    ("Attached ally", ord('4'), (255, 0, 255),   find_attached_ally_location, "point"),
    ("Augment",       ord('5'), (0, 200, 0),     find_augment_location,       "point"),
    ("Shop",          ord('6'), (200, 200, 200), find_shop_location,          "point"),
    ("Arena exit",    ord('7'), (0, 165, 255),   find_arena_exit_location,    "point"),
]


def draw_marker(frame, x, y, color, label):
    cv2.drawMarker(frame, (x, y), color, markerType=cv2.MARKER_CROSS, markerSize=18, thickness=2)
    cv2.circle(frame, (x, y), 14, color, 2)
    cv2.putText(frame, label, (x + 16, y - 10), cv2.FONT_H0ERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)


def draw_legend(frame, enabled):
    y = 20
    for label, key, color, _, _ in DETECTORS:
        state = "ON" if enabled[key] else "off"
        cv2.putText(frame, f"[{chr(key)}] {label}: {state}", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color if enabled[key] else (90, 90, 90), 1, cv2.LINE_AA)
        y += 20


def main():
    sm = ScreenManager()
    sm.start_camera(target_fps=60)

    enabled = {key: True for _, key, _, _, _ in DETECTORS}

    logging.info("Visualizer running. Focus the preview window, press number keys to toggle detectors, Q/ESC to quit.")

    prev_time = time.time()
    fps = 0.0

    try:
        while True:
            frame = sm.get_latest_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            display = frame.copy()

            for label, key, color, finder, kind in DETECTORS:
                if not enabled[key]:
                    continue
                try:
                    result = finder(frame)
                except Exception:
                    logging.exception("Detector '%s' failed", label)
                    continue
                if not result:
                    continue
                points = result if kind == "points" else [result]
                for x, y in points:
                    draw_marker(display, int(x), int(y), color, label)

            draw_legend(display, enabled)

            now = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev_time, 1e-6))
            prev_time = now
            cv2.putText(display, f"FPS: {fps:.0f}", (10, display.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

            if DISPLAY_SCALE != 1.0:
                display = cv2.resize(display, None, fx=DISPLAY_SCALE, fy=DISPLAY_SCALE)

            cv2.imshow(WINDOW_NAME, display)
            k = cv2.waitKey(1) & 0xFF
            if k in (27, ord('q')):
                break
            if k in enabled:
                enabled[k] = not enabled[k]

    except KeyboardInterrupt:
        pass
    finally:
        sm.stop_camera()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
