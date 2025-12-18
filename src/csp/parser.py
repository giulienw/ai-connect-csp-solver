"""Puzzle parser: convert ZebraLogicBench JSON into CSP structures."""

import re
from typing import Any, Dict, List
from .model import CSP, Variable, Constraint

def parse_puzzle(puzzle_json: Dict[str, Any]) -> CSP:
    """
    Turn raw puzzle JSON into a CSP instance.
    
    Args:
        puzzle_json (dict): A single puzzle dictionary.
        
    Returns:
        CSP: An instance of the CSP class defined in model.py.
    """
    puzzle_text = puzzle_json.get('puzzle', '')
    
    # 1. Parse Puzzle Size (Houses)
    size_str = puzzle_json.get('size', '0*0')
    try:
        num_houses = int(size_str.split('*')[0])
    except (ValueError, IndexError):
        # Fallback if size string is missing/malformed
        match = re.search(r"There are (\d+) houses", puzzle_text)
        num_houses = int(match.group(1)) if match else 5

    # 2. Extract Attributes / Clues
    # Support both ZebraLogicBench ("## Clues:") and simpler formats ("Clues:")
    if "## Clues:" in puzzle_text:
        parts = puzzle_text.split("## Clues:", 1)
    elif "\nClues:" in puzzle_text:
        parts = puzzle_text.split("\nClues:", 1)
    elif "Clues:" in puzzle_text:
        parts = puzzle_text.split("Clues:", 1)
    else:
        parts = [puzzle_text]

    description_part = parts[0]
    clues_part = parts[1] if len(parts) > 1 else ""

    categories = {}

    def _canonical_category_name(raw: str) -> str:
        lower = raw.lower().strip(" -")
        if "name" in lower or "person" in lower or "people" in lower or "friend" in lower:
            return "Name"
        if "color" in lower:
            return "Color"
        if "nationality" in lower:
            return "Nationality"
        if "book" in lower:
            return "Book"
        if "food" in lower or "lunch" in lower:
            return "Food"
        if "drink" in lower:
            return "Drink"
        if "animal" in lower or "pet" in lower:
            return "Pet"
        if "occupation" in lower or "job" in lower:
            return "Occupation"
        if "phone" in lower:
            return "Phone"
        if "music" in lower:
            return "Music"
        if "height" in lower:
            return "Height"
        if "child" in lower:
            return "Child"
        return f"Attr_{len(categories)}"

    def _parse_values(values_text: str) -> List[str]:
        raw_vals = values_text.split(",")
        clean_vals = []
        for v in raw_vals:
            vv = v.strip().replace("`", "").strip()
            vv = vv.rstrip(".")
            if vv:
                clean_vals.append(vv)
        return clean_vals

    for line in description_part.split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue

        # Accept both:
        # - "- People have unique favorite colors: `red`, `green`, ..."
        # - "Colors: orange, blue, green."
        if line.lower().startswith("clues:"):
            continue

        if line.startswith("-"):
            desc_text, values_text = line.split(":", 1)
            key = _canonical_category_name(desc_text)
            values = _parse_values(values_text)
            if values:
                categories[key] = values
            continue

        # Non-bulleted category line (e.g. "Colors: red, blue, green.")
        desc_text, values_text = line.split(":", 1)
        key = _canonical_category_name(desc_text)
        values = _parse_values(values_text)
        if values:
            categories[key] = values

    # If names are not explicitly listed, try to infer them from the clue text
    # and pad with placeholders to match the number of houses.
    if "Name" not in categories:
        candidates = re.findall(r"\b[A-Z][a-z]+\b", clues_part)
        stop = {
            "There",
            "Each",
            "House",
            "Houses",
            "Clues",
            "Colors",
            "Pets",
            "Friends",
            "People",
            "The",
            "A",
            "An",
        }
        names = []
        for c in candidates:
            if c in stop:
                continue
            if c not in names:
                names.append(c)
        if names:
            if len(names) < num_houses:
                for i in range(len(names) + 1, num_houses + 1):
                    names.append(f"Person_{i}")
            categories["Name"] = names

    # 3. Create Variable Objects (using model.py class)
    variables: List[Variable] = []
    
    for i in range(1, num_houses + 1):
        for cat_name, cat_values in categories.items():
            var_name = f"House_{i}_{cat_name}"
            # model.py expects 'domain' to be a Set[Any]
            variables.append(Variable(name=var_name, domain=set(cat_values)))

    # 4. Create Constraint Objects (using model.py class)
    constraints: List[Constraint] = []

    # Implicit AllDiff Constraints
    for cat_name in categories.keys():
        scope_vars = [f"House_{i}_{cat_name}" for i in range(1, num_houses + 1)]
        # We store the scope in the description so Solver team can parse it
        # or you can subclass Constraint if allowed.
        desc = f"AllDiff: {', '.join(scope_vars)}"
        constraints.append(Constraint(description=desc))

    # Explicit Clue Constraints
    clue_matches = re.findall(r'\d+\.\s+(.*)', clues_part)
    for idx, clue_text in enumerate(clue_matches):
        constraints.append(Constraint(description=clue_text.strip()))

    return CSP(variables=variables, constraints=constraints)
