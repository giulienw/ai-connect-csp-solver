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

        results.append((puzzle_id, solution))

    print(results)


if __name__ == "__main__":
    main()