import logging
import threading
import time
import os
import cv2
import mss
import numpy as np


class ScreenManager:
    """
    mss-based screen capture manager (Windows and Linux).
    Does NOT lock frame updates — latest frame may be corrupted if read during update.
    """

    def __init__(self):
        """
        Initialize the ScreenManager. Call `start_camera` to begin capturing
        frames as BGR images on a background thread.
        """
        self._thread = None
        self._stop_event = threading.Event()
        self._latest_frame = None

    def is_capturing(self):
        """
        Returns whether the capture thread is running.
        """
        return self._thread is not None and self._thread.is_alive()

    def start_camera(self, target_fps=60):
        """
        Starts the capture thread.
        """
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, args=(target_fps,), daemon=True)
        self._thread.start()
        while self.get_latest_frame() is None:
            time.sleep(0.01)

    def stop_camera(self):
        """
        Stops the capture thread and releases resources.
        """
        if self._thread is not None:
            self._stop_event.set()
            self._thread.join()
            self._thread = None
        else:
            logging.info("ScreenManager camera is not running, nothing to stop.")

    def _capture_loop(self, target_fps):
        interval = 1.0 / target_fps if target_fps > 0 else 0
        with mss.MSS() as sct:
            monitor = sct.monitors[1]
            while not self._stop_event.is_set():
                loop_start = time.time()
                shot = sct.grab(monitor)
                self._latest_frame = np.array(shot)[:, :, :3]
                elapsed = time.time() - loop_start
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def get_latest_frame(self):
        """
        Returns the latest captured frame.
        """
        return self._latest_frame

    def grab(self):
        """
        Captures and returns the current frame without needing to start the camera.
        """
        with mss.MSS() as sct:
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            return np.array(shot)[:, :, :3]

    def save_screenshot(self, file_name="screenshot"):
        """
        Capture a single frame (via `get_screenshot`) and save it to the `temp/`
        directory as a PNG with a timestamped filename.

        Returns:
            str | None: full path to written file on success, else None.
        """
        frame = self.get_latest_frame()
        if frame is None:
            logging.error("No frame captured; not saving screenshot.")
            return None

        out_dir = os.path.join("temp")
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            logging.exception("Failed to create temp directory")
            return None

        filename = f"{file_name}_.png"
        out_path = os.path.join(out_dir, filename)
        try:
            # frame is BGR; write directly
            ok = cv2.imwrite(out_path, frame)
            if not ok:
                logging.error("cv2.imwrite failed for %s", out_path)
                return None
            return out_path
        except Exception:
            logging.exception("Failed to write screenshot to disk")
            return None
