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

## Training (Part 3)

Train the baseline model and log results to MLflow:

```bash
./scripts/dev/create_venv.sh
source .venv/bin/activate
PYTHONPATH=src python -m cats_dogs.train
```

Make sure the dataset is downloaded and split manifests are generated first (see section above).

Optional flags:

- `--verbose` to print per-epoch metrics
- `--device {cpu,mps,cuda}` (recorded in metadata; baseline uses scikit-learn so runs on CPU)

Artifacts produced:

- `artifacts/model/model.pkl`
- `artifacts/figures/` (training curve + confusion matrices)

Optional MLflow UI (uses local `mlruns/` by default):

```bash
mlflow ui --backend-store-uri mlruns
```
