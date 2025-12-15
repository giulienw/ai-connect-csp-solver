"""Top-level CSP solve interface.

Expose `solve_puzzle(puzzle)` that accepts either a pre-built CSP object or a raw
puzzle dictionary compatible with `src.csp.parser.parse_puzzle`.
"""

from typing import Any, Dict

from src.csp import solver_core
from src.csp.model import CSP
from src.csp.parser import parse_puzzle


def solve_puzzle(puzzle: Any) -> Dict[str, Any]:
    """
    Solve a puzzle and return a mapping from variable name to assigned value.
    Accepts:
      - CSP instances (used directly)
      - Raw puzzle dictionaries (parsed via `parse_puzzle`)
    """
    if isinstance(puzzle, CSP):
        csp = puzzle
    elif isinstance(puzzle, dict):
        csp = parse_puzzle(puzzle)
    else:
        raise TypeError("solve_puzzle expects a CSP instance or puzzle dictionary")

    return solver_core.solve(csp)


__all__ = ["solve_puzzle"]
