import logging
import os
import threading
from datetime import datetime


def abbreviate_logger(name: str):
    # Convert the full module path to the dotted abbreviated format
    parts = name.split('.')
    if len(parts) == 1:
        return name.ljust(10)

    abbrev = '.'.join([p[0] for p in parts[:-1]]) + '.' + parts[-1]
    return abbrev.ljust(10)


class LogFormatter(logging.Formatter):
    """A simple Python logging formatter with colours to match the output from Spring Boot applications using Sl4J logging."""
    RESET = "\x1b[0m"
    LOGGER_NAME = "	\033[36m"

    COLOURS = {
        logging.DEBUG: "\x1b[36m",  # Light Blue
        logging.INFO: "\x1b[32m",  # Green
        logging.WARNING: "\x1b[33m",  # Yellow
        logging.ERROR: "\x1b[31m",  # Red
        logging.CRITICAL: "\x1b[1;31m"  # Bold Red
    }

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def format(self, record: logging.LogRecord):
        level = record.levelname
        colour = self.COLOURS.get(record.levelno, self.RESET)

        timestamp = self.formatTime(record)
        pid = os.getpid()
        logger_name = abbreviate_logger(record.name)
        thread_name = threading.current_thread().name
        message = record.getMessage()

        # Fixed-width fields to look pretty
        level_field = f"{level:<5}"
        thread_field = f"[{record.processName.lower()}]".ljust(15)
        thread_name_field = f"{thread_name:<12}"

        formatted = (
            f"{timestamp}  {colour}{level_field}{self.RESET} {pid} --- "
            f"{thread_field} {thread_name_field} {self.LOGGER_NAME}{logger_name}{self.RESET} : {message}{self.RESET}"
        )

        return formatted
