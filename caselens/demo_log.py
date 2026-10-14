"""Demo logging: one readable line per pipeline step, shown on the console and written to logs/demo.log.

Steps logged: route, retrieval, model call, citation check, guardrail, audit. No raw questions,
client IDs, or API keys are logged. Question text is shown only as a length and a short hash.
"""

import hashlib
import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "demo.log"

_logger = logging.getLogger("caselens")


def setup() -> logging.Logger:
    if _logger.handlers:
        return _logger
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-5s | %(message)s", datefmt="%H:%M:%S")
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(fmt)
    _logger.addHandler(console)
    _logger.addHandler(file_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False
    return _logger


def question_tag(text: str) -> str:
    """A short, non-reversible tag for a question. Used instead of the question itself."""
    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:8]
    return f"q#{digest} len={len(text or '')}"


def step(name: str, message: str) -> None:
    setup().info(f"{name:<12} {message}")
