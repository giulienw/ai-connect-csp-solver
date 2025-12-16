"""CLI entrypoint: load puzzle(s), run solver, and report metrics."""

import argparse
import json
from pathlib import Path

from solver import solve_puzzle


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
        with open(puzzle_path, "r", encoding="utf-8") as f:
            puzzle = json.load(f)

        solution = solve_puzzle(puzzle)
        puzzle_id = puzzle.get("id", puzzle_path.stem)
        grid = reformat_to_grid(solution)

        results.append({
            "id": puzzle_id,
            "grid_solution": grid,
            "steps": -1
        })

    print(results)

if __name__ == "__main__":
    main()