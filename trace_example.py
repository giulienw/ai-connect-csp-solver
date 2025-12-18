"""Example: How to use the Tracer with your CSP solver.

This shows how to integrate tracing into solver_core.py to log all steps.
"""

from pathlib import Path
from src.csp.model import CSP
from src.utils.trace import get_tracer, reset_tracer
from solver import solve_puzzle


def solve_and_trace(puzzle_json: dict, output_trace_csv: Path = None) -> dict:
    """
    Solve a puzzle and log all steps to a trace file.
    
    Args:
        puzzle_json: Raw puzzle dictionary
        output_trace_csv: Path to write trace CSV (optional)
    
    Returns:
        Solution dictionary
    """
    # Reset tracer for this puzzle
    reset_tracer()
    tracer = get_tracer()
    
    # Solve the puzzle
    solution = solve_puzzle(puzzle_json)
    
    # Print summary
    summary = tracer.summary()
    print(f"\n{'='*50}")
    print(f"Solver Summary:")
    print(f"  Total steps: {summary['total_steps']}")
    print(f"  Assignments: {summary['num_assignments']}")
    print(f"  Backtracks: {summary['num_backtracks']}")
    print(f"  Time: {summary['elapsed_time_seconds']:.3f}s")
    print(f"  Actions: {summary['action_counts']}")
    print(f"{'='*50}\n")
    
    # Write trace to file if requested
    if output_trace_csv:
        tracer.to_csv(output_trace_csv)
    
    return solution


if __name__ == "__main__":
    # Example usage
    example_puzzle = {
        "puzzle": "Example puzzle text...",
        "size": "5*5",
    }
    
    trace_output = Path("traces/train/example_trace.csv")
    solution = solve_and_trace(example_puzzle, trace_output)
    print(f"Solution: {solution}")
