import argparse
import json
import os
import sys

# Skip this module entirely when pandas is not available (e.g., minimal test env)
try:  # pragma: no cover - guard for lightweight environments
    import pandas as _  # type: ignore
except ImportError:  # pragma: no cover
    import pytest

    pytest.skip("pandas not installed; skip CLI parse script tests", allow_module_level=True)

# Bootstrap sys.path so absolute imports work when running by file path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.csp.loader import load_puzzles
from src.csp.parser import parse_puzzle

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

SAMPLE_PUZZLE = {
    "size": "2*2",
    "puzzle": """
There are 2 houses.

- Colors: Red, Blue
- Pets: Dog, Cat

## Clues:
1. The red house has the dog.
""",
    "id": "sample-2x2",
}


def csp_to_dict(csp):
    """Serialize your CSP object to a plain-JSON structure."""
    return {
        "variables": [
            {"name": v.name, "domain": sorted(list(v.domain))}
            for v in csp.variables
        ],
        "constraints": [
            {"description": c.description}
            for c in csp.constraints
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="Batch-parse ZebraLogicBench puzzles into CSPs.")
    ap.add_argument("--input", help="Path to .parquet or .jsonl dataset")
    ap.add_argument("--use-sample", action="store_true", help="Parse built-in 2x2 sample puzzle")
    ap.add_argument("--max", type=int, default=0, help="Max number of puzzles to process (0 = all)")
    ap.add_argument("--filter-size", default="", help="Filter by size like '5*6' or '4*4' (optional)")
    ap.add_argument("--out-summary", default="parsed_puzzles_summary.json",
                    help="Output path for summary JSON")
    ap.add_argument("--out-sample", default="parsed_puzzles_sample.json",
                    help="Output path for sample JSON of fully serialized CSPs")
    ap.add_argument("--sample-n", type=int, default=5,
                    help="Number of CSPs to fully serialize to --out-sample")
    args = ap.parse_args()

    if not args.use_sample and not args.input:
        ap.error("either --input must be provided or --use-sample set")

    if args.use_sample:
        puzzles = [SAMPLE_PUZZLE]
        print("Using built-in 2x2 sample puzzle")
    else:
        if not os.path.exists(args.input):
            print(f"Error: {args.input} not found")
            sys.exit(1)

        print(f"Loading: {args.input}")
        puzzles = load_puzzles(args.input)
        if not puzzles:
            print("No puzzles loaded. Check format and path.")
            sys.exit(1)

    # Optional filter by size (e.g., "5*6")
    if args.filter_size:
        puzzles = [p for p in puzzles if str(p.get("size", "")).strip() == args.filter_size]
        print(f"Filtered by size {args.filter_size}: {len(puzzles)} puzzles remain")

    total = len(puzzles) if args.max <= 0 else min(args.max, len(puzzles))
    print(f"Parsing up to {total} puzzle(s)...")

    summary = []
    sample = []
    errors = 0

    iterator = puzzles[:total]
    if tqdm:
        iterator = tqdm(iterator, desc="Parsing", unit="puzzle")

    for idx, p in enumerate(iterator):
        pid = p.get("id", f"row_{idx}")
        try:
            csp = parse_puzzle(p)
            # Record lightweight summary
            summary.append({
                "id": pid,
                "size": p.get("size"),
                "variables": len(csp.variables),
                "constraints": len(csp.constraints),
            })
            # Save a few fully serialized CSPs for inspection
            if len(sample) < args.sample_n:
                sample.append({
                    "id": pid,
                    "size": p.get("size"),
                    "csp": csp_to_dict(csp),
                })
        except Exception as e:
            errors += 1
            summary.append({
                "id": pid,
                "size": p.get("size"),
                "error": str(e),
            })

    # Write outputs
    with open(args.out_summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open(args.out_sample, "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2)

    ok = sum(1 for s in summary if "error" not in s)
    print(f"Done. Parsed OK: {ok}/{len(summary)}. Errors: {errors}")
    print(f"- Summary: {args.out_summary}")
    print(f"- Sample CSPs: {args.out_sample} (first {args.sample_n})")


if __name__ == "__main__":
    main()
