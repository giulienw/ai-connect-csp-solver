# AI Connect CSP Solver

Starter layout for building a CSP solver for logic grid (Zebra) puzzles and the related Kaggle challenge.

## Layout
- `solver.py`: Public solve interface that will call into `src/csp/`.
- `run.py`: CLI stub to load puzzles, run the solver, and write results.
- `requirements.md`: Notes on solver requirements and scoring.
- `docs/`: Architecture notes, data handling instructions, and developer guides.
- `data/`: Storage for datasets (`raw/`, `processed/`) and small `examples/` puzzles; placeholders are tracked.
- `src/csp/`: CSP core (models, parser, solver core).
- `src/utils/`: Shared utilities (I/O, config).
- `traces/`: Generated traces (`train/`, `val_test/`).
- `tests/`: Pytest placeholders for CSP core, parser, and solver.
- `notebooks/`: Optional exploratory notebooks (keep outputs small).

## Next steps
- Set up a virtual environment and dependency management.
- Implement data loading from ZebraLogicBench and translate puzzles into CSP variables/constraints.
- Add the baseline solver, trace generation, and evaluation scripts referenced in this layout.
