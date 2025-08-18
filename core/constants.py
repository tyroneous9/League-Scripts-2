# ==========================================================
# Project-wide constants
# ==========================================================

import win32api

# ===========================
# API Endpoints
# ===========================

# Riot's LiveClientData API URL
LIVE_CLIENT_URL = "https://127.0.0.1:2999/liveclientdata"

# Riot LCU WebSocket endpoints
LCU_MATCHMAKING_READY_CHECK = "/lol-matchmaking/v1/ready-check"
LCU_CHAMP_SELECT_SESSION = "/lol-champ-select/v1/session"
LCU_GAMEFLOW_PHASE = "/lol-gameflow/v1/gameflow-phase"

# ===========================
# Timeouts and Delays
# ===========================

# Default timeout for API calls (seconds)
DEFAULT_API_TIMEOUT = 1

# Default key press delay for pywin32 input simulation (seconds)
KEY_PRESS_DELAY = 0.05

# ===========================
# Supported Game Modes
# ===========================

# Maps mode names to their runner scripts
SUPPORTED_MODES = {
    "arena": ["python", "core/run_arena.py"],
    # "aram": ["python", "core/run_aram.py"],
    # "swiftplay": ["python", "core/run_swiftplay.py"],
}

# ===========================
# Color Definitions (BGR)
# ===========================

# Health bar and tick colors for image recognition
HEALTH_TICK_COLOR = (0, 0, 0)            # Black
PLAYER_HEALTH_BAR_COLOR = (107, 217, 99) # Green
ENEMY_HEALTH_BAR_COLOR = (101, 112, 200) # Red
ALLY_HEALTH_BAR_COLOR = (242, 189, 110)  # Blue

# ===========================
# Screen Geometry
# ===========================

# Get screen dimensions using win32api
screen_width = win32api.GetSystemMetrics(0)
screen_height = win32api.GetSystemMetrics(1)
SCREEN_CENTER = (screen_width // 2, screen_height // 2)

# ===========================
# Logging
# ===========================

# Log file name for main logging output
LOG_FILE_NAME = "main_log.log"

# ===========================
# OCR Configuration
# ===========================

# Tesseract OCR executable path
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ===========================
# League Client Window Title
# ===========================
LEAGUE_CLIENT_WINDOW_TITLE = "League of Legends"

