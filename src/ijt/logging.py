import logging
from pathlib import Path
from datetime import datetime
from rich.logging import RichHandler

def setup_logging(log_dir: Path, level: str = "INFO") -> logging.Logger:
    """Configure dual-output logging: Rich console + file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"ijt_{timestamp}.log"

    # File handler: DEBUG level, captures everything including tracebacks
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"
    ))

    # Console handler: INFO level via Rich (colored, concise)
    console_handler = RichHandler(rich_tracebacks=True, show_path=False)
    console_handler.setLevel(getattr(logging, level))

    root = logging.getLogger("ijt")
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    return root

def get_logger(module: str) -> logging.Logger:
    return logging.getLogger(f"ijt.{module}")
