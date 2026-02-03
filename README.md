# Cats vs Dogs — MLOps Assignment 2

## Quickstart

1) Create a Python 3.11 virtual environment and install deps:

```bash
./scripts/dev/create_venv.sh
```

2) Run tests:

```bash
./scripts/dev/run_tests.sh
```

## Dataset & splits (Part 2)

Kaggle credentials are required only if the dataset zip is missing. Provide either:

- `~/.kaggle/kaggle.json`, or
- `KAGGLE_USERNAME` and `KAGGLE_KEY` env vars

Download/extract the dataset and generate deterministic split manifests:

```bash
./scripts/dev/download_dataset.sh
./scripts/dev/generate_splits.sh
```

Split manifest format:

- `data/splits/{train,val,test}.txt` contains `path<TAB>label` (repo-relative path).
- `data/splits/metadata.json` records the seed, ratios, counts, and class mapping.

Preprocessing is implemented in `src/cats_dogs/data.py` (224×224 RGB, float32 [0, 1]).
