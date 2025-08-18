"""
Script to retrieve data from multiple League Client LCU API endpoints and save them to a file in the docs folder using lcu-driver.
"""

import json
import os
from lcu_driver import Connector

# List of endpoints to query (from run_client.py)
LCU_ENDPOINTS = [
    "/lol-summoner/v1/current-summoner",
    # This endpoint requires summonerId, will be handled after fetching summoner info
    # "/lol-champions/v1/inventories/{summoner_id}/champions-minimal",
    "/lol-champ-select/v1/session",
    "/lol-matchmaking/v1/ready-check",
    "/lol-gameflow/v1/gameflow-phase"
]

def save_data(data, output_file="lcu_data.json"):
    docs_folder = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(docs_folder, exist_ok=True)
    output_path = os.path.join(docs_folder, output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[INFO] Data saved to {output_path}")

connector = Connector()

@connector.ready
async def on_ready(connection):
    print("[INFO] Connected to League Client.")
    all_data = {}

    # Fetch /lol-summoner/v1/current-summoner first to get summonerId
    summoner_resp = await connection.request('get', LCU_ENDPOINTS[0])
    summoner_data = await summoner_resp.json()
    all_data[LCU_ENDPOINTS[0]] = summoner_data

    # Fetch /lol-champions/v1/inventories/{summoner_id}/champions-minimal
    summoner_id = summoner_data.get("summonerId")
    if summoner_id:
        champions_endpoint = f"/lol-champions/v1/inventories/{summoner_id}/champions-minimal"
        champions_resp = await connection.request('get', champions_endpoint)
        champions_data = await champions_resp.json()
        all_data[champions_endpoint] = champions_data
    else:
        all_data["/lol-champions/v1/inventories/{summoner_id}/champions-minimal"] = "summonerId not found"

    # Fetch remaining endpoints
    for endpoint in LCU_ENDPOINTS[1:]:
        resp = await connection.request('get', endpoint)
        try:
            data = await resp.json()
        except Exception:
            data = await resp.content()
        all_data[endpoint] = data

    save_data(all_data)
    await connector.stop()

if __name__ == "__main__":
    connector.start()