import datetime
import os
import threading
import psutil
import pywinctl
import pyautogui
import time
import keyboard
import logging


# ===========================
# Mouse and Keyboard Actions
# ===========================


def listen_for_exit(shutdown, shutdown_key="delete"):
    """
    Listens for the exit key and then sets the shutdown_event.
    """
    def _listener():
        logging.info(f"Press {shutdown_key.upper()} key to exit anytime.")
        keyboard.wait(shutdown_key)
        shutdown()
    exit_listener_thread = threading.Thread(target=_listener, daemon=True)
    exit_listener_thread.start()
    return exit_listener_thread
    

def click_percent(x, y, x_offset_percent=0, y_offset_percent=0, button="left"):
    """
    Clicks at (x, y) plus an optional offset specified as percent of window size.
    Args:
        x (int): Base X coordinate.
        y (int): Base Y coordinate.
        x_offset_percent (float): Offset in percent of window width.
        y_offset_percent (float): Offset in percent of window height.
        button (str): 'left' or 'right' mouse button.
    """
    window = pywinctl.getActiveWindow()
    if window is None:
        logging.warning("click_percent: no active window found.")
        return

    # Apply percent offset if provided
    new_x = x + int(window.width * (x_offset_percent / 100.0))
    new_y = y + int(window.height * (y_offset_percent / 100.0))

    pyautogui.moveTo(new_x, new_y)
    if button in ("left", "right"):
        pyautogui.mouseDown(button=button)
        time.sleep(0.05)
        pyautogui.mouseUp(button=button)
    else:
        logging.warning(f"Unknown mouse button: {button}. Use 'left' or 'right'.")


def move_mouse_percent(x, y, x_offset_percent=0, y_offset_percent=0):
    """
    Move the mouse cursor to (x, y) plus an optional offset specified as
    percent of the current foreground window size.

    Returns:
        tuple: the final (x, y) coordinates the cursor was moved to.
    """
    window = pywinctl.getActiveWindow()
    if window is None:
        logging.warning("move_mouse_percent: no active window found.")
        return None

    # Apply percent offset if provided
    new_x = x + int(window.width * (x_offset_percent / 100.0))
    new_y = y + int(window.height * (y_offset_percent / 100.0))

    pyautogui.moveTo(new_x, new_y)

    return (new_x, new_y)


def click_on_cursor(button="left"):
    """
    Simulates a mouse click at the current cursor position.
    """
    button_aliases = {"left": "left", "right": "right", "middle": "middle", "mmb": "middle", "mouse_middle": "middle"}
    pyautogui_button = button_aliases.get(button)
    if pyautogui_button is None:
        logging.warning("Unknown mouse button: %s. Use 'left', 'right', or 'middle'.", button)
        return
    try:
        pyautogui.click(button=pyautogui_button)
    except Exception:
        logging.error("click_on_cursor: unexpected error while clicking (button=%s)", button)
        raise Exception


def get_binding(event_name, keybinds):
    """Resolve a single binding for `event_name` from the `keybinds` map.

    - `keybinds` should be the `Keybinds` mapping from the config.
    - Backwards-compat: if the stored value is a list, the first entry is used.
    Returns the binding (dict or string) or None if not found/empty.
    """
    # Assume `keybinds` is a dict of event -> list (0 or 1) of parsed dicts.
    b = keybinds.get(event_name)
    if not b:
        return None
    # Return the first binding
    return b[0]


def send_keybind(event_name, keybinds, press_time=0.01):
    """Resolve and send the binding for `event_name` using the provided `keybinds` map.

    'keybinds' must refer to the dict holding the keybinds obtained via live data.
    """
    try:
        # Backwards-compatible path: callers may pass a pre-resolved binding
        if isinstance(keybinds, dict) and keybinds.get('__internal__'):
            binding = event_name
        else:
            binding = get_binding(event_name, keybinds)

        if binding is None:
            logging.debug("send_keybind: no binding for %s", event_name)
            return False

        # Core send logic (previously in _send_keybind)
        keybind_type = binding['type']
        modifiers = [m.lower() for m in binding.get('modifiers', [])]

        if keybind_type == 'mouse':
            btn = binding.get('mouse', 'left').lower()
            # press modifiers, click, release modifiers
            for m in modifiers:
                keyboard.press('ctrl' if m == 'control' else ('win' if m in ('win','windows') else m))
            if 'right' in btn or '2' in btn or 'button2' in btn:
                click_on_cursor('right')
            elif 'middle' in btn or '3' in btn or 'button3' in btn:
                click_on_cursor('middle')
            else:
                click_on_cursor('left')
            for m in modifiers:
                keyboard.release('ctrl' if m == 'control' else ('win' if m in ('win','windows') else m))
            return True

        key = binding.get('key', '').lower()
        for m in modifiers:
            keyboard.press('ctrl' if m == 'control' else ('win' if m in ('win','windows') else m))
        if key:
            keyboard.press(key)
            time.sleep(press_time)
            keyboard.release(key)
        else:
            time.sleep(press_time)
        for m in modifiers:
            keyboard.release('ctrl' if m == 'control' else ('win' if m in ('win','windows') else m))
        return True

    except Exception as e:
        logging.exception("send_keybind failed for %s: %s", event_name, e)
        return False


# ===========================
# Mouse and Keyboard Actions
# ===========================


def wait_for_window(window_title, timeout=60):
    """
    Waits for a window with the specified title to appear.
    Returns:
        pywinctl.Window | None: Window object if found, otherwise None.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        windows = pywinctl.getWindowsWithTitle(window_title)
        if windows:
            return windows[0]
        time.sleep(1)

    logging.info(f"Window '{window_title}' is closed.")
    return None


def bring_window_to_front(window_title, timeout=60, retry_delay=0.5):
    """
    Finds a window by title and repeatedly attempts to bring it to the foreground
    until successful or until timeout is reached.

    Args:
        window_title (str): Title of the window.
        timeout (int): Maximum time to keep trying (seconds).
        retry_delay (float): Delay between attempts (seconds).

    Returns:
        pywinctl.Window | None: Window object if successful, otherwise None.
    """
    end_time = time.time() + timeout

    while time.time() < end_time:
        windows = pywinctl.getWindowsWithTitle(window_title)
        window = windows[0] if windows else None

        if window is None:
            time.sleep(retry_delay)
            continue

        try:
            # Restore if minimized
            window.restore(wait=True)
            time.sleep(0.1)

            window.activate(wait=True)
            return window  # success

        except Exception as e:
            logging.debug(
                f"Failed to bring '{window_title}' to front: {e}"
            )

        time.sleep(retry_delay)

    logging.error(
        f"Failed to bring window '{window_title}' to front after {timeout} seconds."
    )
    return None


def terminate_window(window_title):
    windows = pywinctl.getWindowsWithTitle(window_title)
    if windows:
        pid = windows[0].getPID()
        if pid is None:
            logging.error(f"Failed to get PID for window '{window_title}'.")
            return
        try:
            proc = psutil.Process(pid)
            proc.terminate()  # or proc.kill() for immediate termination
            logging.info(f"Process {pid} terminated for window '{window_title}'.")
        except Exception as e:
            logging.error(f"Failed to terminate process {pid}: {e}")
    else:
        logging.warning(f"Window '{window_title}' not found.")


# ===========================
# Other
# ===========================


def enable_logging(log_file=None, level=logging.INFO):
    # Remove all handlers associated with the root logger object
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    if log_file is None:
        if not os.path.exists("logs"):
            os.makedirs("logs")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        log_file = f"logs/{timestamp}.log"
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )