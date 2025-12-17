"""Tracing module: logs CSP solver steps and writes to CSV."""

import csv
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TraceStep:
    """A single step in the solving process."""
    
    timestamp: float
    step_number: int
    action_type: str  # 'assign', 'backtrack', 'constraint_check', 'domain_reduced', 'ac3', etc.
    variable: Optional[str] = None
    value: Optional[Any] = None
    domain_size: Optional[int] = None
    domains_state: Optional[str] = None  # JSON-serialized state (optional, can be large)
    assignment_size: Optional[int] = None  # Number of variables assigned
    constraint_checked: Optional[str] = None
    is_valid: Optional[bool] = None
    reason: Optional[str] = None  # Why backtracking occurred, etc.


class Tracer:
    """Records solver steps for logging and analysis."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.steps: List[TraceStep] = []
        self.start_time = datetime.now().timestamp()
        self.step_counter = 0
    
    def _get_timestamp(self) -> float:
        """Get elapsed time in seconds since tracer creation."""
        return datetime.now().timestamp() - self.start_time
    
    def log_assign(self, variable: str, value: Any, domain_size: int, assignment_size: int):
        """Log a variable assignment."""
        if not self.enabled:
            return
        self.step_counter += 1
        self.steps.append(TraceStep(
            timestamp=self._get_timestamp(),
            step_number=self.step_counter,
            action_type='assign',
            variable=variable,
            value=str(value),
            domain_size=domain_size,
            assignment_size=assignment_size,
        ))
    
    def log_backtrack(self, variable: str, reason: str = "No valid values"):
        """Log a backtrack event."""
        if not self.enabled:
            return
        self.step_counter += 1
        self.steps.append(TraceStep(
            timestamp=self._get_timestamp(),
            step_number=self.step_counter,
            action_type='backtrack',
            variable=variable,
            reason=reason,
        ))
    
    def log_constraint_check(self, constraint_desc: str, is_valid: bool, variable: Optional[str] = None):
        """Log a constraint check."""
        if not self.enabled:
            return
        self.step_counter += 1
        self.steps.append(TraceStep(
            timestamp=self._get_timestamp(),
            step_number=self.step_counter,
            action_type='constraint_check',
            constraint_checked=constraint_desc,
            is_valid=is_valid,
            variable=variable,
        ))
    
    def log_domain_reduction(self, variable: str, new_domain_size: int, reason: str = ""):
        """Log domain reduction for a variable."""
        if not self.enabled:
            return
        self.step_counter += 1
        self.steps.append(TraceStep(
            timestamp=self._get_timestamp(),
            step_number=self.step_counter,
            action_type='domain_reduced',
            variable=variable,
            domain_size=new_domain_size,
            reason=reason,
        ))
    
    def log_ac3_run(self, variables_affected: int, arcs_processed: int):
        """Log an AC-3 arc consistency pass."""
        if not self.enabled:
            return
        self.step_counter += 1
        self.steps.append(TraceStep(
            timestamp=self._get_timestamp(),
            step_number=self.step_counter,
            action_type='ac3',
            reason=f"Affected {variables_affected} vars, processed {arcs_processed} arcs",
        ))
    
    def log_forward_check(self, variable: str, domains_pruned: int):
        """Log forward checking."""
        if not self.enabled:
            return
        self.step_counter += 1
        self.steps.append(TraceStep(
            timestamp=self._get_timestamp(),
            step_number=self.step_counter,
            action_type='forward_check',
            variable=variable,
            reason=f"Pruned {domains_pruned} values from other domains",
        ))
    
    def log_solution_found(self, assignment_size: int):
        """Log when a solution is found."""
        if not self.enabled:
            return
        self.step_counter += 1
        self.steps.append(TraceStep(
            timestamp=self._get_timestamp(),
            step_number=self.step_counter,
            action_type='solution_found',
            assignment_size=assignment_size,
        ))
    
    def to_csv(self, filepath: Path, include_large_states: bool = False) -> None:
        """Write trace to CSV file."""
        if not self.steps:
            print("No trace steps to write")
            return
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Select fields to write
        fieldnames = [
            'timestamp', 'step_number', 'action_type', 'variable', 'value',
            'domain_size', 'assignment_size', 'constraint_checked', 'is_valid', 'reason'
        ]
        if include_large_states:
            fieldnames.append('domains_state')
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for step in self.steps:
                row = asdict(step)
                if not include_large_states:
                    row.pop('domains_state', None)
                writer.writerow(row)
        
        print(f"Trace written to {filepath} ({len(self.steps)} steps)")
    
    def summary(self) -> Dict[str, Any]:
        """Get a summary of the trace."""
        action_counts = {}
        for step in self.steps:
            action_counts[step.action_type] = action_counts.get(step.action_type, 0) + 1
        
        return {
            'total_steps': len(self.steps),
            'elapsed_time_seconds': self._get_timestamp(),
            'action_counts': action_counts,
            'num_assignments': sum(1 for s in self.steps if s.action_type == 'assign'),
            'num_backtracks': sum(1 for s in self.steps if s.action_type == 'backtrack'),
        }


# Global tracer instance
_global_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Get or create the global tracer."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = Tracer(enabled=True)
    return _global_tracer


def reset_tracer() -> None:
    """Reset the global tracer."""
    global _global_tracer
    _global_tracer = None


def enable_tracing(enabled: bool = True) -> None:
    """Enable or disable tracing."""
    get_tracer().enabled = enabled
