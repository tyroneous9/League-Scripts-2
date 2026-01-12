import asyncio
import logging
import random
import time

from lcu_driver import Connector
from utils.config_utils import get_selected_game_mode, load_config, parse_lcu_input_settings, save_parsed_keybinds
from utils.general_utils import bring_window_to_front, wait_for_window
from utils.game_utils import get_champions_map
from utils.cv_utils import load_template_cache
from core.constants import (
    LEAGUE_GAME_WINDOW_TITLE,
    SUPPORTED_MODES,
    LCU_GAMEFLOW_PHASE,
    LCU_CHAMP_SELECT_SESSION,
    LEAGUE_CLIENT_WINDOW_TITLE,
    GAMEFLOW_PHASES,
    CHAMP_SELECT_SUBPHASES,
)
from core.bot_manager import BotManager

class LCUManager:
    """Encapsulates the lcu_driver Connector and its event handlers."""

    def __init__(self, shutdown_event):
        self.shutdown_event = shutdown_event
        self.connector = Connector()
        self.bot_manager = BotManager(self.shutdown_event)
        self.last_phase = None
        self.champions_map = get_champions_map()
        # Event used to pause/resume handlers; set => handlers can run, clear => handlers paused
        self.handlers_can_run = asyncio.Event()
        self.handlers_can_run.set()
        self._register_handlers()

    def _register_handlers(self):
        # Register handlers that respect the `handlers_can_run` event themselves.
        async def _connect(connection):
            await self.handlers_can_run.wait()
            await self._on_connect(connection)

        self.connector.ready(_connect)

        async def _on_gameflow_phase(connection, event):
            await self.handlers_can_run.wait()
            await self.on_gameflow_phase(connection, event)
        self.connector.ws.register(LCU_GAMEFLOW_PHASE, event_types=("UPDATE",))(_on_gameflow_phase)

        async def _on_champ_select_session(connection, event):
            await self.handlers_can_run.wait()
            await self.on_champ_select_session(connection, event)
        self.connector.ws.register(LCU_CHAMP_SELECT_SESSION, event_types=("CREATE", "UPDATE",))(_on_champ_select_session)

        async def _on_current_champion(connection, event):
            await self.handlers_can_run.wait()
            champ_name = self.champions_map.get(event.data, "Unknown champ id")
            logging.info("Champion picked: %s", champ_name)
        self.connector.ws.register('/lol-champ-select/v1/current-champion', event_types=("CREATE", "UPDATE",))(_on_current_champion)

        async def _disconnect(connection):
            await self.handlers_can_run.wait()
            await self._on_disconnect(connection)
        self.connector.close(_disconnect)

    async def _on_connect(self, connection):
        self.connector.loop = asyncio.get_running_loop()
        bring_window_to_front(LEAGUE_CLIENT_WINDOW_TITLE)
        logging.info("Connected to League client.")

        # Preload templates
        load_template_cache()

        # Try to fetch input settings from LCU and save parsed keybinds
        try:
            settings_resp = await connection.request('get', '/lol-game-settings/v1/input-settings')
            settings_json = await settings_resp.json()
            parsed = parse_lcu_input_settings(settings_json)
            if parsed:
                save_parsed_keybinds(parsed)
                logging.info("Loaded and saved parsed LCU input settings.")
            else:
                logging.info("LCU input settings parsed but no bindings found.")
        except Exception as e:
            logging.debug(f"Could not fetch/parse LCU input settings: {e}")

        try:
            phase_resp = await connection.request('get', '/lol-gameflow/v1/gameflow-phase')
            current_phase = await phase_resp.json()
            await self.on_gameflow_phase(connection, type('Event', (object,), {"data": current_phase})())
        except Exception as e:
            logging.error(f"Failed to check gameflow phase: {e}")

    async def on_gameflow_phase(self, connection, event):
        phase = event.data
        if phase == self.last_phase:
            return
        self.last_phase = phase

        await asyncio.sleep(1)

        # Create a lobby
        if phase == GAMEFLOW_PHASES["NONE"]:
            selected_game_mode = get_selected_game_mode()
            mode_info = SUPPORTED_MODES.get(selected_game_mode)
            queue_id = mode_info.get("queue_id")
            try:
                await connection.request('post', '/lol-lobby/v2/lobby', data={"queueId": queue_id})
                logging.info(f"{selected_game_mode.capitalize()} lobby created.")
            except Exception as e:
                logging.error(f"Failed to create {selected_game_mode} lobby: {e}")

        # Start queue
        if phase == GAMEFLOW_PHASES["LOBBY"]:
            try:
                await connection.request('post', '/lol-lobby/v2/lobby/matchmaking/search')
                logging.info("Starting queue.")
            except Exception as e:
                logging.error(f"Failed to start queue: {e}")

        # Accept ready check
        if phase == GAMEFLOW_PHASES["READY_CHECK"]:
            try:
                await connection.request('post', '/lol-matchmaking/v1/ready-check/accept')
                logging.info("Accepted ready check.")
            except Exception as e:
                logging.error(f"Failed to accept ready check: {e}")

        # Start bot loop thread on game start
        if phase == GAMEFLOW_PHASES["IN_PROGRESS"]:
            logging.info("Game is in progress.")
            bring_window_to_front(LEAGUE_GAME_WINDOW_TITLE)
            self.bot_manager.start_bot_thread()

        # Clean up bot thread and play again on end of game
        if phase == GAMEFLOW_PHASES["PRE_END_OF_GAME"]:
            logging.info("Game ended.")
            self.handlers_can_run.clear()
            self.bot_manager.wait_for_bot_thread()
            # make sure game window is closed, timeout after certain duration (game may have crashed)
            end_time = time.time() + 60
            while wait_for_window(LEAGUE_GAME_WINDOW_TITLE, timeout=10) != None:
                if time.time() > end_time:
                    logging.error("Game did not close correctly. Shutting down program.")
                    self.shutdown_event.set()
                    self.stop()
                    return
                await asyncio.sleep(1)
            self.handlers_can_run.set()
            # Play again (recreate lobby)
            try:
                await connection.request('post', '/lol-lobby/v2/play-again')
                logging.info("Sent play-again request.")
            except Exception as e:
                logging.error(f"Failed to send play-again request: {e}")

    async def on_champ_select_session(self, connection, event):
        session_data = event.data
        timer = session_data.get('timer', {})
        champ_phase = timer.get('phase')
        actions = session_data.get('actions', [])
        local_cell_id = session_data.get('localPlayerCellId')

        config = load_config()
        preferred_champion_obj = config.get("General", {}).get("preferred_champion", {})
        preferred_champ_id = preferred_champion_obj.get("id") if isinstance(preferred_champion_obj, dict) else None
        
        if champ_phase == CHAMP_SELECT_SUBPHASES["BAN_PICK"]:
            for action_group in actions:
                for action in action_group:
                    # Ban phase
                    if action.get('actorCellId') == local_cell_id and action.get('type') == 'ban' and action.get('isInProgress'):
                        grid_resp = await connection.request('get', '/lol-champ-select/v1/all-grid-champions')
                        grid_data = await grid_resp.json()
                        pickable_champ_ids = [
                            champ['id'] for champ in grid_data
                            if (champ.get('owned') or champ.get('freeToPlay'))
                            and not champ.get('selectionStatus', {}).get('pickedByOtherOrBanned', False)
                        ]
                        action_id = action.get('id')
                        ban_champ_id = random.choice(pickable_champ_ids)
                        response = await connection.request(
                            'patch',
                            f'/lol-champ-select/v1/session/actions/{action_id}',
                            data={"championId": ban_champ_id, "completed": True}
                        )
                        await asyncio.sleep(0.5)
                    # Pick phase
                    if action.get('actorCellId') == local_cell_id and action.get('type') == 'pick' and action.get('isInProgress'):
                        grid_resp = await connection.request('get', '/lol-champ-select/v1/all-grid-champions')
                        grid_data = await grid_resp.json()
                        owned_or_free_champs = [
                            champ['id'] for champ in grid_data
                            if (champ.get('owned') or champ.get('freeToPlay'))
                        ]
                        action_id = action.get('id')

                        # Try preferred champion
                        await connection.request(
                            'patch',
                            f'/lol-champ-select/v1/session/actions/{action_id}',
                            data={"championId": preferred_champ_id, "completed": True}
                        )

                        # Try bravery champion
                        await connection.request(
                            'patch',
                            f'/lol-champ-select/v1/session/actions/{action_id}',
                            data={"championId": -3, "completed": True}
                        )

                        # Try random champion
                        if owned_or_free_champs:
                            champ_id = random.choice(owned_or_free_champs)
                            await connection.request(
                                'patch',
                                f'/lol-champ-select/v1/session/actions/{action_id}',
                                data={"championId": champ_id, "completed": True}
                            )
                        
                        return

    async def _on_disconnect(self, connection):
        logging.info("Connector has been closed.")

    def start(self):
        logging.info("Starting LCU connector...")
        self.connector.start()

    def stop(self, timeout: int = 10):
        fut = asyncio.run_coroutine_threadsafe(self.connector.stop(), self.connector.loop)
        fut.result(timeout=timeout)
        self.bot_manager.wait_for_bot_thread()
