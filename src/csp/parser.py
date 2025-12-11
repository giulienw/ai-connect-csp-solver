"""Puzzle parser: convert ZebraLogicBench JSON into CSP structures (stub)."""

from typing import Any, Dict

from .model import CSP


def parse_puzzle(puzzle_json: Dict[str, Any]) -> CSP:
    """Turn raw puzzle JSON into a CSP instance."""
    _ = puzzle_json
    raise NotImplementedError
