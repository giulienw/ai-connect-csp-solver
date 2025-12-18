"""CLI entrypoint: load puzzle(s), run solver, and report metrics."""

import argparse
import json
import csv
from pathlib import Path
from typing import Any

from solver import solve_puzzle
from src.utils.trace import get_tracer, reset_tracer
from src.csp.loader import load_puzzles


def parse_args():
    parser = argparse.ArgumentParser(description="Run CSP solver on ZebraLogicBench puzzles")
    parser.add_argument("input", type=Path, help="Path to puzzle JSON or directory of puzzles")
    parser.add_argument("--output", type=Path, default=None, help="Optional path to write solutions")
    parser.add_argument(
        "--sample-submission",
        type=Path,
        default=None,
        help="Optional Kaggle sample submission CSV used to align output header/shape per id.",
    )
    parser.add_argument(
        "--include-status",
        action="store_true",
        help="Include a 'status' field in grid_solution (debug only; may hurt Kaggle scoring).",
    )
    return parser.parse_args()

def reformat_to_grid(
    assignment: dict,
    *,
    header: list[str] | None = None,
    num_houses: int | None = None,
) -> dict:
    houses = set()
    attributes = set()

    for var_name in assignment.keys():
        if var_name.startswith("House_"):
            _, house, attr = var_name.split("_", 2)
            houses.add(int(house))
            attributes.add(attr)

    if header:
        # Header includes "House" as first column.
        attributes = list(header[1:])
    else:
        attributes = sorted(attributes)

    if num_houses is None:
        num_houses = max(houses) if houses else 0

    resolved_header = ["House"] + attributes
    rows: list[list[Any]] = []

    def _lookup(house: int, attr: str) -> Any:
        key = f"House_{house}_{attr}"
        if key in assignment:
            return assignment[key]
        # Common aliases between datasets/templates.
        aliases = {
            "Pet": ["Animal"],
            "Animal": ["Pet"],
            "Book": ["BookGenre"],
            "BookGenre": ["Book"],
            "Phone": ["PhoneModel"],
            "PhoneModel": ["Phone"],
        }.get(attr, [])
        for alt in aliases:
            alt_key = f"House_{house}_{alt}"
            if alt_key in assignment:
                return assignment[alt_key]
        return "___"

    for h in range(1, num_houses + 1):
        row = [str(h)]
        for attr in attributes:
            row.append(_lookup(h, attr))
        rows.append(row)

    return {
        "header": resolved_header,
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

def _load_sample_templates(sample_path: Path) -> dict[str, dict]:
    templates: dict[str, dict] = {}
    if not sample_path:
        return templates

    with open(sample_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("id")
            raw = row.get("grid_solution")
            if not pid or raw is None:
                continue
            raw = raw.strip()
            if not raw or raw.lower() == "null":
                continue
            try:
                template = json.loads(raw)
            except Exception:
                continue
            template = _coerce_jsonable(template)
            if isinstance(template, dict) and "header" in template and "rows" in template:
                templates[pid] = template
    return templates


def format_solution(
    solution: dict,
    puzzle: dict | None = None,
    template: dict | None = None,
    *,
    include_status: bool = False,
) -> dict:
    template = template or (puzzle.get("solution") if isinstance(puzzle, dict) else None)
    template = _coerce_jsonable(template) if template else None

    if not solution and not template:
        empty = {"header": [], "rows": []}
        if include_status:
            return {"status": "unsolved", **empty}
        return empty

    if template and isinstance(template, dict):
        tpl_header = template.get("header") or []
        tpl_rows = template.get("rows") or []
        num_houses = len(tpl_rows) if isinstance(tpl_rows, list) else None
        if isinstance(tpl_header, list) and tpl_header and num_houses:
            grid = reformat_to_grid(solution or {}, header=tpl_header, num_houses=num_houses)
        else:
            grid = {"header": tpl_header, "rows": tpl_rows}
    else:
        # Best-effort output for datasets without templates.
        grid = reformat_to_grid(solution or {})
        attrs = list(grid.get("header", [])[1:])
        preferred = [
            "Name",
            "Nationality",
            "BookGenre",
            "Book",
            "Occupation",
            "PhoneModel",
            "Phone",
            "CarModel",
            "Sport",
            "Food",
            "Drink",
            "Color",
            "Pet",
            "Animal",
            "Music",
            "Height",
            "Child",
        ]
        ordered = [a for a in preferred if a in attrs] + sorted([a for a in attrs if a not in preferred])
        grid = reformat_to_grid(
            solution or {},
            header=["House", *ordered],
            num_houses=len(grid["rows"]),
        )

    if include_status:
        status = "solved" if solution else "unsolved"
        return {"status": status, **grid}
    return grid

def write_results_csv(results, output_path: Path):
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "grid_solution", "steps"])

        for r in results:
            writer.writerow([
                r["id"],
                json.dumps(r["grid_solution"], ensure_ascii=False, separators=(",", ":")),
                r["steps"]
            ])

def main():
    args = parse_args()
    puzzles = []
    results = []
    templates = _load_sample_templates(args.sample_submission) if args.sample_submission else {}

    if args.input.is_file():
        puzzles = load_puzzles(str(args.input))
    elif args.input.is_dir():
        for file_path in sorted(args.input.iterdir()):
            if file_path.suffix in [".json", ".jsonl", ".parquet", ".csv"]:
                puzzles.extend(load_puzzles(str(file_path)))
    else:
        raise ValueError(f"Input path {args.input} is neither file nor directory")


    for puzzle in puzzles:
        reset_tracer()
        tracer = get_tracer()

        try:
            solution = solve_puzzle(puzzle)
            puzzle_id = puzzle.get("id", "unknown")
            grid = format_solution(
                solution,
                puzzle,
                templates.get(puzzle_id),
                include_status=args.include_status,
            )

            summary = tracer.summary()

            results.append({
                "id": puzzle_id,
                "grid_solution": grid,
                # Use assignments as a proxy for search effort; avoids counting bookkeeping logs.
                "steps": summary.get("num_assignments", summary["total_steps"])
            })
        except Exception as e:
            print(f"ERROR: Failed to solve puzzle {puzzle}: {e}")
            results.append({
                "id": puzzle_id,
                "grid_solution": {"header": [], "rows": []},
                "steps": -1
            })

    if args.output:
        write_results_csv(results, args.output)
    else:
        print(results)

if __name__ == "__main__":
    main()
