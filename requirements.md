# Solver Requirements (notes)

- Parse ZebraLogicBench puzzles (entities, clues, solution grids) into CSP variables/domains/constraints.
- Implement backtracking with MRV variable ordering, forward checking, and arc consistency (AC-3 style).
- Support constraint types: equality, relative/positional (left of, one-between, etc.), and category uniqueness.
- Log trace features per decision: chosen var/value, domain sizes, active constraints, backtracks/steps.
- Evaluate on validation/test splits with composite score: Accuracy (%) – 10 × (AvgSteps / MaxAvgSteps).
- Keep CLI/script entry points for running solver, generating traces, and evaluations reproducibly.
