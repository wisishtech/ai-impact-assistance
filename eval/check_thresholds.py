"""Release gate: fail (exit code 1) if the latest eval misses any threshold.

Run:  uv run python eval/check_thresholds.py
"""
import json
import sys
from pathlib import Path

SUMMARY = Path(__file__).resolve().parent / "results" / "summary.json"

# metric: (rule, limit)
THRESHOLDS = {
    "leaked_questions": ("max", 0),            # no restricted document may ever reach all staff
    "hit_at_5": ("min", 0.85),
    "restricted_hit_rate": ("min", 0.85),
    "groundedness_avg": ("min", 4.0),
    "correctness": ("min", 0.75),
    "refusal_rate_unanswerable": ("min", 0.9),
}


def main() -> int:
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    failed = 0
    for metric, (rule, limit) in THRESHOLDS.items():
        value = s[metric]
        ok = value <= limit if rule == "max" else value >= limit
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {metric:28} {value}  ({rule} {limit})")
    print("\nRelease gate:", "PASSED" if not failed else f"FAILED ({failed} metric(s))")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())