"""Integration-style tests for the baseline CSP solver."""

from solver import solve_puzzle
from src.csp.model import CSP, Constraint, Variable


def _red_house_has_dog(assignment):
    pairs = [
        ("House_1_Color", "House_1_Pet"),
        ("House_2_Color", "House_2_Pet"),
    ]
    for color_var, pet_var in pairs:
        color = assignment.get(color_var)
        pet = assignment.get(pet_var)
        if color == "Red" and pet is not None and pet != "Dog":
            return False
        if pet == "Dog" and color is not None and color != "Red":
            return False
    return True


def _build_demo_puzzle() -> CSP:
    variables = [
        Variable("House_1_Color", {"Red", "Blue"}),
        Variable("House_2_Color", {"Red", "Blue"}),
        Variable("House_1_Pet", {"Dog", "Cat"}),
        Variable("House_2_Pet", {"Dog", "Cat"}),
    ]

    constraints = [
        Constraint.all_diff(["House_1_Color", "House_2_Color"]),
        Constraint.all_diff(["House_1_Pet", "House_2_Pet"]),
        Constraint.equals("House_1_Color", "Red"),
        Constraint(
            description="Red house has the dog",
            scope=[
                "House_1_Color",
                "House_2_Color",
                "House_1_Pet",
                "House_2_Pet",
            ],
            predicate=_red_house_has_dog,
        ),
    ]
    return CSP(variables=variables, constraints=constraints)


def test_solver_solves_small_logic_grid():
    csp = _build_demo_puzzle()
    solution = solve_puzzle(csp)

    assert solution, "Solver should find an assignment"
    assert set(solution.keys()) == {v.name for v in csp.variables}
    assert solution["House_1_Color"] == "Red"
    assert solution["House_1_Pet"] == "Dog"
    assert solution["House_2_Color"] == "Blue"
    assert solution["House_2_Pet"] == "Cat"
