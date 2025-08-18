import threading
import time
from utils.general_utils import listen_for_exit_key

threading.Thread(target=listen_for_exit_key, daemon=True).start()
while True:
    print("waiting for exit...")
    time.sleep(2)