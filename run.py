"""CLI entrypoint: load puzzle(s), run solver, and report metrics."""

import argparse
import json
import csv
from pathlib import Path

from solver import solve_puzzle
from src.utils.trace import get_tracer, reset_tracer


def parse_args():
    parser = argparse.ArgumentParser(description="Run CSP solver on ZebraLogicBench puzzles")
    parser.add_argument("input", type=Path, help="Path to puzzle JSON or directory of puzzles")
    parser.add_argument("--output", type=Path, default=None, help="Optional path to write solutions")
    return parser.parse_args()

def reformat_to_grid(assignment: dict) -> dict:
    houses = set()
    attributes = set()

    for ass in assignment:
        if not ass.startswith("House_"):
            continue
        _, house, attr = ass.split("_", 2)
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
    puzzle_files = []
    results = []

    if args.input.is_file():
        puzzle_files = [args.input]
    elif args.input.is_dir():
        puzzle_files = sorted(args.input.glob("*.json"))
    else:
        raise ValueError("Input path does not exist")

    for puzzle_path in puzzle_files:
        reset_tracer()
        tracer = get_tracer()

        with open(puzzle_path, "r", encoding="utf-8") as f:
            puzzle = json.load(f)

        solution = solve_puzzle(puzzle)
        puzzle_id = puzzle.get("id", puzzle_path.stem)
        grid = reformat_to_grid(solution)

        summary = tracer.summary()

        results.append({
            "id": puzzle_id,
            "grid_solution": grid,
            "steps": summary['total_steps']
        })

    if args.output:
        write_results_csv(results, args.output)
    else:
        print(results)
if __name__ == "__main__":
    main()