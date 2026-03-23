"""
validate_data.py
Validates all optimizer years have required files and correct data structure.
Run: python3 scripts/validate_data.py
"""
import json
import csv
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

OPTIMIZER_YEARS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
OPTIONAL_YEARS  = [2011, 2012, 2013, 2014]
REQUIRED_FILES  = ["team_stats.csv", "chalk_bracket.json", "actual_results.json"]
ADVANCED_COLS   = ["AdjOffSQ", "AdjDefSQ", "Rim3Rate", "KillShotsScored", "KillShotsConceded"]

ROUND_COUNTS = {
    "round_of_32":   32,
    "sweet_sixteen": 16,
    "elite_eight":   8,
    "final_four":    4,
}

def validate_year(year: int) -> list[str]:
    """Returns a list of error strings. Empty = pass."""
    errors = []
    base = Path(f"years/{year}/data")

    # 1. File presence
    for fname in REQUIRED_FILES:
        if not (base / fname).exists():
            errors.append(f"MISSING: {fname}")

    # 2. actual_results.json structure
    results_path = base / "actual_results.json"
    if results_path.exists():
        try:
            with open(results_path) as f:
                r = json.load(f)
            for key, expected in ROUND_COUNTS.items():
                actual = len(r.get(key, []))
                if actual != expected:
                    errors.append(f"ROUND COUNT: {key} has {actual} (expected {expected})")
            if not r.get("champion"):
                errors.append("MISSING: champion field in actual_results.json")
        except json.JSONDecodeError as e:
            errors.append(f"JSON ERROR in actual_results.json: {e}")

    # 3. team_stats.csv structure and advanced metrics
    csv_path = base / "team_stats.csv"
    if csv_path.exists():
        try:
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                cols = reader.fieldnames or []
                rows = list(reader)
            if not rows:
                errors.append("EMPTY: team_stats.csv has no rows")
            missing_adv = [c for c in ADVANCED_COLS if c not in cols]
            if missing_adv:
                errors.append(f"MISSING ADVANCED COLS: {', '.join(missing_adv)}")
        except Exception as e:
            errors.append(f"CSV ERROR: {e}")

    return errors


def main():
    print("=" * 60)
    print("MM-Bracket-Flow Data Validator")
    print("=" * 60)

    all_years = OPTIMIZER_YEARS + OPTIONAL_YEARS
    passed = 0
    warnings = 0
    failed = 0

    for year in sorted(all_years):
        is_optional = year in OPTIONAL_YEARS
        errors = validate_year(year)
        label = "[OPT]" if is_optional else "     "

        if not errors:
            print(f"  PASS {label} {year}")
            passed += 1
        elif is_optional:
            print(f"  WARN {label} {year} — {len(errors)} issue(s):")
            for e in errors:
                print(f"           {e}")
            warnings += 1
        else:
            print(f"  FAIL {label} {year} — {len(errors)} issue(s):")
            for e in errors:
                print(f"           {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed | {warnings} optional-warnings | {failed} failed")
    print("=" * 60)

    if failed > 0:
        print("\nFix all FAIL years before running optimization.")
        sys.exit(1)
    else:
        print("\nAll core optimizer years OK.")


if __name__ == "__main__":
    main()
