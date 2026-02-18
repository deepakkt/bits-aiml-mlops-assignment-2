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

## Inference API (Part 4)

Ensure `artifacts/model/model.pkl` exists (run the training step above).

Start the FastAPI service:

```bash
./scripts/dev/create_venv.sh
source .venv/bin/activate
PYTHONPATH=src uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Endpoints:

- `GET /health` (model/build info)
- `POST /predict` (multipart form field `file`)
- `GET /metrics` (Prometheus)

Example calls:

```bash
curl http://localhost:8000/health
curl -F "file=@data/raw/PetImages/Cat/0.jpg" http://localhost:8000/predict
curl http://localhost:8000/metrics
```

Set `MODEL_PATH` if the model lives somewhere else (default is `artifacts/model/model.pkl`).

## Docker (Part 5)

Build and run the API container locally:

```bash
./scripts/dev/run_docker.sh
```

Run the smoke test (health + predict):

```bash
./scripts/dev/smoke_test_local.sh
```

Optional environment variables:

- `DOCKERHUB_USERNAME` (default: `local`)
- `IMAGE_TAG` (default: `local`)
- `CONTAINER_NAME` (default: `cats-dogs-api`)
- `HOST_PORT` (default: `8000`)
- `API_URL` (default: `http://localhost:8000` for smoke tests)

## GitHub Actions CI (Part 6 + 9)

On every push and pull request, CI installs dependencies, runs `pytest`, and builds the Docker image.

On `main`, the workflow:

- pushes `docker.io/<DOCKERHUB_USERNAME>/cats-dogs-classifier:<git_sha>`
- updates `k8s/overlays/dev/kustomization.yaml` to the same image SHA
- commits the GitOps manifest update back to `main` using `github-actions[bot]` and `GITHUB_TOKEN`

Required GitHub repository secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

## Kubernetes on Minikube (Part 7)

Build/load the image into Minikube (choose one):

```bash
# Option A: build directly in Minikube's Docker daemon
eval $(minikube -p minikube docker-env)
docker build -f docker/Dockerfile -t docker.io/local/cats-dogs-classifier:local .

# Option B: build locally and load into Minikube
docker build -f docker/Dockerfile -t docker.io/local/cats-dogs-classifier:local .
minikube image load docker.io/local/cats-dogs-classifier:local
```

Deploy and run the gated in-cluster smoke test:

```bash
./scripts/dev/deploy_minikube.sh
```

Standalone smoke test (re-runnable):

```bash
./scripts/dev/smoke_test_k8s.sh
```

Port-forward for local access:

```bash
kubectl -n cats-dogs port-forward svc/cats-dogs-api 8000:8000
curl http://localhost:8000/health
```

If you need to tweak image tags or env vars, edit `k8s/overlays/dev/kustomization.yaml`.

## Argo CD + GitOps (Part 8 + 9)

Provision Minikube and install Argo CD:

```bash
./scripts/provision/minikube_start.sh
./scripts/provision/argocd_install.sh
```

`argocd_install.sh` sets RBAC defaults for local dev; override with `ARGOCD_RBAC_DEFAULT_ROLE` if needed.

Register the Argo CD Application:

```bash
./scripts/provision/argocd_bootstrap_app.sh
```

If you forked the repo, update `argocd/application.yaml` with your repo URL before bootstrapping.

The Application is configured with automated sync (`prune` + `selfHeal`), so new manifest commits from CI are deployed without manual intervention.

Access the Argo CD UI and get the admin password:

```bash
kubectl -n argocd port-forward svc/argocd-server 8080:443
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 --decode; echo
```

Login with the CLI and validate deployment state:

```bash
argocd login localhost:8080 --username admin --password <password> --insecure
./scripts/dev/argocd_sync_and_wait.sh
```

If the repo is private, add repo credentials in Argo CD before syncing.

`argocd_sync_and_wait.sh` exits non-zero on sync/health/hook failure and prints app status/history.

## Deployment Failure Surfacing (Part 9)

The smoke test Job remains a `PostSync` Argo hook. If it fails, Argo marks the sync as failed.

Observe failure in Argo UI:

- open app `cats-dogs`
- check Sync Status / Operation State for failed hook details

Observe failure via CLI:

```bash
argocd app get cats-dogs
argocd app history cats-dogs
./scripts/dev/argocd_sync_and_wait.sh
```

## Part 8 + 9 Combined Flow

```bash
./scripts/provision/minikube_start.sh

./scripts/provision/argocd_install.sh
./scripts/provision/argocd_bootstrap_app.sh

kubectl -n argocd port-forward svc/argocd-server 8080:443
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 --decode; echo
argocd login localhost:8080 --username admin --password <password> --insecure

./scripts/dev/argocd_sync_and_wait.sh

kubectl -n cats-dogs port-forward svc/cats-dogs-api 8000:8000
curl http://localhost:8000/health
```
