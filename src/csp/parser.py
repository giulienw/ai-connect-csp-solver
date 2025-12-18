from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple, Callable

from .model import CSP, Variable, Constraint



# Normalization / utilities
 

_STOP_CAPS = {
    "There",
    "Each",
    "House",
    "Houses",
    "Clues",
    "Colors",
    "Pets",
    "People",
    "Person",
    "Friends",
    "Friend",
    "The",
    "A",
    "An",
    "In",
    "On",
    "To",
    "Of",
    "And",
    "Is",
    "Are",
    "Was",
    "Were",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "First",
    "Second",
    "Third",
    "Left",
    "Right",
    "Immediately",
    "Between",
}

_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).lower()

def _strip_punct(s: str) -> str:
    return s.strip().strip(" \t\r\n. ;:!?,")

def _strip_article(s: str) -> str:
    # "the dog" -> "dog"
    return re.sub(r"^(the|a|an)\s+", "", s.strip(), flags=re.IGNORECASE)

def _clean_value_phrase(s: str) -> str:
    # clean a phrase that should map to a value in some category
    return _strip_punct(_strip_article(s)).strip()


def _parse_num_houses(puzzle_json: Dict[str, Any], puzzle_text: str) -> int:
    size_str = puzzle_json.get("size", "0*0")
    num_houses: Optional[int] = None

    try:
        a, _b = size_str.split("*", 1)
        num_houses = int(a)
    except Exception:
        num_houses = None

    if not num_houses or num_houses <= 0:
        m = re.search(r"numbered\s+1\s+to\s+(\d+)", puzzle_text, flags=re.IGNORECASE)
        if not m:
            m = re.search(r"There are\s+(\d+)\s+houses", puzzle_text, flags=re.IGNORECASE)
        num_houses = int(m.group(1)) if m else 5

    return num_houses


def _split_description_and_clues(puzzle_text: str) -> Tuple[str, str]:
    if "## Clues:" in puzzle_text:
        parts = puzzle_text.split("## Clues:", 1)
        return parts[0], parts[1]
    if "\nClues:" in puzzle_text:
        parts = puzzle_text.split("\nClues:", 1)
        return parts[0], parts[1]
    if "Clues:" in puzzle_text:
        parts = puzzle_text.split("Clues:", 1)
        return parts[0], parts[1]
    return puzzle_text, ""


def _canonical_category_name(raw: str, unknown_idx_ref: List[int], raw_to_key: Dict[str, str]) -> str:
    raw_clean = _strip_punct(raw).strip(" -–—\t")
    raw_key = _norm(raw_clean)

    if raw_key in raw_to_key:
        return raw_to_key[raw_key]

    lower = raw_key

    if any(k in lower for k in ["name", "person", "people", "friend"]):
        key = "Name"
    elif "color" in lower:
        key = "Color"
    elif "nationality" in lower:
        key = "Nationality"
    elif "book" in lower:
        key = "Book"
    elif any(k in lower for k in ["food", "lunch", "meal"]):
        key = "Food"
    elif "drink" in lower:
        key = "Drink"
    elif any(k in lower for k in ["animal", "pet", "pets"]):
        key = "Pet"
    elif any(k in lower for k in ["occupation", "job"]):
        key = "Occupation"
    elif "phone" in lower:
        key = "Phone"
    elif "music" in lower:
        key = "Music"
    elif "height" in lower:
        key = "Height"
    elif "child" in lower:
        key = "Child"
    else:
        key = f"Attr_{unknown_idx_ref[0]}"
        unknown_idx_ref[0] += 1

    raw_to_key[raw_key] = key
    return key


def _parse_values(values_text: str) -> List[str]:
    t = values_text.strip()
    t = t.replace("•", ",")
    t = t.replace(";", ",")
    t = t.replace("|", ",")
    t = re.sub(r"\s+and\s+", ", ", t, flags=re.IGNORECASE)
    t = t.replace("`", "")
    t = t.strip().rstrip(".")

    parts = [p.strip() for p in t.split(",")]
    out: List[str] = []
    for p in parts:
        p2 = _strip_punct(p)
        if p2:
            out.append(p2)
    return out


def _extract_categories(description_part: str) -> Dict[str, List[str]]:
    categories: Dict[str, List[str]] = {}
    unknown_idx_ref = [1]
    raw_to_key: Dict[str, str] = {}

    for raw_line in description_part.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("clues:"):
            continue
        if line.startswith("-"):
            line = line[1:].strip()

        m = re.match(r"^\s*([^:–—-]+)\s*[:–—-]\s*(.+)$", line)
        if not m:
            continue

        desc_text, values_text = m.group(1), m.group(2)
        key = _canonical_category_name(desc_text, unknown_idx_ref, raw_to_key)
        values = _parse_values(values_text)
        if values:
            categories[key] = values

    return categories


def _infer_names_from_clues(clues_part: str, num_houses: int) -> List[str]:
    """
    Improved name inference:
    - Collect capitalized tokens from clues section
    - Filter stopwords + number-words
    - Rank by frequency, take top num_houses
    - If fewer than num_houses, pad with Person_i
    """
    # Extract the clue text lines only (remove numbers like "1. ")
    clue_lines = []
    for ln in clues_part.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        ln = re.sub(r"^\s*\d+\.\s*", "", ln)
        clue_lines.append(ln)
    text = "\n".join(clue_lines)

    # Tokenize capitalized words
    tokens = re.findall(r"\b[A-Z][a-z]+\b", text)

    freq: Dict[str, int] = {}
    for tok in tokens:
        if tok in _STOP_CAPS:
            continue
        if _norm(tok) in _NUMBER_WORDS:
            continue
        freq[tok] = freq.get(tok, 0) + 1

    # Heuristic: prefer tokens that appear in common "name slots"
    # (e.g., "X lives", "X does not", "X owns") by adding weight
    slot_patterns = [
        r"\b([A-Z][a-z]+)\s+lives\b",
        r"\b([A-Z][a-z]+)\s+does\s+not\b",
        r"\b([A-Z][a-z]+)\s+owns\b",
        r"\b([A-Z][a-z]+)\s+has\b",
        r"\b([A-Z][a-z]+)\s+keeps\b",
    ]
    for pat in slot_patterns:
        for m in re.finditer(pat, text):
            name = m.group(1)
            if name in _STOP_CAPS:
                continue
            if _norm(name) in _NUMBER_WORDS:
                continue
            freq[name] = freq.get(name, 0) + 3  # slot bonus

    # Rank by freq desc, then name for determinism
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    names = [n for (n, _c) in ranked][:num_houses]

    if len(names) < num_houses:
        for i in range(len(names) + 1, num_houses + 1):
            names.append(f"Person_{i}")

    return names[:num_houses]


def _build_value_index(categories: Dict[str, List[str]]) -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for cat, vals in categories.items():
        for v in vals:
            nv = _norm(v)
            if nv not in idx:
                idx[nv] = cat
    return idx


 
# Constraint builders
 

def _alldiff_pred(scope: List[str]) -> Callable[[Dict[str, Any]], bool]:
    def _p(assignment: Dict[str, Any]) -> bool:
        vals = [assignment[v] for v in scope if v in assignment]
        return len(vals) == len(set(vals))
    return _p


def _unary_equals(var: str, value: str, desc: str) -> Constraint:
    def _p(a: Dict[str, Any]) -> bool:
        if var in a:
            return a[var] == value
        return True
    return Constraint(scope=[var], predicate=_p, description=desc)


def _find_positions_in_assignment(
    assignment: Dict[str, Any], category: str, target_value: str, num_houses: int
) -> Optional[int]:
    """Return house index i where House_i_category == target_value if known, else None."""
    for i in range(1, num_houses + 1):
        v = f"House_{i}_{category}"
        if v in assignment and assignment[v] == target_value:
            return i
    return None


def _link_biimplication(
    cat_a: str, val_a: str, cat_b: str, val_b: str, num_houses: int, desc: str
) -> Constraint:
    scope: List[str] = []
    for i in range(1, num_houses + 1):
        scope.append(f"House_{i}_{cat_a}")
        scope.append(f"House_{i}_{cat_b}")

    def _p(a: Dict[str, Any]) -> bool:
        for i in range(1, num_houses + 1):
            va = f"House_{i}_{cat_a}"
            vb = f"House_{i}_{cat_b}"
            if va in a and a[va] == val_a and vb in a and a[vb] != val_b:
                return False
            if vb in a and a[vb] == val_b and va in a and a[va] != val_a:
                return False
        return True

    return Constraint(scope=scope, predicate=_p, description=desc)


def _forbid_pair_same_house(
    cat_a: str, val_a: str, cat_b: str, val_b: str, num_houses: int, desc: str
) -> Constraint:
    scope: List[str] = []
    for i in range(1, num_houses + 1):
        scope.append(f"House_{i}_{cat_a}")
        scope.append(f"House_{i}_{cat_b}")

    def _p(a: Dict[str, Any]) -> bool:
        for i in range(1, num_houses + 1):
            va = f"House_{i}_{cat_a}"
            vb = f"House_{i}_{cat_b}"
            if va in a and vb in a and a[va] == val_a and a[vb] == val_b:
                return False
        return True

    return Constraint(scope=scope, predicate=_p, description=desc)


def _immediately_left_of_color(left_color: str, right_color: str, num_houses: int, desc: str) -> Constraint:
    scope = [f"House_{i}_Color" for i in range(1, num_houses + 1)]

    def _p(a: Dict[str, Any]) -> bool:
        last_var = f"House_{num_houses}_Color"
        if last_var in a and a[last_var] == left_color:
            return False
        first_var = "House_1_Color"
        if first_var in a and a[first_var] == right_color:
            return False

        for i in range(1, num_houses):
            vi = f"House_{i}_Color"
            vj = f"House_{i+1}_Color"
            if vi in a and a[vi] == left_color and vj in a and a[vj] != right_color:
                return False
            if vj in a and a[vj] == right_color and vi in a and a[vi] != left_color:
                return False

        pos_left = _find_positions_in_assignment(a, "Color", left_color, num_houses)
        pos_right = _find_positions_in_assignment(a, "Color", right_color, num_houses)
        if pos_left is not None and pos_right is not None:
            return pos_right == pos_left + 1
        return True

    return Constraint(scope=scope, predicate=_p, description=desc)


def _adjacent_by_values(cat_a: str, val_a: str, cat_b: str, val_b: str, num_houses: int, desc: str) -> Constraint:
    """
    abs(pos(val_a in cat_a) - pos(val_b in cat_b)) == 1
    """
    scope: List[str] = []
    for i in range(1, num_houses + 1):
        scope.append(f"House_{i}_{cat_a}")
        scope.append(f"House_{i}_{cat_b}")

    def _p(a: Dict[str, Any]) -> bool:
        pa = _find_positions_in_assignment(a, cat_a, val_a, num_houses)
        pb = _find_positions_in_assignment(a, cat_b, val_b, num_houses)
        if pa is not None and pb is not None:
            return abs(pa - pb) == 1
        # Early pruning: if pa known at an edge, pb cannot be at the opposite non-adjacent positions.
        # Keep this conservative.
        return True

    return Constraint(scope=scope, predicate=_p, description=desc)


def _ordered_by_values(cat_a: str, val_a: str, cat_b: str, val_b: str, num_houses: int, desc: str, direction: str) -> Constraint:
    """
    direction='left': pos(a) < pos(b)
    direction='right': pos(a) > pos(b)
    """
    scope: List[str] = []
    for i in range(1, num_houses + 1):
        scope.append(f"House_{i}_{cat_a}")
        scope.append(f"House_{i}_{cat_b}")

    def _p(a: Dict[str, Any]) -> bool:
        pa = _find_positions_in_assignment(a, cat_a, val_a, num_houses)
        pb = _find_positions_in_assignment(a, cat_b, val_b, num_houses)
        if pa is not None and pb is not None:
            return pa < pb if direction == "left" else pa > pb
        return True

    return Constraint(scope=scope, predicate=_p, description=desc)


def _distance_by_values(cat_a: str, val_a: str, cat_b: str, val_b: str, num_houses: int, dist: int, desc: str) -> Constraint:
    """
    Exactly dist houses between => abs(pos(a) - pos(b)) == dist + 1
    """
    scope: List[str] = []
    for i in range(1, num_houses + 1):
        scope.append(f"House_{i}_{cat_a}")
        scope.append(f"House_{i}_{cat_b}")

    def _p(a: Dict[str, Any]) -> bool:
        pa = _find_positions_in_assignment(a, cat_a, val_a, num_houses)
        pb = _find_positions_in_assignment(a, cat_b, val_b, num_houses)
        if pa is not None and pb is not None:
            return abs(pa - pb) == dist + 1
        return True

    return Constraint(scope=scope, predicate=_p, description=desc)


 
# Clue compiler
 

def _compile_clue(
    clue_text: str,
    categories: Dict[str, List[str]],
    value_to_cat: Dict[str, str],
    num_houses: int,
) -> List[Constraint]:
    t = clue_text.strip()
    t_clean = _strip_punct(t)

    constraints: List[Constraint] = []

    # 1) "House k is painted <color>." / "House k is <color>."
    m = re.match(r"^House\s+(\d+)\s+is\s+(?:painted\s+)?([A-Za-z][A-Za-z\s-]*)$", t_clean, flags=re.IGNORECASE)
    if m:
        k = int(m.group(1))
        val = _clean_value_phrase(m.group(2))
        cat = "Color" if "Color" in categories else value_to_cat.get(_norm(val), "Color")
        var = f"House_{k}_{cat}"
        constraints.append(_unary_equals(var, val, desc=t_clean))
        return constraints

    # 2) "<Name> lives in house k."
    m = re.match(r"^([A-Z][a-z]+)\s+lives\s+in\s+house\s+(\d+)$", t_clean)
    if m:
        name = m.group(1)
        k = int(m.group(2))
        var = f"House_{k}_Name"
        constraints.append(_unary_equals(var, name, desc=t_clean))
        return constraints

    # 3) "The person in house k owns the <X>."
    m = re.match(r"^The\s+person\s+in\s+house\s+(\d+)\s+owns\s+the\s+(.+)$", t_clean, flags=re.IGNORECASE)
    if m:
        k = int(m.group(1))
        val = _clean_value_phrase(m.group(2))
        cat = value_to_cat.get(_norm(val))
        if cat:
            var = f"House_{k}_{cat}"
            constraints.append(_unary_equals(var, val, desc=t_clean))
            return constraints

    # 4) "<Name> lives in the <value> house."
    m = re.match(r"^([A-Z][a-z]+)\s+lives\s+in\s+the\s+(.+)\s+house$", t_clean, flags=re.IGNORECASE)
    if m:
        name = m.group(1)
        val = _clean_value_phrase(m.group(2))
        cat_val = value_to_cat.get(_norm(val))
        if cat_val:
            constraints.append(_link_biimplication("Name", name, cat_val, val, num_houses, desc=t_clean))
            return constraints

    # 5) "The <valueA> house contains the <valueB>."
    m = re.match(r"^The\s+(.+)\s+house\s+contains\s+the\s+(.+)$", t_clean, flags=re.IGNORECASE)
    if m:
        val_a = _clean_value_phrase(m.group(1))
        val_b = _clean_value_phrase(m.group(2))
        cat_a = value_to_cat.get(_norm(val_a))
        cat_b = value_to_cat.get(_norm(val_b))
        if cat_a and cat_b and cat_a != cat_b:
            constraints.append(_link_biimplication(cat_a, val_a, cat_b, val_b, num_houses, desc=t_clean))
            return constraints

    # 6) "<Name> does not live in the <value> house."
    m = re.match(r"^([A-Z][a-z]+)\s+does\s+not\s+live\s+in\s+the\s+(.+)\s+house$", t_clean, flags=re.IGNORECASE)
    if m:
        name = m.group(1)
        val = _clean_value_phrase(m.group(2))
        cat_val = value_to_cat.get(_norm(val))
        if cat_val:
            constraints.append(_forbid_pair_same_house("Name", name, cat_val, val, num_houses, desc=t_clean))
            return constraints

    # 7) "The <color1> house is immediately to the left of the <color2> house."
    m = re.match(
        r"^The\s+(.+)\s+house\s+is\s+immediately\s+to\s+the\s+left\s+of\s+the\s+(.+)\s+house$",
        t_clean,
        flags=re.IGNORECASE,
    )
    if m:
        c1 = _clean_value_phrase(m.group(1))
        c2 = _clean_value_phrase(m.group(2))
        if value_to_cat.get(_norm(c1)) == "Color" and value_to_cat.get(_norm(c2)) == "Color":
            constraints.append(_immediately_left_of_color(c1, c2, num_houses, desc=t_clean))
            return constraints

    # 8) Ownership: "<Name> owns/has/keeps the <X>."
    m = re.match(r"^([A-Z][a-z]+)\s+(owns|has|keeps)\s+the\s+(.+)$", t_clean, flags=re.IGNORECASE)
    if m:
        name = m.group(1)
        val = _clean_value_phrase(m.group(3))
        cat = value_to_cat.get(_norm(val))
        if cat:
            constraints.append(_link_biimplication("Name", name, cat, val, num_houses, desc=t_clean))
            return constraints

    # 9) Reverse ownership: "The <X> belongs to <Name>."
    m = re.match(r"^The\s+(.+)\s+belongs\s+to\s+([A-Z][a-z]+)$", t_clean, flags=re.IGNORECASE)
    if m:
        val = _clean_value_phrase(m.group(1))
        name = m.group(2)
        cat = value_to_cat.get(_norm(val))
        if cat:
            constraints.append(_link_biimplication(cat, val, "Name", name, num_houses, desc=t_clean))
            return constraints

    # 10) Adjacency: "... next to ..."
    # Examples:
    # - "Alice lives next to the dog."
    # - "The red house is next to the blue house."
    m = re.match(r"^(?:The\s+)?(.+?)\s+(?:house\s+)?(?:lives\s+)?is\s+next\s+to\s+(?:the\s+)?(.+?)(?:\s+house)?$", t_clean, flags=re.IGNORECASE)
    if not m:
        m = re.match(r"^(.+?)\s+lives\s+next\s+to\s+(?:the\s+)?(.+)$", t_clean, flags=re.IGNORECASE)
    if m:
        left = _clean_value_phrase(m.group(1))
        right = _clean_value_phrase(m.group(2))

        # left/right might be a Name or a value in another category
        cat_left = "Name" if re.fullmatch(r"[A-Z][a-z]+", left) and left in categories.get("Name", []) else value_to_cat.get(_norm(left))
        val_left = left
        if cat_left is None and re.fullmatch(r"[A-Z][a-z]+", left):
            cat_left = "Name"

        cat_right = "Name" if re.fullmatch(r"[A-Z][a-z]+", right) and right in categories.get("Name", []) else value_to_cat.get(_norm(right))
        val_right = right
        if cat_right is None and re.fullmatch(r"[A-Z][a-z]+", right):
            cat_right = "Name"

        if cat_left and cat_right and cat_left != cat_right:
            constraints.append(_adjacent_by_values(cat_left, val_left, cat_right, val_right, num_houses, desc=t_clean))
            return constraints

    # 11) Non-immediate ordering:
    # "The red house is to the left of the blue house."
    m = re.match(
        r"^The\s+(.+)\s+house\s+is\s+to\s+the\s+(left|right)\s+of\s+the\s+(.+)\s+house$",
        t_clean,
        flags=re.IGNORECASE,
    )
    if m:
        a = _clean_value_phrase(m.group(1))
        direction = m.group(2).lower()
        b = _clean_value_phrase(m.group(3))
        if value_to_cat.get(_norm(a)) == "Color" and value_to_cat.get(_norm(b)) == "Color":
            constraints.append(_ordered_by_values("Color", a, "Color", b, num_houses, desc=t_clean, direction=direction))
            return constraints

    # 12) Distance: "There is one house between X and Y." / "There are two houses between X and Y."
    m = re.match(
        r"^There\s+(?:is|are)\s+(\w+)\s+house(?:s)?\s+between\s+(.+)\s+and\s+(.+)$",
        t_clean,
        flags=re.IGNORECASE,
    )
    if m:
        dist_token = _norm(m.group(1))
        dist = _NUMBER_WORDS.get(dist_token)
        if dist is None:
            try:
                dist = int(dist_token)
            except Exception:
                dist = None
        if dist is not None:
            x = _clean_value_phrase(m.group(2))
            y = _clean_value_phrase(m.group(3))
            cat_x = "Name" if re.fullmatch(r"[A-Z][a-z]+", x) else value_to_cat.get(_norm(x))
            cat_y = "Name" if re.fullmatch(r"[A-Z][a-z]+", y) else value_to_cat.get(_norm(y))
            if cat_x and cat_y and cat_x != cat_y:
                constraints.append(_distance_by_values(cat_x, x, cat_y, y, num_houses, dist=dist, desc=t_clean))
                return constraints

    # Fallback: keep as non-binding for debugging
    constraints.append(Constraint(description=t_clean))
    return constraints


 
# Main parse function
 

def parse_puzzle(puzzle_json: Dict[str, Any]) -> CSP:
    puzzle_text = puzzle_json.get("puzzle", "") or ""

    # 1) Houses
    num_houses = _parse_num_houses(puzzle_json, puzzle_text)

    # 2) Split description and clues
    description_part, clues_part = _split_description_and_clues(puzzle_text)

    # 3) Categories
    categories = _extract_categories(description_part)

    # Ensure Name category exists (infer from clues if missing)
    if "Name" not in categories:
        categories["Name"] = _infer_names_from_clues(clues_part, num_houses)

    # 4) Variables
    variables: List[Variable] = []
    for i in range(1, num_houses + 1):
        for cat_name, cat_values in categories.items():
            var_name = f"House_{i}_{cat_name}"
            variables.append(Variable(name=var_name, domain=set(cat_values)))

    # 5) Constraints
    constraints: List[Constraint] = []

    # AllDiff constraints (explicit, enforceable)
    for cat_name in categories.keys():
        scope_vars = [f"House_{i}_{cat_name}" for i in range(1, num_houses + 1)]
        constraints.append(
            Constraint(scope=scope_vars, predicate=_alldiff_pred(scope_vars), description=f"AllDiff({cat_name})")
        )

    # Compile clue constraints
    value_to_cat = _build_value_index(categories)

    # Extract numbered clues if present; otherwise treat each non-empty line as a clue.
    clue_matches = re.findall(r"^\s*\d+\.\s+(.*)$", clues_part, flags=re.MULTILINE)
    if not clue_matches:
        clue_matches = [ln.strip() for ln in clues_part.splitlines() if ln.strip()]

    for clue_text in clue_matches:
        constraints.extend(_compile_clue(clue_text, categories, value_to_cat, num_houses))

    return CSP(variables=variables, constraints=constraints)
