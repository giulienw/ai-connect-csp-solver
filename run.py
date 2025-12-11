"""CLI entrypoint: load puzzle(s), run solver, and report metrics."""

import argparse
from pathlib import Path

from solver import solve_puzzle


def parse_args():
    parser = argparse.ArgumentParser(description="Run CSP solver on ZebraLogicBench puzzles")
    parser.add_argument("input", type=Path, help="Path to puzzle JSON or directory of puzzles")
    parser.add_argument("--output", type=Path, default=None, help="Optional path to write solutions")
    return parser.parse_args()


def main():
    args = parse_args()
    _ = (args, solve_puzzle)  # placeholder until wiring is implemented
    raise NotImplementedError("CLI wiring not yet implemented")


if __name__ == "__main__":
    main()
