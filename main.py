# python -m core.main
import logging
import threading
from utils.cv_utils import load_template_cache
from utils.general_utils import enable_logging, listen_for_exit
from core.menu import show_menu  
from core.lcu_manager import LCUManager

# State variables
shutdown_event = threading.Event()

# Module instances
lcu_manager = LCUManager(shutdown_event)


# ===========================
# Script Functions
# ===========================

 
def run_script():
    logging.info("Starting Script. Waiting for client...")
    lcu_manager.start()

def shutdown():
    logging.info("Shutting down program...")
    shutdown_event.set()

    # Stop connector
    try:
        lcu_manager.stop()
    except Exception:
        logging.exception("Error while stopping LCU manager")

    logging.info("Shut down complete.")
    print("\a", end="", flush=True)

# ===========================
# Main Entry Point
# ===========================

if __name__ == "__main__":
    """
    Main entry point for the League Bot Launcher.
    Handles menu navigation and starts the connector.
    """
    enable_logging()
    load_template_cache()
    
    listen_for_exit(shutdown)
    show_menu(run_script)


