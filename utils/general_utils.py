import sys
import win32gui
import win32api
import win32con
import time
import keyboard
import mss
import numpy as np
import cv2
import logging
from core.constants import TESSERACT_PATH
import pytesseract
from PIL import Image

# ===========================
# Mouse and Keyboard Actions
# ===========================

# Click at a position specified by percent of screen size (absolute)
def click_percent_absolute(x_percent, y_percent, button="left"):
    """
    Clicks at a position specified by x_percent and y_percent of the foreground window size.
    Args:
        x_percent (float): X position as percent of window width.
        y_percent (float): Y position as percent of window height.
        button (str): 'left' or 'right' mouse button.
    """
    hwnd = win32gui.GetForegroundWindow()
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

# Click at an absolute position, with optional percent offset
def click_percent_relative(x, y, x_offset_percent=0, y_offset_percent=0, button="left"):
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
    keyboard.wait("end")
    logging.info("END key pressed. Exiting program...")
    sys.exit(0)


# ===========================
# Screen Data Retrieval & OCR
# ===========================

# Take a screenshot of the primary monitor
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

# Extract text from the screen using OCR
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

# Extract text and their locations from the screen using OCR
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

# Find the location of a specific text on the screen
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

