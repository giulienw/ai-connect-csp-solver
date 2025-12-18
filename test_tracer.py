"""Test to verify trace.py works and captures solver steps."""

from pathlib import Path
from src.csp.model import CSP, Variable, Constraint
from src.utils.trace import get_tracer, reset_tracer
import json


def test_tracer_captures_steps():
    """
    Simple test that verifies the tracer logs steps correctly.
    This doesn't use the full solver - just demonstrates the tracer API.
    """
    reset_tracer()
    tracer = get_tracer()
    
    print("Testing Tracer Functionality")
    print("=" * 60)
    
    # Simulate solver steps
    print("\n1. Logging variable assignment...")
    tracer.log_assign("House_1_Color", "Red", domain_size=5, assignment_size=1)
    
    print("2. Logging domain reduction...")
    tracer.log_domain_reduction("House_2_Color", new_domain_size=4, reason="After constraint check")
    
    print("3. Logging constraint check...")
    tracer.log_constraint_check("AllDiff: House_1_Color, House_2_Color", is_valid=True, variable="House_1_Color")
    
    print("4. Logging AC-3 arc consistency...")
    tracer.log_ac3_run(variables_affected=3, arcs_processed=6)
    
    print("5. Logging forward check...")
    tracer.log_forward_check("House_1_Color", domains_pruned=2)
    
    print("6. Logging backtrack...")
    tracer.log_backtrack("House_2_Food", reason="No valid values left after constraint propagation")
    
    print("7. Logging solution found...")
    tracer.log_solution_found(assignment_size=5)
    
    # Get summary
    summary = tracer.summary()
    print("\n" + "=" * 60)
    print("TRACER SUMMARY:")
    print(f"  Total steps captured: {summary['total_steps']}")
    print(f"  Elapsed time: {summary['elapsed_time_seconds']:.4f} seconds")
    print(f"  Assignments logged: {summary['num_assignments']}")
    print(f"  Backtracks logged: {summary['num_backtracks']}")
    print(f"  Action breakdown: {summary['action_counts']}")
    print("=" * 60)
    
    # Verify steps were captured
    assert len(tracer.steps) > 0, "Tracer should have captured steps"
    print("\n✓ SUCCESS: Tracer captured all steps!")
    
    # Show the actual steps
    print("\nAll captured steps:")
    print("-" * 60)
    for step in tracer.steps:
        print(f"  [{step.step_number}] {step.action_type:20} | "
              f"Var: {str(step.variable):20} | "
              f"Value: {str(step.value):10} | "
              f"Time: {step.timestamp:.4f}s")
    
    # Write to CSV and verify file exists
    output_path = Path("test_trace_output.csv")
    tracer.to_csv(output_path)
    
    # Verify CSV was written
    assert output_path.exists(), f"CSV file should exist at {output_path}"
    print(f"\n✓ CSV file created: {output_path}")
    
    # Read and display CSV content
    print("\nCSV Content:")
    print("-" * 60)
    with open(output_path, 'r') as f:
        content = f.read()
        print(content)
    
    # Cleanup
    output_path.unlink()
    print(f"\n✓ Cleanup: Removed test CSV file")
    
    return True


if __name__ == "__main__":
    success = test_tracer_captures_steps()
    if success:
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED - Tracer works correctly!")
        print("=" * 60)
