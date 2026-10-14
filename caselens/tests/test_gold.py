import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"
sys.path.insert(0, str(EVAL_DIR))

import run_gold  # noqa: E402


def test_gold_questions_all_pass():
    results = run_gold.run()
    failed = [r for r in results if not r["passed"]]
    assert not failed, failed
