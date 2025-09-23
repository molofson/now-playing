import logging
from collections import deque


class EnrichmentLogBuffer:
    def __init__(self, logger_name: str, max_lines: int = 50):
        """Initialize the EnrichmentLogBuffer."""
        self.logger = logging.getLogger(logger_name)
        self.max_lines = max_lines
        self.buffer = deque(maxlen=max_lines)
        self._install_handler()

    def _install_handler(self):
        handler = logging.StreamHandler(self)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(handler)
        self.logger.propagate = True

    def write(self, message):
        if message.strip():
            self.buffer.append(message.rstrip())

    def flush(self):
        pass

    def get_lines(self):
        return list(self.buffer)
