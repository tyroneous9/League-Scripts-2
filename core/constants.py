# Shared constants used across the project
import win32api

# Riot's LiveClientData API URL (use HTTPS as discussed)
LIVE_CLIENT_URL = "https://127.0.0.1:2999/liveclientdata"

# Riot LCU WebSocket endpoints (optional for expansion)
LCU_MATCHMAKING_READY_CHECK = "/lol-matchmaking/v1/ready-check"
LCU_CHAMP_SELECT_SESSION = "/lol-champ-select/v1/session"
LCU_GAMEFLOW_PHASE = "/lol-gameflow/v1/gameflow-phase"

# Default timeout for API calls
DEFAULT_API_TIMEOUT = 1

# Optional: Define default key press delay for pywin32 input simulation
KEY_PRESS_DELAY = 0.05

SUPPORTED_MODES = {
    "Arena": ["python", "core/run_arena.py"],
    # "ARAM": ["python", "core/run_aram.py"],
    # "Swiftplay": ["python", "core/run_swiftplay.py"],
}

# Colors (BGR)
HEALTH_TICK_COLOR = (0, 0, 0) # Black
PLAYER_HEALTH_BAR_COLOR = (107, 217, 99) # Green
ENEMY_HEALTH_BAR_COLOR = (101, 112, 200) # Red
ALLY_HEALTH_BAR_COLOR = (242, 189, 110) # Blue
SHOP_BODY_COLOR = (55, 47, 6)      # Dark blue
SHOP_BORDER_COLOR = (52, 93, 121)  # Gold

# Screen dimensions
screen_width = win32api.GetSystemMetrics(0)
screen_height = win32api.GetSystemMetrics(1)
SCREEN_CENTER = (screen_width // 2, screen_height // 2)

# Log file name
LOG_FILE_NAME = "main_log.log"

# Tesseract OCR executable path
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

