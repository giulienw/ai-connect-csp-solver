"""CSP core data structures and helper logic."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

Predicate = Callable[[Dict[str, Any]], bool]


@dataclass
class Variable:
    name: str
    domain: Set[Any] = field(default_factory=set)


@dataclass
class Constraint:
    """
    A constraint is defined by a scope (the variables it touches) and a predicate
    that returns True when the current partial assignment is consistent.
    If no predicate is provided we fall back to lightweight defaults (e.g., AllDiff).
    """

    description: str
    scope: Optional[List[str]] = None
    predicate: Optional[Predicate] = None

    def __post_init__(self) -> None:
        if self.scope is None:
            self.scope = self._infer_scope_from_description()

    @classmethod
    def all_diff(cls, variables: Iterable[str]) -> "Constraint":
        vars_list = list(variables)
        desc = f"AllDiff: {', '.join(vars_list)}"

        def _predicate(assignment: Dict[str, Any]) -> bool:
            values = []
            for var in vars_list:
                if var in assignment:
                    values.append(assignment[var])
            # Partial assignments are allowed; only fail on duplicates.
            return len(values) == len(set(values))

        return cls(description=desc, scope=vars_list, predicate=_predicate)

    @classmethod
    def equals(cls, variable: str, value: Any) -> "Constraint":
        desc = f"{variable} == {value}"

        def _predicate(assignment: Dict[str, Any]) -> bool:
            if variable not in assignment:
                return True
            return assignment[variable] == value

        return cls(description=desc, scope=[variable], predicate=_predicate)

    def involves(self, variable: str) -> bool:
        return bool(self.scope) and variable in self.scope

    def is_satisfied(self, assignment: Dict[str, Any]) -> bool:
        if self.predicate:
            return self.predicate(assignment)

        # Lightweight support for AllDiff constraints encoded in descriptions.
        if self.description.lower().startswith("alldiff"):
            scope = self.scope or []
            seen: Set[Any] = set()
            for var in scope:
                if var in assignment:
                    value = assignment[var]
                    if value in seen:
                        return False
                    seen.add(value)
            return True

        # If we cannot evaluate the constraint yet, treat it as non-binding.
        return True

    def _infer_scope_from_description(self) -> Optional[List[str]]:
        if self.description.lower().startswith("alldiff"):
            _, _, raw_vars = self.description.partition(":")
            if raw_vars:
                parsed = [v.strip() for v in raw_vars.split(",") if v.strip()]
                return parsed or None
        return None


@dataclass
class CSP:
    variables: List[Variable]
    constraints: List[Constraint]

    def __post_init__(self) -> None:
        self.variable_names: List[str] = [v.name for v in self.variables]
        if len(set(self.variable_names)) != len(self.variable_names):
            raise ValueError("Variable names must be unique")

        # Domains are mutable during search; keep a canonical copy on the CSP.
        self.domains: Dict[str, Set[Any]] = {
            var.name: set(var.domain) for var in self.variables
        }

        # Map each variable to the constraints that mention it.
        self.constraints_by_var: Dict[str, List[Constraint]] = {
            name: [] for name in self.variable_names
        }
        for constraint in self.constraints:
            if not constraint.scope:
                continue
            for var in constraint.scope:
                if var in self.constraints_by_var:
                    self.constraints_by_var[var].append(constraint)

        # Neighbor map used for forward-checking/arc-consistency.
        self.neighbors: Dict[str, Set[str]] = {name: set() for name in self.variable_names}
        for constraint in self.constraints:
            if not constraint.scope:
                continue
            for var in constraint.scope:
                if var not in self.neighbors:
                    continue
                others = [v for v in constraint.scope if v != var and v in self.neighbors]
                self.neighbors[var].update(others)

    def constraints_for(self, variable: str) -> List[Constraint]:
        return self.constraints_by_var.get(variable, [])

    def constraints_between(self, var_a: str, var_b: str) -> List[Constraint]:
        return [
            c
            for c in self.constraints
            if c.scope and var_a in c.scope and var_b in c.scope
        ]

    def is_consistent(self, assignment: Dict[str, Any]) -> bool:
        """Check whether every constraint is satisfied under the current partial assignment."""
        for constraint in self.constraints:
            if not constraint.is_satisfied(assignment):
                return False
        return True

    def copy_domains(self, domains: Optional[Dict[str, Set[Any]]] = None) -> Dict[str, Set[Any]]:
        source = domains if domains is not None else self.domains
        return {var: set(values) for var, values in source.items()}
