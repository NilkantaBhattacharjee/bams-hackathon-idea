"""Guardrails for every model call: masking check, output leak check, injection scan, and audit log.

Nothing here calls the model. It checks text before and after the call and records what was sent.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from summary import MASKS

LOG_PATH = Path(__file__).resolve().parent / "logs" / "audit.jsonl"
PROMPT_VERSION = "chat-v2"

# Raw identifiers that must never reach the model. Masked forms (CL-, [CLIENT]) are allowed.
RAW_ID = re.compile(r"\bCL-\d+\b")
RAW_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
RAW_ACCOUNT = re.compile(r"\b\d{9,}\b")

# Phrases that try to override instructions. Matched case-insensitively.
INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|above|prior) (instructions|rules|prompts?)",
    r"disregard (all |any |the )?(previous|above|prior)",
    r"you are now\b",
    r"act as (an? )?(unrestricted|developer|admin)",
    r"reveal (the |your )?(system )?(prompt|instructions|api key|key)",
    r"(print|show|output) (the |your )?(system )?prompt",
    r"approve (this|the) case",
    r"change (the )?(status|decision) to",
]
INJECTION = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def leaks(text: str) -> list[str]:
    """Raw identifiers still present in text that is about to be sent. Empty list means clean."""
    found = []
    for name, pat in [("client_id", RAW_ID), ("email", RAW_EMAIL), ("account_number", RAW_ACCOUNT)]:
        if pat.search(text or ""):
            found.append(name)
    return found


def injection_hits(text: str) -> list[str]:
    return [m.group(0) for m in INJECTION.finditer(text or "")]


def masked_ok(text: str) -> bool:
    """True when masking has removed every raw identifier and no override phrase is present."""
    return not leaks(text) and not injection_hits(text)


def prompt_hash(messages: list[dict]) -> str:
    blob = json.dumps(messages, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def audit(kind: str, *, case_ids=None, masked_prompt_hash="", model="", citations=None,
          dropped=0, error="", path: Path | None = None) -> None:
    """Append one line to the audit log. Stores hashes and IDs only, never the raw question or key."""
    path = Path(path or LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "case_ids": list(case_ids or []),
        "masked_prompt_sha256": masked_prompt_hash,
        "citations": sorted(set(citations or [])),
        "dropped_lines": dropped,
        "error": error,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
