"""Diagnostic: list invented terms that the chat answered with a dictionary citation. Offline, no model calls."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chat  # noqa: E402
from config import CASES_CSV, JARGON_JSON  # noqa: E402
from jargon import build_patterns, load_entries  # noqa: E402
from metrics import load_cases  # noqa: E402
from scorecard import INVENTED_TERMS, offline  # noqa: E402

CITE = re.compile(r"\[JD-\d{3}\]")


def main() -> None:
    df = load_cases(CASES_CSV)
    entries = load_entries(JARGON_JSON)
    patterns = build_patterns(entries)
    with offline():
        for term in INVENTED_TERMS:
            reply = chat.answer(f"What is {term}?", df, patterns, entries, history=[])["text"]
            if CITE.search(reply):
                print("FABRICATED:", term, "->", reply[:250].replace("\n", " | "))
    print("Dictionary entries JD-036, JD-052:",
          [(e["ID"], e["Term"]) for e in entries if e["ID"] in ("JD-036", "JD-052")])


if __name__ == "__main__":
    main()
