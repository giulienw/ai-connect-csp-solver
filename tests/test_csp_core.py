"""Unit tests for CSP core solver utilities."""

from src.csp.model import CSP, Constraint, Variable
from src.csp import solver_core


def _make_all_diff_csp():
    variables = [
        Variable("A", {1, 2}),
        Variable("B", {1, 2}),
    ]
    constraints = [Constraint.all_diff(["A", "B"])]
    return CSP(variables=variables, constraints=constraints)


def _make_equal_constraint():
    return Constraint(
        description="A == B",
        scope=["A", "B"],
        predicate=lambda a: a.get("A") == a.get("B") if "A" in a and "B" in a else True,
    )


def test_mrv_picks_smallest_domain_then_name():
    csp = CSP(
        variables=[
            Variable("X", {1}),  # smallest domain, alphabetically first among size-1
            Variable("Z", {1}),
            Variable("Y", {1, 2}),
        ],
        constraints=[],
    )
    domains = csp.copy_domains()
    choice = solver_core._select_unassigned_variable(csp, {}, domains)
    assert choice == "X"


def test_forward_check_prunes_neighbor_values():
    csp = _make_all_diff_csp()
    domains = csp.copy_domains()
    domains["A"] = {1}
    assignment = {"A": 1}

    ok = solver_core._forward_check(csp, "A", assignment, domains)
    assert ok
    assert domains["B"] == {2}


def test_ac3_removes_unsupported_values():
    csp = CSP(
        variables=[Variable("A", {1, 2}), Variable("B", {1})],
        constraints=[_make_equal_constraint()],
    )
    domains = csp.copy_domains()
    ok = solver_core._ac3(csp, domains, {})
    assert ok
    assert domains["A"] == {1}
    assert domains["B"] == {1}


def test_ac3_detects_inconsistency():
    csp = CSP(
        variables=[Variable("A", {1}), Variable("B", {2})],
        constraints=[_make_equal_constraint()],
    )
    domains = csp.copy_domains()
    ok = solver_core._ac3(csp, domains, {})
    assert not ok
