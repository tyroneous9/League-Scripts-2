import time
import win32api
import win32con
import pyautogui
import pyperclip
import cv2

def print_color_on_click():
    print("[INFO] Listening for mouse clicks. Press Ctrl+C to stop.")
    prev_state = win32api.GetKeyState(win32con.VK_LBUTTON)
    while True:
        curr_state = win32api.GetKeyState(win32con.VK_LBUTTON)
        if prev_state >= 0 and curr_state < 0:  # Button was just pressed
            x, y = win32api.GetCursorPos()
            screenshot = pyautogui.screenshot()
            color = screenshot.getpixel((x, y))
            color_str = f"Mouse clicked at ({x}, {y}) - Color (RGB): {color}"
            print(color_str)
            pyperclip.copy(str(color))
        prev_state = curr_state

def hover_mouse_over_color(target_color, tolerance=30):
    print(f"[INFO] Searching for color {target_color}")
    while True:
        screenshot = pyautogui.screenshot()
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        lower = np.array([max(c - tolerance, 0) for c in target_color], dtype=np.uint8)
        upper = np.array([min(c + tolerance, 255) for c in target_color], dtype=np.uint8)
        mask = cv2.inRange(img, lower, upper)

        ys, xs = np.where(mask > 0)
        if ys.size > 0:
            location = (int(xs[0]), int(ys[0]))
            win32api.SetCursorPos(location)
            print(f"[INFO] Mouse moved to color at {location}")
        else:
            print("[INFO] Color not found on screen.")
        time.sleep(3)

if __name__ == "__main__":
    print("Tests starting.")