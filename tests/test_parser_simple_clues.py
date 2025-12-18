from solver import solve_puzzle


def test_parse_and_solve_simple_clues_puzzle():
    puzzle = {
        "id": "simple-3x3",
        "size": "3*3",
        "puzzle": """Three friends live in three houses in a row, numbered 1 to 3.
Each house is painted a different color and each friend owns a different pet.

Colors: orange, blue, green.
Pets: cat, turtle, dog.

Clues:
1. Alice lives in house 3.
2. House 1 is painted orange.
3. The orange house contains the turtle.
4. Mallory lives in the blue house.
5. The green house contains the dog.
""",
    }

    sol = solve_puzzle(puzzle)
    assert sol, "Expected a solution assignment"
    assert sol["House_1_Color"] == "orange"
    assert sol["House_1_Animal"] == "turtle"
    assert sol["House_2_Color"] == "blue"
    assert sol["House_2_Name"] == "Mallory"
    assert sol["House_2_Animal"] == "cat"
    assert sol["House_3_Name"] == "Alice"
    assert sol["House_3_Color"] == "green"
    assert sol["House_3_Animal"] == "dog"

