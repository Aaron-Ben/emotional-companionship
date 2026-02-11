"""
File logging utility for chat and tool call logs.

Logs are stored in data/logs/:
- today.txt: Current day's logs
- YYYY-MM-DD.txt: Archived logs from previous days
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Base logs directory
LOGS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "logs"


class DailyFileHandler(logging.Handler):
    """
    Custom logging handler that writes to daily rotating log files.

    - Current day: today.txt
    - Previous days: YYYY-MM-DD.txt
    """

    def __init__(self, logs_dir: Optional[Path] = None):
        super().__init__()
        self.logs_dir = logs_dir or LOGS_DIR
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.current_date = None
        self.file_handle = None
        self._rotate_if_needed()

    def emit(self, record):
        """Write log record to the appropriate file."""
        try:
            # Check if we need to rotate to a new day
            self._rotate_if_needed()

            if self.file_handle:
                msg = self.format(record)
                self.file_handle.write(msg + '\n')
                self.file_handle.flush()  # Flush immediately for real-time viewing
        except Exception:
            self.handleError(record)

    def _rotate_if_needed(self):
        """Check if we need to rotate to a new log file."""
        today = datetime.now().date()

        # If date changed, rotate files
        if self.current_date != today:
            self._close_file()
            self._archive_today_if_new_day()
            self._open_today_file()
            self.current_date = today

    def _open_today_file(self):
        """Open today.txt for writing."""
        today_path = self.logs_dir / "today.txt"
        self.file_handle = open(today_path, 'a', encoding='utf-8')

    def _close_file(self):
        """Close the current file handle."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None

    def _archive_today_if_new_day(self):
        """
        Archive today.txt to YYYY-MM-DD.txt if it's from a previous day.
        This runs when the date changes.
        """
        today_path = self.logs_dir / "today.txt"

        if not today_path.exists():
            return

        # Get the modification time of the file
        file_mtime = datetime.fromtimestamp(today_path.stat().st_mtime)
        file_date = file_mtime.date()

        # Only archive if the file is from a previous day
        today = datetime.now().date()
        if file_date < today:
            # Archive to dated file
            archive_name = file_date.strftime("%Y-%m-%d") + ".txt"
            archive_path = self.logs_dir / archive_name

            # Handle duplicate archives (append number if exists)
            counter = 1
            while archive_path.exists():
                archive_name = file_date.strftime("%Y-%m-%d") + f"_{counter}" + ".txt"
                archive_path = self.logs_dir / archive_name
                counter += 1

            # Move/rename the file
            today_path.rename(archive_path)
            print(f"[FileLogger] Archived log to {archive_name}")

    def close(self):
        """Close the file handler."""
        self._close_file()


def setup_file_logger(
    logger_name: str = "chat_logs",
    level: int = logging.INFO,
    logs_dir: Optional[Path] = None
) -> logging.Logger:
    """
    Set up a file logger with daily rotation.

    Args:
        logger_name: Name for the logger
        level: Logging level (default: INFO)
        logs_dir: Custom logs directory (default: data/logs/)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers
    if not logger.handlers:
        # Create file handler
        file_handler = DailyFileHandler(logs_dir)

        # Format: timestamp - logger_name - level - message
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger


def get_log_content(date: Optional[datetime] = None) -> str:
    """
    Get log content for a specific date.

    Args:
        date: Date to read logs for (default: today)

    Returns:
        Log file content as string
    """
    logs_dir = LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)

    target_date = date or datetime.now()
    date_str = target_date.strftime("%Y-%m-%d")
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Check if it's today
    if date_str == today_str:
        log_path = logs_dir / "today.txt"
    else:
        # Find the log file (may have counter suffix)
        log_path = None
        for i in range(10):  # Check up to 10 variants
            if i == 0:
                candidate = logs_dir / f"{date_str}.txt"
            else:
                candidate = logs_dir / f"{date_str}_{i}.txt"

            if candidate.exists():
                log_path = candidate
                break

    if not log_path or not log_path.exists():
        return ""

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def list_log_files() -> list:
    """
    List all available log files.

    Returns:
        List of (filename, date_str) tuples, sorted by date (newest first)
    """
    logs_dir = LOGS_DIR
    if not logs_dir.exists():
        return []

    log_files = []
    today = datetime.now().strftime("%Y-%m-%d")

    for file in logs_dir.glob("*.txt"):
        if file.name == "today.txt":
            log_files.append((file.name, today))
        else:
            # Extract date from filename (YYYY-MM-DD.txt or YYYY-MM-DD_N.txt)
            parts = file.stem.split("_")
            if len(parts) >= 1 and len(parts[0]) == 10:
                log_files.append((file.name, parts[0]))

    # Sort by date descending
    log_files.sort(key=lambda x: x[1], reverse=True)
    return log_files
