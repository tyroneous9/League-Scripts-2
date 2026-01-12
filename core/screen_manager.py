import logging
import time
import os
import cv2
import dxcam


class ScreenManager:
    """
    DXGI-based screen capture manager using `dxcam`.
    Does NOT lock frame updates — latest frame may be corrupted if read during update.
    """

    def __init__(self):
        """
        Initialize the ScreenManager and begins capturing frames as BGR images.
        Args:
            target_fps (int): Frames per second to capture.
        """
        self._camera = dxcam.create(output_color="BGR")


    def is_capturing(self):
        """
        Returns whether the capture thread is running.
        """
        return self._camera.is_capturing
    

    def start_camera(self, target_fps=60):
        """
        Starts the capture thread.
        """
        
        self._camera.start(target_fps=target_fps)
        while self._camera.get_latest_frame() is None:
            time.sleep(0.01)


    def stop_camera(self):
        """
        Stops the capture thread and releases resources.
        """
        if self._camera:
            self._camera.stop()
            del self._camera
        else:
            logging.info("ScreenManager camera is not running, nothing to stop.")


    def get_latest_frame(self):
        """
        Returns the latest captured frame.
        """
        return self._camera.get_latest_frame()
    
    def grab(self):
        """
        Captures and returns the current frame without needing to start the camera.
        """
        return self._camera.grab()
    

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