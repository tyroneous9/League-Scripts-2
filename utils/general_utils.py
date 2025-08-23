import datetime
import os
import requests
import win32gui
import win32api
import win32con
import time
import keyboard
import mss
import numpy as np
import cv2
import logging
from core.constants import DEFAULT_API_TIMEOUT, LIVE_CLIENT_URL, TESSERACT_PATH
import pytesseract
from PIL import Image

# ===========================
# API Utilities
# ===========================


def retrieve_game_data():
    """
    Retrieves all game data from the League client API.
    Returns:
        dict or None: Game data if successful, else None.
    """
    try:
        res = requests.get(f"{LIVE_CLIENT_URL}/allgamedata", timeout=DEFAULT_API_TIMEOUT, verify=False)
        if res.status_code == 200:
            return res.json()
        else:
            print("[ERROR] Game data request failed.")
            return None
    except Exception as e:
        print(f"[ERROR] Game data request failed: {e}")
        return None


def poll_game_data(latest_game_data_container, stop_event, poll_time=2):
    """
    Continuously polls game data and updates the provided container.
    Exits when stop_event is set.
    Args:
        latest_game_data_container (dict): Container to store latest data.
        stop_event (threading.Event): Event to signal polling should stop.
        poll_time (int): Poll interval in seconds.
    """
    while not stop_event.is_set():
        latest_game_data_container['data'] = retrieve_game_data()
        time.sleep(poll_time)

    
# ===========================
# Mouse and Keyboard Actions
# ===========================


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
    hwnd = win32gui.GetForegroundWindow()
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    window_width = right - left
    window_height = bottom - top

    # Apply percent offset if provided
    new_x = x + int(window_width * (x_offset_percent / 100.0))
    new_y = y + int(window_height * (y_offset_percent / 100.0))

    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    win32api.SetCursorPos((new_x, new_y))
    if button == "left":
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, new_x, new_y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, new_x, new_y, 0, 0)
    elif button == "right":
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, new_x, new_y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, new_x, new_y, 0, 0)
    else:
        print(f"[WARN] Unknown mouse button: {button}. Use 'left' or 'right'.")

# Listen for the END key to terminate the bot
def listen_for_exit_key():
    """
    Listens for the END key and exits the program immediately.
    """
    logging.info("Press END key to exit anytime.")
    keyboard.wait("end")
    logging.info("END key pressed. Exiting program...")
    os._exit(0)


# ===========================
# Screen Data Retrieval & OCR
# ===========================

def get_screenshot():
    """
    Captures a screenshot of the primary monitor.
    Returns:
        np.ndarray: Screenshot image (BGR).
    """
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Full screen; use sct.monitors[0] for all
        img = np.array(sct.grab(monitor))
        # Remove alpha channel if present
        if img.shape[2] == 4:
            img = img[:, :, :3]
        return img


def extract_screen_text():
    """
    Extracts text from the current screen using Tesseract OCR.
    Returns:
        str: Extracted text.
    """
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    img = get_screenshot()

    # preprocessing
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img_thresh = cv2.threshold(img_gray, 70, 255, cv2.THRESH_BINARY)
    pil_img = Image.fromarray(img_thresh)
    # cv2.imwrite("preprocessed_image.jpg", img_thresh) 

    text = pytesseract.image_to_string(pil_img, config='--psm 11')
    print(text)
    return text


def extract_text_with_locations():
    """
    Extracts text and their bounding boxes from the screen using Tesseract OCR.
    Returns:
        dict: line_num -> list of {'text', 'box'}
    """
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    img = get_screenshot()

    # preprocessing
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img_thresh = cv2.threshold(img_gray, 70, 255, cv2.THRESH_BINARY)
    pil_img = Image.fromarray(img_thresh)
    # cv2.imwrite("preprocessed_image.jpg", img_thresh)

    data = pytesseract.image_to_data(pil_img, config='--psm 11', output_type=pytesseract.Output.DICT)

    text_locations = []
    n_boxes = len(data['text'])
    for i in range(n_boxes):
        text = data['text'][i].strip()
        if text:
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            text_locations.append({'text': text, 'box': (x, y, w, h)})

    lines = {}
    for entry in text_locations:
        line_num = data['line_num'][text_locations.index(entry)]
        if line_num not in lines:
            lines[line_num] = []
        lines[line_num].append(entry)

    return lines  # Dictionary: line_num -> list of {'text', 'box'}


def find_text_location(target_text):
    """
    Finds the location of the specified text on the screen using OCR.
    Args:
        target_text (str): Text to search for.
    Returns:
        tuple or None: (x, y, w, h) if found, else None.
    """
    lines = extract_text_with_locations()
    for line_entries in lines.values():
        for entry in line_entries:
            if entry['text'].lower() == target_text.lower():
                logging.info(f"OCR: Found text '{target_text}' at location {entry['box']}")
                return entry['box']
    logging.info(f"OCR: Text '{target_text}' not found on screen.")
    return None

# ===========================
# Client Utilities
# ===========================


# def bring_window_to_front(window_title):
#     """
#     Brings the specified window to the foreground.
#     Args:
#         window_title (str): The title of the window to bring to front.
#     Returns:
#         bool: True if successful, False otherwise.
#     """
#     hwnd = win32gui.FindWindow(None, window_title)
#     if not hwnd:
#         logging.warning(f"{window_title} window not found.")
#         return False
#     try:
#         win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
#         win32gui.SetForegroundWindow(hwnd)
#         return True
#     except Exception as e:
#         logging.error(f"Could not bring {window_title} to front: {e}")
#         return False


# def start_queue_loop():
#     """
#     Periodically brings the client to the front and clicks the queue button.
#     Args:
#         window_title (str): The title of the window to bring to front.
#     """
#     while True:
#         bring_window_to_front(LEAGUE_CLIENT_WINDOW_TITLE)
#         click_percent(40, 95)
#         time.sleep(3)


# ===========================
# Logging Utilities
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
