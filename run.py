"""CLI entrypoint: load puzzle(s), run solver, and report metrics."""

import argparse
import json
import csv
from pathlib import Path

from solver import solve_puzzle
from src.utils.trace import get_tracer, reset_tracer
from src.csp.loader import load_puzzles


def parse_args():
    parser = argparse.ArgumentParser(description="Run CSP solver on ZebraLogicBench puzzles")
    parser.add_argument("input", type=Path, help="Path to puzzle JSON or directory of puzzles")
    parser.add_argument("--output", type=Path, default=None, help="Optional path to write solutions")
    return parser.parse_args()

def reformat_to_grid(assignment: dict) -> dict:
    houses = set()
    attributes = set()

    for var_name in assignment:
        if not var_name.startswith("House_"):
            continue
        _, house, attr = var_name.split("_", 2)
        houses.add(int(house))
        attributes.add(attr)

    houses = sorted(houses)
    attributes = sorted(attributes)

    header = ["House"] + attributes
    rows = []

    for h in houses:
        row = [str(h)]
        for attr in attributes:
            key = f"House_{h}_{attr}"
            row.append(assignment.get(key, "___"))
        rows.append(row)

    return {
        "header": header,
        "rows": rows
    }

def _coerce_jsonable(value):
    if isinstance(value, dict):
        return {k: _coerce_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_coerce_jsonable(v) for v in value]
    if hasattr(value, "tolist"):
        try:
            return value.tolist()
        except Exception:
            pass
    return value

def format_solution(solution: dict, puzzle: dict | None = None) -> dict:
    if not solution:
        template = None
        if isinstance(puzzle, dict):
            template = puzzle.get("solution")
        if template:
            template = _coerce_jsonable(template)
            header = template.get("header", [])
            rows = template.get("rows", [])
            return {"status": "unsolved", "header": header, "rows": rows}
        return {"status": "unsolved", "header": [], "rows": []}

    grid = reformat_to_grid(solution)
    return {"status": "solved", **grid}

def write_results_csv(results, output_path: Path):
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "grid_solution", "steps"])

        for r in results:
            writer.writerow([
                r["id"],
                json.dumps(r["grid_solution"]),
                r["steps"]
            ])

def main():
    args = parse_args()
    puzzles = []
    results = []

    if args.input.is_file():
        puzzles = load_puzzles(str(args.input))
    elif args.input.is_dir():
        for file_path in sorted(args.input.iterdir()):
            if file_path.suffix in [".json", ".jsonl", ".parquet"]:
                puzzles.extend(load_puzzles(str(file_path)))
    else:
        raise ValueError(f"Input path {args.input} is neither file nor directory")


    for puzzle in puzzles:
        reset_tracer()
        tracer = get_tracer()

        try:
            solution = solve_puzzle(puzzle)
            puzzle_id = puzzle.get("id", "unknown")
            grid = format_solution(solution, puzzle)

            summary = tracer.summary()

            results.append({
                "id": puzzle_id,
                "grid_solution": grid,
                "steps": summary['total_steps']
            })
        except Exception as e:
            print(f"ERROR: Failed to solve puzzle {puzzle}: {e}")
            results.append({
                "id": puzzle_id,
                "grid_solution": {"status": "failed", "header": [], "rows": []},
                "steps": -1
            })

    if args.output:
        write_results_csv(results, args.output)
    else:
        print(results)

if __name__ == "__main__":
    main()
