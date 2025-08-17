import requests
import win32gui
import win32api
import win32con
import time
import keyboard
import os
import mss
import numpy as np
import cv2
import logging
from constants import DEFAULT_API_TIMEOUT, LIVE_CLIENT_URL, TESSERACT_PATH
import pytesseract
from PIL import Image


# Mouse and Keyboard Actions
def click_percent(x_percent, y_percent, button="left"):
    hwnd = win32gui.GetForegroundWindow()  # Use the current active window
    if hwnd is None:
        print("[WARN] Window handle is None.")
        return
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    window_width = right - left
    window_height = bottom - top
    x = int(left + window_width * (x_percent / 100.0))
    y = int(top + window_height * (y_percent / 100.0))
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    win32api.SetCursorPos((x, y))
    if button == "left":
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
    elif button == "right":
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
    else:
        print(f"[WARN] Unknown mouse button: {button}. Use 'left' or 'right'.")

def click_percent_relative(x, y, x_offset_percent=0, y_offset_percent=0, button="left"):
    hwnd = win32gui.GetForegroundWindow()
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    window_width = right - left
    window_height = bottom - top

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

def click_absolute(x, y, button="left"):
    win32gui.ShowWindow(win32gui.GetForegroundWindow(), win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(win32gui.GetForegroundWindow())
    time.sleep(0.2)
    win32api.SetCursorPos((x, y))
    if button == "left":
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
    elif button == "right":
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
    else:
        print(f"[WARN] Unknown mouse button: {button}. Use 'left' or 'right'.")


def listen_for_exit_key():
    print("[INFO] Press the END key at any time to terminate the bot.")
    keyboard.wait("end")
    print("[INFO] END key pressed. Exiting.")
    os._exit(0)


# API Data Retrieval
def retrieve_game_data():
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

def poll_game_data(latest_game_data_container, poll_time=5):
    while True:
        latest_game_data_container['data'] = retrieve_game_data()
        time.sleep(poll_time)


# Screen Data Retrieval
def get_screenshot():
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Full screen; use sct.monitors[0] for all
        img = np.array(sct.grab(monitor))
        # Remove alpha channel if present
        if img.shape[2] == 4:
            img = img[:, :, :3]
        return img


def extract_screen_text():
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
    lines = extract_text_with_locations()
    for line_entries in lines.values():
        for entry in line_entries:
            if entry['text'].lower() == target_text.lower():
                logging.info(f"OCR: Found text '{target_text}' at location {entry['box']}")
                return entry['box']
    logging.info(f"OCR: Text '{target_text}' not found on screen.")
    return None


# Game Data Retrieval
def find_champion_location(health_bar_bgr, health_tick_bgr, tolerance=2):
    img = get_screenshot()

    lower_health_bar = np.array([max(c - tolerance, 0) for c in health_bar_bgr], dtype=np.uint8)
    upper_health_bar = np.array([min(c + tolerance, 255) for c in health_bar_bgr], dtype=np.uint8)
    mask_health_bar = cv2.inRange(img, lower_health_bar, upper_health_bar)

    lower_health_tick = np.array([max(c - tolerance, 0) for c in health_tick_bgr], dtype=np.uint8)
    upper_health_tick = np.array([min(c + tolerance, 255) for c in health_tick_bgr], dtype=np.uint8)
    mask_health_tick = cv2.inRange(img, lower_health_tick, upper_health_tick)

    search_size_x = 100
    height, width = mask_health_bar.shape

    for y in range(height):
        for x in range(width):
            if mask_health_bar[y, x] > 0:
                for dx in range(0, search_size_x + 1):
                    nx = x + dx
                    if nx < width and mask_health_tick[y, nx] > 0:
                        champion_location = (x+40, y+120)
                        return champion_location

    logging.debug("Health bar color not detected on screen or no valid champion location found.")
    return None

def get_relative_location(x, y, x_offset_percent=0, y_offset_percent=0):
    hwnd = win32gui.GetForegroundWindow()
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    window_width = right - left
    window_height = bottom - top

    new_x = x + int(window_width * (x_offset_percent / 100.0))
    new_y = y + int(window_height * (y_offset_percent / 100.0))
    return new_x, new_y

# Example usage:
# Move 50% screen width to the right from (x, y)
# new_x, new_y = get_relative_location(x, y, x_offset_percent=50)
