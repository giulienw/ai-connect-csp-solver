## Data

This repo expects ZebraLogicBench puzzle files (e.g. `test.parquet`) to be provided externally.

### Kaggle

- Add the ZebraLogicBench dataset as a Kaggle Dataset/Competition input.
- Run the solver with a parquet input path, e.g.:
  - `python run.py /kaggle/input/<dataset>/test.parquet --output /kaggle/working/submission.csv`

### Hugging Face (download)

You can download ZebraLogicBench directly from Hugging Face and save it under `data/`.

Example (Python):

```python
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    repo_id="allenai/ZebraLogicBench",
    repo_type="dataset",
    filename="grid_mode/test-00000-of-00001.parquet",
)
print(path)
```

