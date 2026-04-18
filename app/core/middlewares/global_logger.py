import logging
from enum import Enum
from typing import Optional


class Logger:
    """Centralized logging utility that integrates with SystemLog model"""

    def __init__(self, module_name):
        self.module_name = module_name
        self.logger = logging.getLogger(module_name)

    # ---------- Base Methods ----------

    def debug(self, message: str, details: Optional[str] = None):
        self.logger.debug(self._format(message, details))

    def info(self, message: str, details: Optional[str] = None):
        self.logger.info(self._format(message, details))

    def warning(self, message: str, details: Optional[str] = None):
        self.logger.warning(self._format(message, details))

    def error(self, message: str, details: Optional[str] = None):
        self.logger.error(self._format(message, details))

    def critical(self, message: str, details: Optional[str] = None):
        self.logger.critical(self._format(message, details))

    # ---------- Helper ----------

    def _format(self, message: str, details: Optional[str]):
        base = f"[{self.module_name}] {message}"
        if details:
            return f"{message} | details: {details}"
        return base


def get_logger(module_name: str) -> "Logger":
    """Get an AppLogger instance for a module"""
    return Logger(module_name)
