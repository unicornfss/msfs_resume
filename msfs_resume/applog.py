from __future__ import annotations

import logging
import traceback
import urllib.parse
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .constants import APP_NAME, CONTACT_EMAIL
from .settings import APP_DIR, ensure_app_dir

LOG_PATH = APP_DIR / "error.log"
logger = logging.getLogger("msfs_resume")


def setup_logging() -> Path:
    ensure_app_dir()
    handler = RotatingFileHandler(LOG_PATH, maxBytes=512_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.setLevel(logging.INFO)
        root.addHandler(handler)
    logging.captureWarnings(True)
    return LOG_PATH


def log_exception(message: str, exc: BaseException | None = None) -> None:
    if exc is None:
        logger.exception(message)
    else:
        logger.error("%s: %s\n%s", message, exc, traceback.format_exc())


def read_log_tail(path: Path | None = None, max_chars: int = 8000) -> str:
    target = path or LOG_PATH
    if not target.exists():
        return "(No errors have been logged yet.)"
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[-max_chars:]
    return text


def mailto_log(path: Path | None = None) -> str:
    tail = read_log_tail(path, max_chars=1500)
    subject = urllib.parse.quote(f"{APP_NAME} error log")
    body = urllib.parse.quote(
        f"Please describe what you were doing.\n\nLog file: {path or LOG_PATH}\n\n---\n{tail}"
    )
    return f"mailto:{CONTACT_EMAIL}?subject={subject}&body={body}"


def email_error_log() -> None:
    webbrowser.open(mailto_log())
