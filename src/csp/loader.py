import json
import os
import pandas as pd
from typing import List, Dict, Any

def load_puzzles(file_path: str) -> List[Dict[str, Any]]:
    """
    Reads puzzles from a file. Handles .parquet and .jsonl formats.
    Returns a list of raw puzzle dictionaries.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Case 1: Parquet File (Binary)
    if file_path.endswith('.parquet'):
        try:
            df = pd.read_parquet(file_path)
            # Convert DataFrame to a list of dicts
            return df.to_dict(orient='records')
        except Exception as e:
            print(f"Error reading parquet: {e}")
            return []

    # Case 2: JSONL File (Text)
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data