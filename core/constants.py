# ==========================================================
# Project-wide constants
# ==========================================================

import win32api
import os
import sys
from pathlib import Path


# ===========================
# League General
# ===========================
LEAGUE_CLIENT_WINDOW_TITLE = "League of Legends"
LEAGUE_GAME_WINDOW_TITLE = "League of Legends (TM) Client"

SUPPORTED_MODES = {
    "arena": {
        "module": "core.run_arena",
        "queue_id": 1700
    },
    "aram": {
        "module": "core.run_aram",
        "queue_id": 450
    },
    "test": {
        "module": "core.run_test",
        "queue_id": -1
    },
    "yuumi_sr": {
        "module": "core.run_yuumi_sr",
        "queue_id": -1
    }
    # For a list of Queue IDs, visit https://static.developer.riotgames.com/docs/lol/queues.json
}

# AFK timeout (seconds). The true timeout is 60 seconds, but a lower value is used to be safe.
AFK_TIMEOUT = 50

# ===========================
# Ingame Color Definitions (BGR)
# ===========================

# Colors for CV detection
TEST_COLOR = (27, 38, 154)  # Configurable color for testing
HEALTH_LEFT_COLOR = (8, 4, 8) # Black HEX: #080408
PLAYER_HEALTH_RIGHT_COLOR = (66, 199, 66) # Green HEX: #42C742
ENEMY_HEALTH_RIGHT_COLOR = (90, 101, 206) # Red HEX: #CE655A
ALLY_HEALTH_RIGHT_COLOR = (247, 186, 66)  # Blue HEX: #42BAF7
AUGMENT_UPPER_COLOR = (140, 117, 8) # Blue HEX: #08758C
AUGMENT_LOWER_COLOR = (205, 177, 102) # Light Blue HEX: #66B1CD
SHOP_UPPER_COLOR = (36,29,23) # Dark gray HEX: #171D24
SHOP_LOWER_COLOR = (86,84,85) # Light gray HEX: #555456
ARENA_EXIT_UPPER_COLOR = (81,119,137) # gold HEX: #897751
ARENA_EXIT_LOWER_COLOR = (41,32,24) # dark blue HEX: #182029
ATTACHED_ALLY_LEFT_COLOR = (222,97,99) # light purple HEX: #6361DE
ATTACHED_ALLY_RIGHT_COLOR = (140,55,55) # dark purple HEX: #37378C


# ===========================
# League APIs
# ===========================

# Default timeout for API calls (seconds)
DEFAULT_API_TIMEOUT = 60

# LiveClientData
LIVE_CLIENT_URL = "https://127.0.0.1:2999/liveclientdata"

# LCU
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
    "PRE_END_OF_GAME": "PreEndOfGame",
    "END_OF_GAME": "EndOfGame",
}
CHAMP_SELECT_SUBPHASES = {
    "BAN_PICK": "BAN_PICK"
}

# Data Dragon
DATA_DRAGON_VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
DATA_DRAGON_DEFAULT_LOCALE = "en_US"


# ===========================
# Screen Information
# ===========================

# Tolerance for color masking
THRESHHOLD = 70

# Get screen dimensions using win32api
SCREEN_WIDTH = win32api.GetSystemMetrics(0)
SCREEN_HEIGHT = win32api.GetSystemMetrics(1)
SCREEN_CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)


# Parameters for the hybrid pixel->game units predictor (kept as constants for stability)
GAME_DISTANCE_PARAMS = {
    "unit_scale": 1.1272789362463531,
    "v_top": 0.40579309745655007,
    "v_bottom": -0.18471266892028299,
    "wiggle_coeff": 0.0,
    "k_sep": 0.2766888164988386,
    "max_sep_mult": 1.3276067468392727,
    "pos_multiplier_min": 0.15,
}

# ===========================
# Paths
# ===========================


# Templates

if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
    TEMPLATES_DIR = Path(sys._MEIPASS) / "templates"
else:
    TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
TEMPLATES_INDEX_PATH = TEMPLATES_DIR / "index.json"

# Config
if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
    CONFIG_DIR = Path(sys._MEIPASS) / "config"
else:
    CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
CONFIG_PATH = CONFIG_DIR / "config.json"



