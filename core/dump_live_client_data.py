"""
Script to retrieve all data from the League Live Client API and save it to a file in the docs folder.
"""

import json
import requests
from constants import LIVE_CLIENT_URL, DEFAULT_API_TIMEOUT
import os

def dump_live_client_data(output_file=None):
    """
    Retrieves all game data from the Live Client API and saves it to a JSON file in the docs folder.
    Args:
        output_file (str): Path to the output file.
    """
    docs_folder = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(docs_folder, exist_ok=True)
    if output_file is None:
        output_file = os.path.join(docs_folder, "live_client_data.json")
    else:
        output_file = os.path.join(docs_folder, output_file)

    try:
        res = requests.get(f"{LIVE_CLIENT_URL}/allgamedata", timeout=DEFAULT_API_TIMEOUT, verify=False)
        if res.status_code == 200:
            data = res.json()
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[INFO] Data saved to {output_file}")
        else:
            print(f"[ERROR] Failed to retrieve data. Status code: {res.status_code}")
    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}")

if __name__ == "__main__":
    dump_live_client_data()