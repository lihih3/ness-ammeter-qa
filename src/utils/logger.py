import logging
import os
from datetime import datetime

LOG_DIR = "results/logs"

# One log file per program run, shared by every TestLogger instance.
_run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"{_run_timestamp}_test_run.log")


def _setup_logger() -> logging.Logger:
    """
    Configure the parent logger once. Every TestLogger is a child of it,
    so they all write to the same file through a single handler.
    """
    parent = logging.getLogger("ammeter_qa")
    parent.setLevel(logging.DEBUG)

    if not parent.handlers:
        os.makedirs(LOG_DIR, exist_ok=True)
        handler = logging.FileHandler(LOG_FILE)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        parent.addHandler(handler)

    return parent


class TestLogger:
    def __init__(self, test_name: str):
        self._test_name = test_name
        _setup_logger()
        self.logger = logging.getLogger(f"ammeter_qa.{test_name}")

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def warning(self, message: str):
        self.logger.warning(message)