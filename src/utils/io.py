"""I/O helpers for puzzles, traces, and configs (stub)."""

from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    """Load JSON from disk; placeholder."""
    _ = path
    raise NotImplementedError


def save_json(path: Path, payload: Any) -> None:
    """Write JSON to disk; placeholder."""
    _ = (path, payload)
    raise NotImplementedError
