import os
import sys

# Bootstrap sys.path so absolute imports like 'src.csp.loader' work when running by file path
# This adds the repository root (two levels up from this file) to PYTHONPATH at runtime.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.csp.loader import load_puzzles
from src.csp.parser import parse_puzzle


def main():
    # Point this to your dataset path; supports .parquet (requires pandas+pyarrow) or .jsonl
    # Examples:
    # file_path = "data/zebra-logic-bench.parquet"
    # file_path = "data/zebra-logic-bench.jsonl"
    file_path = os.environ.get("ZEBRA_DATA_PATH", "data/test-00000-of-00001.parquet")

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found. Set ZEBRA_DATA_PATH or update file_path.")
        return

    try:
        puzzles = load_puzzles(file_path)
    except Exception as e:
        print(f"Loader error: {e}")
        return

    if not puzzles:
        print("No puzzles loaded. Check the file path and format.")
        return

    # Parse the first puzzle as a smoke test
    csp = parse_puzzle(puzzles[0])

    print(f"Parsed CSP OK")
    print(f"- Variables:   {len(csp.variables)}")
    print(f"- Constraints: {len(csp.constraints)}")
    if csp.variables:
        print(f"- Example var: {csp.variables[0].name}")
    if csp.constraints:
        print(f"- Example constraint: {csp.constraints[0].description}")


if __name__ == "__main__":
    main()