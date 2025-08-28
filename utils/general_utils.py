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
from core.constants import (
    DEFAULT_API_TIMEOUT, LIVE_CLIENT_URL, TESSERACT_PATH,
    DATA_DRAGON_VERSIONS_URL, DATA_DRAGON_DEFAULT_LOCALE
)
import pytesseract
from PIL import Image

# ===========================
# API Utilities
# ===========================


def fetch_live_client_data():
    """
    Retrieves all game data from the live client API.
    Returns:
        dict or None: Game data if successful, else None.
    """
    try:
        res = requests.get(f"{LIVE_CLIENT_URL}/allgamedata", timeout=DEFAULT_API_TIMEOUT, verify=False)
        if res.status_code == 200:
            return res.json()
        else:
            print("[ERROR] Game data request succeeded, but no data available.")
            return None
    except Exception as e:
        print(f"[ERROR] Game data request failed.")
        return None


def poll_live_client_data(latest_game_data_container, stop_event, poll_time=0.2):
    """
    Continuously polls live client data and updates the provided container.
    Exits when stop_event is set.
    Args:
        latest_game_data_container (dict): Container to store latest data.
        stop_event (threading.Event): Event to signal polling should stop.
        poll_time (int): Poll interval in seconds.
    """
    while not stop_event.is_set():
        latest_game_data_container['data'] = fetch_live_client_data()
        time.sleep(poll_time)


def fetch_data_dragon_data(endpoint, version=None, locale=DATA_DRAGON_DEFAULT_LOCALE):
    """
    Fetches static data from Riot Data Dragon.
    Args:
        endpoint (str): The endpoint, e.g. "champion".
        version (str, optional): Patch version. If None, fetches latest.
        locale (str): Language code, default from constants.
    Returns:
        dict: The JSON data from Data Dragon, or {} on failure.
    """
    try:
        if not version:
            versions = requests.get(DATA_DRAGON_VERSIONS_URL, timeout=5).json()
            version = versions[0]
        url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/{locale}/{endpoint}.json"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error(f"Failed to fetch Data Dragon data for endpoint '{endpoint}': {e}")
        return {}

def get_champions_map():
    """
    Fetches champion data from Riot Data Dragon and returns a {name: id} mapping.
    Returns:
        dict: {champion_name: champion_id}
    """
    data = fetch_data_dragon_data("champion")
    champions_map = {}
    for champ in data.get("data", {}).values():
        champions_map[champ["name"]] = int(champ["key"])
    return champions_map


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


def click_on_cursor(button="left"):
    """
    Simulates a mouse click at the current cursor position.
    """
    x, y = win32api.GetCursorPos()
    if button == "left":
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    elif button == "right":
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
    else:
        print(f"[WARN] Unknown mouse button: {button}. Use 'left' or 'right'.")
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


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
# Screen Data
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
    cv2.imwrite("preprocessed_image.jpg", img_thresh) 

    text = pytesseract.image_to_string(pil_img, config='--psm 11')
    logging.info(text)
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


def bring_window_to_front(window_title):
    """
    Finds the window by title and brings it to the foreground.
    Args:
        window_title (str): The title of the window.
    """
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.1)
        win32gui.SetForegroundWindow(hwnd)
    else:
        logging.warning(f"Window with title '{window_title}' not found.")

def wait_for_window(window_title, timeout=60):
    """
    Waits for a window with the given title to appear within the timeout period.
    If found, brings it to the foreground.
    Args:
        window_title (str): The title of the window to wait for.
        timeout (int): Maximum time to wait in seconds.
    Returns:
        int or None: Window handle if found, else None.
    """
    hwnd = None
    for _ in range(timeout):
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            bring_window_to_front(window_title)
            return hwnd
        time.sleep(1)
    logging.warning(f"Window with title '{window_title}' not found after {timeout} seconds.")
    return
