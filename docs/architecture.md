# Architecture Overview

System supports ZebraLogicBench (~1,000 logic grid puzzles, 2–6 houses and 2–6 attribute categories). Goal: maximize `Accuracy (%) – 10 × (AvgSteps / MaxAvgSteps)` where steps reflect search effort.

## Core Components
- **Data Loader**: Parse Hugging Face JSON into CSP structures (variables for house/attribute pairs, category-specific domains, and constraints from clues).
- **CSP Solver**: Backtracking engine with MRV variable ordering, forward checking, and arc consistency to prune domains during search.
- **Trace Generator**: Hooks that log decision states (domain sizes, active constraints, chosen variable/value) as feature vectors for analysis or ML augmentation.
- **Evaluator**: Runs the solver on validation/test splits, reporting solve rate, average backtracks/steps, and composite score.

## Data Flow
Hugging Face Dataset → Data Loader → CSP Model → Solver + Tracer → Solution Grid → Evaluator

## Constraint Typing (examples)
- **Equality**: `"German is Bob"` → nationality(house) = german iff name(house) = bob.
- **Positional**: `"one house between X and Y"` → `|pos(X) - pos(Y)| = 2`.
- **Relative**: `"left of"` → `pos(X) < pos(Y)`.

## Solver Sketch
```python
def solve(csp):
    if all_assigned(csp):
        return solution_grid(csp)
    var = select_mrv(csp)  # smallest domain
    for val in domain(var):
        if consistent(csp, var, val):
            assign(var, val)
            trace_log(csp.state)  # domain sizes, constraints, choice
            result = solve(csp)
            if result:
                return result
            backtrack(csp)
    return failure
```

Forward checking updates neighbor domains after assignments; arc consistency iteratively revises pairs to maintain consistency before deeper search.

## Milestones (suggested)
- Week 1: Loader + baseline solver on small puzzles (e.g., `lgp-test-2x2-33`); generate traces.
- Week 2: Validate across sizes, run held-out Kaggle set, and report accuracy/step metrics with trace visualizations.
