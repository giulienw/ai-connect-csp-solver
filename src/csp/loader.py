import json
import os
import re
from typing import Any, Dict, List, Optional

import pandas as pd

def load_puzzles(file_path: str) -> List[Dict[str, Any]]:
    """
    Reads puzzles from a file. Handles .parquet and .jsonl formats.
    Returns a list of raw puzzle dictionaries.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    def _is_nonempty_str(value: Any) -> bool:
        return isinstance(value, str) and value.strip() != ""

    def _infer_size(value: Any) -> Optional[str]:
        if _is_nonempty_str(value):
            match = re.search(r"-(\d+)x(\d+)-", value)
            if match:
                return f"{match.group(1)}*{match.group(2)}"
        return None

    def _infer_houses_from_puzzle_text(puzzle_text: str) -> Optional[int]:
        match = re.search(r"There are (\d+) houses", puzzle_text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    def _extract_puzzle_text(record: Dict[str, Any]) -> str:
        if _is_nonempty_str(record.get("puzzle")):
            return record["puzzle"].strip()

        for key in ("puzzle_text", "prompt", "text", "question", "input"):
            if _is_nonempty_str(record.get(key)):
                return record[key].strip()

        best = ""
        best_score = 0
        for value in record.values():
            if not _is_nonempty_str(value):
                continue
            text = value
            score = 0
            if "## Clues" in text:
                score += 2
            if "There are " in text and " houses" in text:
                score += 1
            if score > best_score:
                best = text
                best_score = score

        return best.strip()

    def _normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
        puzzle_text = _extract_puzzle_text(record)
        if puzzle_text:
            record["puzzle"] = puzzle_text

        size_value = record.get("size")
        if not _is_nonempty_str(size_value):
            inferred = _infer_size(record.get("id"))
            if inferred:
                record["size"] = inferred
            elif puzzle_text:
                houses = _infer_houses_from_puzzle_text(puzzle_text)
                if houses is not None:
                    record["size"] = f"{houses}*0"

        return record

    # Case 1: Parquet File (Binary)
    if file_path.endswith('.parquet'):
        try:
            df = pd.read_parquet(file_path)
            records = df.to_dict(orient="records")
            return [_normalize_record(r) for r in records]
        except Exception as e:
            print(f"Error reading parquet: {e}")
            return []

    # Case 2: JSON File (Text; array or object)
    if file_path.endswith(".json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, list):
                return [_normalize_record(p) for p in payload if isinstance(p, dict)]
            if isinstance(payload, dict):
                return [_normalize_record(payload)]
            return []
        except json.JSONDecodeError:
            # Some sources use ".json" but actually store JSONL; fall back to line-delimited parsing.
            data = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        data.append(_normalize_record(obj))
            return data

    # Case 2: JSONL File (Text)
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    data.append(_normalize_record(obj))
    return data
