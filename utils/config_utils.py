import json
import os
import re
from core.constants import CONFIG_DIR, CONFIG_PATH

def load_config(path=CONFIG_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing config at {path}")
    with open(path, "r") as f:
        return json.load(f)


def save_config(config, path=CONFIG_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=4)


def load_settings():
    config = load_config()
    parsed = config.get("Keybinds")
    if parsed is not None:
        return parsed, config.get("General", {})
    return config.get("Keybinds", {}), config.get("General", {})

def get_selected_game_mode():
    config = load_config()
    return config.get("General", {}).get("selected_game_mode").lower()

def set_selected_game_mode(mode):
    config = load_config()
    config["General"]["selected_game_mode"] = mode
    save_config(config)


def parse_lcu_input_settings(input_json: dict) -> dict:
    """Parse the LCU `/lol-game-settings/v1/input-settings` structure into
    a normalized mapping of event -> list of binding objects.

    Binding object schema:
      - type: 'key' or 'mouse'
      - key: normalized key name (for type=='key')
      - mouse: 'left'|'right'|'middle' (for type=='mouse')
      - modifiers: list of modifier names (['shift','ctrl','alt','win'])
      - raw: original raw binding string
    """
    parsed = {}

    def parse_single_binding(raw_binding: str):
        tokens = re.findall(r"\[([^\]]*)\]", raw_binding)
        if not tokens:
            return None
        if any(t.strip().lower() == '<unbound>' for t in tokens):
            return None

        modifiers = []
        key = None
        mouse = None

        for t in tokens:
            tt = t.strip()
            tl = tt.lower()
            # Modifiers
            if tl in ('shift', 'ctrl', 'control', 'alt', 'altgr', 'win', 'windows', 'cmd', 'meta'):
                if tl in ('control',):
                    modifiers.append('ctrl')
                elif tl in ('win', 'windows'):
                    modifiers.append('win')
                else:
                    modifiers.append('shift' if tl == 'shift' else ('alt' if 'alt' in tl else tl))
                continue

            # Mouse buttons
            if tl.startswith('button') or 'mouse' in tl:
                # 'Button 1' => left, 'Button 2' => right, 'Button 3' => middle
                m = re.search(r'button\s*(\d)', tl)
                if m:
                    num = m.group(1)
                    if num == '1':
                        mouse = 'left'
                    elif num == '2':
                        mouse = 'right'
                    else:
                        mouse = 'middle'
                    continue
                if 'left' in tl:
                    mouse = 'left'
                    continue
                if 'right' in tl:
                    mouse = 'right'
                    continue
                if 'middle' in tl:
                    mouse = 'middle'
                    continue

            # Otherwise treat as key (normalize common names)
            def _normalize_key_name_local(raw: str) -> str:
                s = raw.strip().lower()
                mappings = {
                    'space': 'space',
                    'return': 'enter',
                    'enter': 'enter',
                    'down arrow': 'down',
                    'up arrow': 'up',
                    'left arrow': 'left',
                    'right arrow': 'right',
                    'escape': 'esc',
                    'esc': 'esc',
                    'backspace': 'backspace',
                    'tab': 'tab',
                    '`': '`',
                    'tilde': '`',
                }
                if s in mappings:
                    return mappings[s]
                if re.fullmatch(r'f\d{1,2}', s):
                    return s
                if len(s) == 1:
                    return s
                return s.replace(' ', '_')

            key = _normalize_key_name_local(tt)

        if mouse:
            return {'type': 'mouse', 'mouse': mouse, 'modifiers': modifiers, 'raw': raw_binding}
        if key:
            return {'type': 'key', 'key': key, 'modifiers': modifiers, 'raw': raw_binding}
        return None

    # LCU layout often nests GameEvents, HUDEvents, Quickbinds, ShopEvents
    for section in ('GameEvents', 'HUDEvents', 'Quickbinds', 'ShopEvents'):
        sec = input_json.get(section, {})
        for evt, val in sec.items():
            # val may be a string with multiple bindings separated by commas
            if not isinstance(val, str):
                parsed[evt] = []
                continue
            bindings = []
            parts = [p.strip() for p in val.split(',') if p.strip()]
            for part in parts:
                b = parse_single_binding(part)
                if b:
                    bindings.append(b)
            parsed[evt] = bindings

    return parsed

def save_parsed_keybinds(parsed: dict):
    """Save parsed bindings directly into config.json under the key 'Keybinds'."""
    config = load_config()
    config['Keybinds'] = parsed
    save_config(config)
