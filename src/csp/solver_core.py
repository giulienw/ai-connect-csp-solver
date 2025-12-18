"""Backtracking CSP solver with MRV, forward checking, and AC-3 arc consistency."""

from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from .model import CSP, Constraint
from src.utils.trace import Tracer, get_tracer

Assignment = Dict[str, Any]
Domains = Dict[str, Set[Any]]


def solve(csp: CSP) -> Assignment:
    """
    Solve a CSP instance using backtracking with MRV, forward checking, and AC-3.
    Returns an assignment mapping variable -> value. Empty dict if unsatisfiable.
    """
    tracer = get_tracer()
    domains = csp.copy_domains()
    if not _enforce_unary_constraints(csp, domains, {}):
        return {}
    if not _ac3(csp, domains, {}, tracer):
        return {}

    result = _backtrack(csp, {}, domains, tracer)
    return result or {}


def _backtrack(
    csp: CSP, assignment: Assignment, domains: Domains, tracer: Optional[Tracer] = None
) -> Optional[Assignment]:
    tracer = tracer or get_tracer()
    if len(assignment) == len(csp.variable_names):
        if csp.is_consistent(assignment):
            tracer.log_solution_found(assignment_size=len(assignment))
            return dict(assignment)
        return None

    var = _select_unassigned_variable(csp, assignment, domains)
    if var is None:
        return None

    for value in _order_domain_values(var, domains):
        if not _is_value_consistent(csp, var, value, assignment):
            continue

        local_assignment = dict(assignment)
        local_assignment[var] = value
        tracer.log_assign(
            variable=var,
            value=value,
            domain_size=len(domains[var]),
            assignment_size=len(local_assignment),
        )

        local_domains = csp.copy_domains(domains)
        local_domains[var] = {value}

        if not _forward_check(csp, var, local_assignment, local_domains, tracer):
            continue

        if not _ac3(csp, local_domains, local_assignment, tracer):
            continue

        result = _backtrack(csp, local_assignment, local_domains, tracer)
        if result is not None:
            return result

    tracer.log_backtrack(var)
    return None


def _select_unassigned_variable(csp: CSP, assignment: Assignment, domains: Domains) -> Optional[str]:
    unassigned = [v for v in csp.variable_names if v not in assignment]
    if not unassigned:
        return None
    # Minimum Remaining Values (MRV) heuristic.
    return min(unassigned, key=lambda v: (len(domains[v]), v))


def _order_domain_values(variable: str, domains: Domains) -> List[Any]:
    # Deterministic ordering for reproducibility.
    return sorted(domains[variable], key=lambda v: str(v))


def _is_value_consistent(csp: CSP, variable: str, value: Any, assignment: Assignment) -> bool:
    trial_assignment = dict(assignment)
    trial_assignment[variable] = value
    for constraint in csp.constraints_for(variable):
        if not constraint.is_satisfied(trial_assignment):
            return False
    return True


def _forward_check(
    csp: CSP,
    variable: str,
    assignment: Assignment,
    domains: Domains,
    tracer: Optional[Tracer] = None,
) -> bool:
    """Prune neighbor domains after assigning `variable`."""
    tracer = tracer or get_tracer()
    if not _enforce_unary_constraints(csp, domains, assignment):
        return False

    pruned = 0
    for neighbor in csp.neighbors.get(variable, []):
        constraints = csp.constraints_between(variable, neighbor)
        if not constraints:
            continue
        for neighbor_value in list(domains[neighbor]):
            trial = dict(assignment)
            trial[neighbor] = neighbor_value
            trial[variable] = assignment[variable]
            if not all(constraint.is_satisfied(trial) for constraint in constraints):
                domains[neighbor].remove(neighbor_value)
                pruned += 1
        if not domains[neighbor]:
            return False
    if pruned:
        tracer.log_forward_check(variable=variable, domains_pruned=pruned)
    return True


def _ac3(
    csp: CSP, domains: Domains, assignment: Assignment, tracer: Optional[Tracer] = None
) -> bool:
    """Maintain arc consistency across all arcs."""
    tracer = tracer or get_tracer()
    if not _enforce_unary_constraints(csp, domains, assignment):
        return False

    queue: deque[Tuple[str, str]] = deque()
    for var in csp.variable_names:
        for neighbor in csp.neighbors.get(var, []):
            queue.append((var, neighbor))

    arcs_processed = 0
    variables_affected = 0
    while queue:
        xi, xj = queue.popleft()
        arcs_processed += 1
        if _revise(csp, xi, xj, domains, assignment):
            variables_affected += 1
            if not domains[xi]:
                return False
            for xk in csp.neighbors.get(xi, set()):
                if xk != xj:
                    queue.append((xk, xi))
    if arcs_processed:
        tracer.log_ac3_run(variables_affected=variables_affected, arcs_processed=arcs_processed)
    return True


def _revise(csp: CSP, xi: str, xj: str, domains: Domains, assignment: Assignment) -> bool:
    """Remove values from Xi that are unsupported by any value in Xj."""
    revised = False
    related_constraints = csp.constraints_between(xi, xj)
    if not related_constraints:
        return revised

    for value in list(domains[xi]):
        if not _has_support(csp, xi, value, xj, domains, assignment, related_constraints):
            domains[xi].remove(value)
            revised = True
    return revised


def _has_support(
    csp: CSP,
    xi: str,
    value: Any,
    xj: str,
    domains: Domains,
    assignment: Assignment,
    constraints: List[Constraint],
) -> bool:
    """Check if `value` for `xi` is consistent with some value of `xj`."""
    for neighbor_value in domains[xj]:
        trial_assignment = dict(assignment)
        trial_assignment[xi] = value
        trial_assignment[xj] = neighbor_value
        if all(constraint.is_satisfied(trial_assignment) for constraint in constraints):
            return True
    return False


def _enforce_unary_constraints(csp: CSP, domains: Domains, assignment: Assignment) -> bool:
    """Prune domains using unary constraints under the current assignment."""
    for var in csp.variable_names:
        unary_constraints = [
            c for c in csp.constraints_for(var) if c.scope and len(c.scope) == 1
        ]
        if not unary_constraints:
            continue

        for value in list(domains[var]):
            trial = dict(assignment)
            trial[var] = value
            if not all(constraint.is_satisfied(trial) for constraint in unary_constraints):
                domains[var].remove(value)
        if not domains[var]:
            return False
    return True
