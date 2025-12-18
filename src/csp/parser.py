"""Puzzle parser: convert puzzle text into CSP structures.

Supports:
- ZebraLogicBench format (attribute bullets + "## Clues:")
- Simpler format used by small test sets (e.g. "Colors: ..." + "Clues:")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .model import CSP, Constraint, Variable


@dataclass(frozen=True)
class _ValueRef:
    category: str
    value: str  # canonical casing from domains


def parse_puzzle(puzzle_json: Dict[str, Any]) -> CSP:
    puzzle_text = str(puzzle_json.get("puzzle", "") or "")

    # 1) Parse puzzle size (houses)
    size_str = str(puzzle_json.get("size", "0*0") or "0*0")
    try:
        num_houses = int(size_str.split("*", 1)[0])
    except (ValueError, IndexError):
        match = re.search(r"There are (\d+) houses", puzzle_text)
        num_houses = int(match.group(1)) if match else 5

    # 2) Split description vs clues
    if "## Clues:" in puzzle_text:
        description_part, clues_part = puzzle_text.split("## Clues:", 1)
    elif "\nClues:" in puzzle_text:
        description_part, clues_part = puzzle_text.split("\nClues:", 1)
    elif "Clues:" in puzzle_text:
        description_part, clues_part = puzzle_text.split("Clues:", 1)
    else:
        description_part, clues_part = puzzle_text, ""

    categories: Dict[str, List[str]] = {}

    def _canonical_category_name(raw: str) -> str:
        lower = raw.lower().strip(" -")
        if "name" in lower or "names" in lower:
            return "Name"
        if "color" in lower:
            return "Color"
        if "nationality" in lower or "nationalities" in lower:
            return "Nationality"
        if "book" in lower and ("genre" in lower or "genres" in lower):
            return "BookGenre"
        if "book" in lower:
            return "Book"
        if "food" in lower or "lunch" in lower:
            return "Food"
        if "drink" in lower:
            return "Drink"
        if "animal" in lower or "pet" in lower:
            return "Animal"
        if "occupation" in lower or "job" in lower:
            return "Occupation"
        if "phone" in lower and ("model" in lower or "models" in lower):
            return "PhoneModel"
        if "phone" in lower:
            return "Phone"
        if "car" in lower and ("model" in lower or "models" in lower):
            return "CarModel"
        if "sport" in lower or "sports" in lower:
            return "Sport"
        if "music" in lower:
            return "Music"
        if "height" in lower:
            return "Height"
        if "child" in lower:
            return "Child"
        return f"Attr_{len(categories)}"

    def _parse_values(values_text: str) -> List[str]:
        raw_vals = values_text.split(",")
        clean_vals: List[str] = []
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
        if line.lower().startswith("clues:"):
            continue

        if line.startswith("-"):
            desc_text, values_text = line.split(":", 1)
        else:
            desc_text, values_text = line.split(":", 1)

        key = _canonical_category_name(desc_text)
        values = _parse_values(values_text)
        if values:
            categories[key] = values

    # If names are not explicitly listed, infer from clue text and pad.
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
        names: List[str] = []
        for c in candidates:
            if c in stop:
                continue
            if c not in names:
                names.append(c)
        if names:
            while len(names) < num_houses:
                names.append(f"Person_{len(names) + 1}")
            categories["Name"] = names

    # Build lookup from mentioned value -> category + canonical value
    value_lookup: Dict[str, _ValueRef] = {}
    for cat, vals in categories.items():
        for v in vals:
            key = str(v).strip().lower()
            if not key:
                continue
            # If duplicates exist across categories, keep the first.
            value_lookup.setdefault(key, _ValueRef(category=cat, value=str(v)))

    # 3) Variables
    variables: List[Variable] = []
    for house in range(1, num_houses + 1):
        for cat_name, cat_values in categories.items():
            variables.append(
                Variable(name=f"House_{house}_{cat_name}", domain=set(cat_values))
            )

    # 4) Constraints: AllDiff per category
    constraints: List[Constraint] = []
    for cat_name in categories.keys():
        constraints.append(
            Constraint.all_diff([f"House_{h}_{cat_name}" for h in range(1, num_houses + 1)])
        )

    def _var(house: int, category: str) -> str:
        return f"House_{house}_{category}"

    def _ordinal_to_int(token: str) -> Optional[int]:
        mapping = {
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "fifth": 5,
            "sixth": 6,
        }
        return mapping.get(token.strip().lower())

    def _find_value_refs(text: str) -> List[_ValueRef]:
        lowered = text.lower()
        hits: List[Tuple[int, int, _ValueRef]] = []
        for key in sorted(value_lookup.keys(), key=len, reverse=True):
            pattern = r"(?<![A-Za-z0-9_])" + re.escape(key) + r"(?![A-Za-z0-9_])"
            for m in re.finditer(pattern, lowered):
                hits.append((m.start(), m.end(), value_lookup[key]))

        hits.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        selected: List[Tuple[int, int, _ValueRef]] = []
        last_end = -1
        for start, end, ref in hits:
            if start < last_end:
                continue
            selected.append((start, end, ref))
            last_end = end

        selected.sort(key=lambda x: x[0])
        return [ref for _, _, ref in selected]

    def _pos_of(ref: _ValueRef, assignment: Dict[str, Any]) -> Optional[int]:
        for house in range(1, num_houses + 1):
            if assignment.get(_var(house, ref.category)) == ref.value:
                return house
        return None

    def _equals_in_house(ref: _ValueRef, house: int) -> Constraint:
        return Constraint.equals(_var(house, ref.category), ref.value)

    def _not_in_house_constraint(ref: _ValueRef, house: int, clue: str) -> Constraint:
        scope = [_var(h, ref.category) for h in range(1, num_houses + 1)]

        def _pred(assignment: Dict[str, Any]) -> bool:
            p = _pos_of(ref, assignment)
            return True if p is None else p != house

        return Constraint(description=clue, scope=scope, predicate=_pred)

    def _same_house_constraints(a: _ValueRef, b: _ValueRef, negate: bool, clue: str) -> List[Constraint]:
        out: List[Constraint] = []
        for house in range(1, num_houses + 1):
            var_a = _var(house, a.category)
            var_b = _var(house, b.category)

            def _pred(
                assignment: Dict[str, Any],
                va: str = var_a,
                vb: str = var_b,
                aval: str = a.value,
                bval: str = b.value,
                neg: bool = negate,
            ) -> bool:
                av = assignment.get(va)
                bv = assignment.get(vb)
                if av is None or bv is None:
                    return True
                if neg:
                    return not (av == aval and bv == bval)
                # equivalence: either both are present in this house or neither
                return not ((av == aval) ^ (bv == bval))

            out.append(Constraint(description=clue, scope=[var_a, var_b], predicate=_pred))
        return out

    def _positional_constraint(a: _ValueRef, b: _ValueRef, kind: str, clue: str) -> Constraint:
        scope = [_var(h, a.category) for h in range(1, num_houses + 1)]
        if b.category != a.category:
            scope += [_var(h, b.category) for h in range(1, num_houses + 1)]

        def _pred(assignment: Dict[str, Any]) -> bool:
            pa = _pos_of(a, assignment)
            pb = _pos_of(b, assignment)
            if pa is None or pb is None:
                return True
            if kind == "left_of":
                return pa < pb
            if kind == "right_of":
                return pa > pb
            if kind == "directly_left_of":
                return pa + 1 == pb
            if kind == "next_to":
                return abs(pa - pb) == 1
            if kind == "one_between":
                return abs(pa - pb) == 2
            if kind == "two_between":
                return abs(pa - pb) == 3
            return True

        return Constraint(description=clue, scope=scope, predicate=_pred)

    def _build_constraints_from_clue(clue_text: str) -> List[Constraint]:
        cleaned = clue_text.strip().replace("`", "")
        if not cleaned:
            return []
        lowered = cleaned.lower()
        refs = _find_value_refs(cleaned)

        # "<Name> lives in house N"
        m = re.search(r"\b([A-Z][a-z]+)\s+lives\s+in\s+house\s+(\d+)\b", cleaned)
        if m:
            house = int(m.group(2))
            if 1 <= house <= num_houses:
                name_key = m.group(1).lower()
                ref = value_lookup.get(name_key)
                if ref is not None:
                    return [_equals_in_house(ref, house)]

        # "<Name> lives in the <value> house" (common in small puzzles)
        if "lives in the" in lowered and " house" in lowered and len(refs) >= 2:
            name_ref = next((r for r in refs if r.category == "Name"), None)
            other_ref = next((r for r in refs if r.category != "Name"), None)
            if name_ref and other_ref:
                return _same_house_constraints(name_ref, other_ref, negate=False, clue=cleaned)

        # "... is in the <ordinal> house"
        m = re.search(r"\bis\s+in\s+the\s+(first|second|third|fourth|fifth|sixth)\s+house\b", lowered)
        if m and refs:
            house = _ordinal_to_int(m.group(1))
            if house is not None and 1 <= house <= num_houses:
                return [_equals_in_house(refs[0], house)]

        # "... is not in the <ordinal> house"
        m = re.search(r"\bis\s+not\s+in\s+the\s+(first|second|third|fourth|fifth|sixth)\s+house\b", lowered)
        if m and refs:
            house = _ordinal_to_int(m.group(1))
            if house is not None and 1 <= house <= num_houses:
                return [_not_in_house_constraint(refs[0], house, cleaned)]

        # "House N ..." -> prefer binding Color if present
        m = re.search(r"\bhouse\s+(\d+)\b", lowered)
        if m and refs:
            house = int(m.group(1))
            if 1 <= house <= num_houses:
                preferred = next((r for r in refs if r.category == "Color"), refs[0])
                return [_equals_in_house(preferred, house)]

        # "The <value> house contains/has the <value>"
        if len(refs) >= 2 and any(k in lowered for k in (" contains ", " has ", " contains the", " has the")):
            return _same_house_constraints(refs[0], refs[1], negate=False, clue=cleaned)

        # Positional relations
        if len(refs) >= 2:
            if any(k in lowered for k in ("directly left of", "immediately to the left of", "immediately left of")):
                return [_positional_constraint(refs[0], refs[1], "directly_left_of", cleaned)]
            if any(k in lowered for k in ("directly right of", "immediately to the right of", "immediately right of")):
                return [_positional_constraint(refs[1], refs[0], "directly_left_of", cleaned)]
            if "next to each other" in lowered:
                return [_positional_constraint(refs[0], refs[1], "next_to", cleaned)]
            if "one house between" in lowered:
                return [_positional_constraint(refs[0], refs[1], "one_between", cleaned)]
            if "one house in between" in lowered:
                return [_positional_constraint(refs[0], refs[1], "one_between", cleaned)]
            if "two houses between" in lowered:
                return [_positional_constraint(refs[0], refs[1], "two_between", cleaned)]
            if "somewhere" in lowered and "to the left of" in lowered:
                return [_positional_constraint(refs[0], refs[1], "left_of", cleaned)]
            if "somewhere" in lowered and "to the right of" in lowered:
                return [_positional_constraint(refs[0], refs[1], "right_of", cleaned)]
            if "to the left of" in lowered and "somewhere" not in lowered:
                return [_positional_constraint(refs[0], refs[1], "left_of", cleaned)]
            if "to the right of" in lowered and "somewhere" not in lowered:
                return [_positional_constraint(refs[0], refs[1], "right_of", cleaned)]

        # "X does not live in the Y house" (typically name + color)
        if "does not live in" in lowered and "house" in lowered and len(refs) >= 2:
            return _same_house_constraints(refs[0], refs[1], negate=True, clue=cleaned)

        # Generic positive/negative pairings (most ZebraLogicBench "X is Y")
        if len(refs) >= 2 and " is " in lowered:
            if " not " in lowered:
                return _same_house_constraints(refs[0], refs[1], negate=True, clue=cleaned)
            return _same_house_constraints(refs[0], refs[1], negate=False, clue=cleaned)

        return [Constraint(description=cleaned)]

    # Explicit clue constraints
    clue_matches = re.findall(r"\d+\.\s+(.*)", clues_part)
    for clue_text in clue_matches:
        constraints.extend(_build_constraints_from_clue(clue_text))

    return CSP(variables=variables, constraints=constraints)
