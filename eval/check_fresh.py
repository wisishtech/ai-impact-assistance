"""Fail if the committed eval results were produced for different code, instructions or test set.

run_eval.py stores a fingerprint of the files below in eval/results/summary.json.
If any of them changed since, re-run the evaluation before releasing.

Run:  python eval/check_fresh.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHED = ["agent/instructions.md", "eval/test_set.jsonl", "data/sources.csv", "mcp_server/src"]


def fingerprint() -> str:
    h = hashlib.sha256()
    for rel in WATCHED:
        p = ROOT / rel
        files = sorted(p.rglob("*.py")) if p.is_dir() else [p]
        for f in files:
            h.update(f.relative_to(ROOT).as_posix().encode())
            h.update(f.read_bytes().replace(b"\r\n", b"\n"))  # same hash on Windows and Linux
    return h.hexdigest()


def main() -> int:
    summary = json.loads((ROOT / "eval" / "results" / "summary.json").read_text(encoding="utf-8"))
    recorded = summary.get("fingerprint")
    current = fingerprint()
    if recorded == current:
        print(f"Eval results are current ({summary.get('run_at')}).")
        return 0
    print("Eval results are stale: instructions, test set, sources or server code changed since the last run.")
    print("Re-run:  uv run python eval/run_eval.py  and commit eval/results/summary.json")
    return 1


if __name__ == "__main__":
    sys.exit(main())
