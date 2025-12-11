"""Top-level CSP solve interface.

Expose `solve_puzzle(puzzle)` that takes a parsed puzzle object and returns a solved grid or raises on failure.
Implementation lives in `src/csp/solver_core.py` once wired.
"""

from src.csp import solver_core


def solve_puzzle(puzzle):
    """Solve a parsed puzzle; placeholder delegates to solver_core.solve when implemented."""
    # TODO: implement parsing-to-model and delegate to solver_core
    _ = puzzle
    raise NotImplementedError("solve_puzzle is not yet implemented")


__all__ = ["solve_puzzle"]
