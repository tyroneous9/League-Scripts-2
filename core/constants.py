# ==========================================================
# Project-wide constants
# ==========================================================

import win32api


# ===========================
# League General
# ===========================
LEAGUE_CLIENT_WINDOW_TITLE = "League of Legends"

SUPPORTED_MODES = {
    "arena": {
        "module": "core.run_arena",
        "queue_id": 1700
    },
    "aram": {
        "module": "core.run_aram",
        "queue_id": 450
    },
    "swiftplay": {
        "module": "core.run_swiftplay",
        "queue_id": 490
    },
    # Add more modes as needed
}


# ===========================
# Ingame Color Definitions (BGR)
# ===========================

# Health bar colors
HEALTH_TICK_COLOR = (0, 0, 0)            # Black
PLAYER_HEALTH_BAR_COLOR = (107, 217, 99) # Green
ENEMY_HEALTH_BAR_COLOR = (101, 112, 200) # Red
ALLY_HEALTH_BAR_COLOR = (242, 189, 110)  # Blue


# ===========================
# League API
# ===========================

# LiveClientData API URL
LIVE_CLIENT_URL = "https://127.0.0.1:2999/liveclientdata"

# LCU Endpoints
LCU_MATCHMAKING_READY_CHECK = "/lol-matchmaking/v1/ready-check"
LCU_CHAMP_SELECT_SESSION = "/lol-champ-select/v1/session"
LCU_GAMEFLOW_PHASE = "/lol-gameflow/v1/gameflow-phase"
LCU_SUMMONER = "/lol-summoner/v1/current-summoner"
LCU_CHAMPIONS_MINIMAL = "/lol-champions/v1/inventories/{summoner_id}/champions-minimal"

GAMEFLOW_PHASES = {
    "NONE": "None",
    "LOBBY": "Lobby",
    "READY_CHECK": "ReadyCheck",
    "CHAMP_SELECT": "ChampionSelect",
    "GAME_START": "GameStart",
    "IN_PROGRESS": "InProgress",
    "END_OF_GAME": "EndOfGame",
}
CHAMP_SELECT_SUBPHASES = {
    "BAN_PICK": "BAN_PICK"
}


# ===========================
# Timeouts and Delays
# ===========================

# Default timeout for API calls (seconds)
DEFAULT_API_TIMEOUT = 1

# Default key press delay for pywin32 input simulation (seconds)
KEY_PRESS_DELAY = 0.05


# ===========================
# Screen Geometry
# ===========================

# Get screen dimensions using win32api
screen_width = win32api.GetSystemMetrics(0)
screen_height = win32api.GetSystemMetrics(1)
SCREEN_CENTER = (screen_width // 2, screen_height // 2)

# ===========================
# OCR Configuration
# ===========================

# Tesseract OCR executable path
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


