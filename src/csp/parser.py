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

    # 2. Extract Attributes
    parts = puzzle_text.split("## Clues:")
    description_part = parts[0]
    clues_part = parts[1] if len(parts) > 1 else ""

    categories = {}
    for line in description_part.split('\n'):
        line = line.strip()
        if line.startswith('-') and ':' in line:
            desc_text, values_text = line.split(':', 1)
            
            # Infer Category Name
            key = "Unknown"
            lower = desc_text.lower()
            if "name" in lower: key = "Name"
            elif "color" in lower: key = "Color"
            elif "nationality" in lower: key = "Nationality"
            elif "book" in lower: key = "Book"
            elif "food" in lower or "lunch" in lower: key = "Food"
            elif "drink" in lower: key = "Drink"
            elif "animal" in lower or "pet" in lower: key = "Animal"
            elif "occupation" in lower: key = "Occupation"
            elif "phone" in lower: key = "Phone"
            elif "music" in lower: key = "Music"
            elif "height" in lower: key = "Height"
            elif "child" in lower: key = "Child"
            else:
                key = f"Attr_{len(categories)}"

            # Clean Values
            raw_vals = values_text.split(',')
            clean_vals = [v.strip().replace('`', '').replace('.', '') for v in raw_vals if v.strip()]
            categories[key] = clean_vals

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