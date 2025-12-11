# Data Notes

- Primary source: `allenai/ZebraLogicBench` (Hugging Face). Store downloads under `data/raw/`.
- Derived artifacts (parsed CSP instances, cached constraints, traces) should live in `data/processed/` with clear filenames and metadata.
- Keep large artifacts out of git; rely on scripts in `scripts/` to reproduce downloads and preprocessing steps.
