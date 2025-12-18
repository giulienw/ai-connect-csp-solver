from src.csp.parser import parse_puzzle


def test_parser_uses_zebra_like_header_names():
    puzzle = {
        "id": "zebra-mini",
        "size": "3*0",
        "puzzle": """There are 3 houses, numbered 1 to 3 from left to right.
- The people are of nationalities: `norwegian`, `german`, `dane`
- People have unique favorite book genres: `fantasy`, `mystery`, `romance`
- People use unique phone models: `iphone 13`, `oneplus 9`, `samsung galaxy s21`

## Clues:
1. The German is in the first house.
""",
    }

    csp = parse_puzzle(puzzle)
    names = {v.name for v in csp.variables}
    assert "House_1_Nationality" in names
    assert "House_1_BookGenre" in names
    assert "House_1_PhoneModel" in names

