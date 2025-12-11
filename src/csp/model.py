"""CSP core data structures (placeholder)."""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Any


@dataclass
class Variable:
    name: str
    domain: Set[Any] = field(default_factory=set)


@dataclass
class Constraint:
    description: str

    def is_satisfied(self, assignment: Dict[str, Any]) -> bool:
        # TODO: implement actual constraint logic
        _ = assignment
        raise NotImplementedError


@dataclass
class CSP:
    variables: List[Variable]
    constraints: List[Constraint]

    def is_consistent(self, assignment: Dict[str, Any]) -> bool:
        # TODO: check all constraints against the current assignment
        _ = assignment
        raise NotImplementedError
