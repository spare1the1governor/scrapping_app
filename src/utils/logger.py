'''настройка логгирования'''
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger  # чтобы не дублировать handlers

    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s | %(message)s"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger

# def_log_for_user():
    

