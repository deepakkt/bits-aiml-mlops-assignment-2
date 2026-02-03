# Project State — Cats vs Dogs MLOps Assignment 2

## Completed Parts
- [x] Part 1 — Repo bootstrap + dev environment + scaffolding
- [x] Part 2 — Dataset acquisition + split manifests + preprocessing utilities + 1 unit test
- [x] Part 3 — Baseline model training + evaluation + MLflow logging + save `model.pkl`
- [x] Part 4 — Inference core + FastAPI service + 1 unit test
- [ ] Part 5 — Docker packaging (local run) + smoke-test script
- [ ] Part 6 — GitHub Actions CI (tests + build) + push to Docker Hub on main
- [ ] Part 7 — Kubernetes manifests + Minikube deploy + gated post-deploy smoke test
- [ ] Part 8 — Provisioning scripts: Minikube + Argo CD + GitOps app + Argo-gated smoke test
- [ ] Part 9 — GitOps image update automation (CI → manifests → Argo sync)
- [ ] Part 10 — Observability + post-deploy performance tracking + submission-ready packaging

## Global Conventions
- Python: 3.11
- Deterministic split seed (to be used in Part 2): **1337**
- Image preprocessing target: 224×224 RGB
- Dataset zip present: `data/cats-and-dogs-classification-dataset.zip` (do not delete)
- Extracted dataset root (expected): `data/raw/PetImages`
- Split manifests: `data/splits/{train,val,test}.txt` with `path<TAB>label` (repo-relative path)
- Split metadata: `data/splits/metadata.json` with seed/ratios/counts/class mapping
- Git-LFS rules: `data/raw/**`, `data/processed/**`, `data/*.zip`, `artifacts/model/*.pkl`

## Pinned Dependencies (Part 4)
- pytest==8.3.3 (test runner)
- numpy==1.26.4 (array handling for preprocessing)
- pillow==10.4.0 (image loading/preprocessing)
- kaggle==1.6.17 (Kaggle CLI for dataset download)
- scikit-learn==1.5.2 (baseline classifier + metrics)
- matplotlib==3.8.4 (training curve + confusion matrices)
- mlflow==2.12.1 (experiment tracking)
- fastapi==0.115.5 (inference API)
- uvicorn==0.30.6 (ASGI server)
- prometheus-client==0.20.0 (metrics export)
- python-multipart==0.0.9 (multipart uploads)

## Model/Training Conventions (Part 3)
- Baseline features: normalized RGB color histograms (8 bins per channel, 24-dim)
- Model: `SGDClassifier(loss="log_loss")` with deterministic seed
- Augmentation (train-only): random horizontal flip, +/- 15 deg rotation, brightness/contrast jitter
- MLflow tracking: local `mlruns/` by default (override with `--mlflow-uri`)
- Model bundle: `ModelBundle` pickle at `artifacts/model/model.pkl` with preprocessing + feature config metadata

## Inference Service (Part 4)
- FastAPI app: `app/main.py`
- Model path env var: `MODEL_PATH` (default `artifacts/model/model.pkl`)
- Endpoints: `/health`, `/predict`, `/metrics`

## Container/Image Conventions
- Docker image name: `docker.io/<dockerhub_username>/cats-dogs-classifier`
- Tag format: `:<git_sha>` (and optionally `:latest` on main)

## Kubernetes Conventions (planned)
- Namespace: `cats-dogs`
- Service name: `cats-dogs-api`
- Container/service port: `8000`
- Port-forward (planned): `kubectl -n cats-dogs port-forward svc/cats-dogs-api 8000:8000`

## Argo CD Conventions (planned)
- App name: `cats-dogs`
- Sync method: manual trigger initially; auto-sync decision in Part 8/9

## Prometheus/Grafana Strategy (planned)
- Prefer ServiceMonitor via kube-prometheus-stack
- Scrape `/metrics` on the FastAPI service

## How To Verify (Part 3)
```bash
./scripts/dev/download_dataset.sh
./scripts/dev/generate_splits.sh
./scripts/dev/run_tests.sh
PYTHONPATH=src python -m cats_dogs.train
```

## How To Verify (Part 4)
```bash
./scripts/dev/run_tests.sh
PYTHONPATH=src uvicorn app.main:app --host 0.0.0.0 --port 8000
curl http://localhost:8000/health
curl -F "file=@data/raw/PetImages/Cat/0.jpg" http://localhost:8000/predict
curl http://localhost:8000/metrics
```

## Next Part Notes
- Add Dockerfile to package FastAPI service and `model.pkl`.
- Create local docker run + smoke-test scripts (idempotent).
- Ensure container exposes port 8000 and health/predict endpoints.
