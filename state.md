# Project State — Cats vs Dogs MLOps Assignment 2

## Completed Parts
- [x] Part 1 — Repo bootstrap + dev environment + scaffolding
- [x] Part 2 — Dataset acquisition + split manifests + preprocessing utilities + 1 unit test
- [x] Part 3 — Baseline model training + evaluation + MLflow logging + save `model.pkl`
- [x] Part 4 — Inference core + FastAPI service + 1 unit test
- [x] Part 5 — Docker packaging (local run) + smoke-test script
- [x] Part 6 — GitHub Actions CI (tests + build) + push to Docker Hub on main
- [x] Part 7 — Kubernetes manifests + Minikube deploy + gated post-deploy smoke test
- [x] Part 8 — Provisioning scripts: Minikube + Argo CD + GitOps app + Argo-gated smoke test
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
- Local default `DOCKERHUB_USERNAME`: `local`
- Local default `IMAGE_TAG`: `local`
- Local container name: `cats-dogs-api`
- Local host port: `8000`

## CI/CD (Part 6)
- Workflow: `.github/workflows/ci.yaml`
- PR/push: install deps, run `pytest`, build Docker image
- main: push `docker.io/<DOCKERHUB_USERNAME>/cats-dogs-classifier:<git_sha>`
- Required GitHub secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`

## Kubernetes Conventions (Part 7)
- Namespace: `cats-dogs`
- Service name: `cats-dogs-api`
- Container/service port: `8000`
- Deployment: `cats-dogs-api`
- Smoke test Job: `cats-dogs-smoke-test`
- Resource requests/limits (container):
  - requests: cpu `100m`, memory `256Mi`
  - limits: cpu `500m`, memory `512Mi`
- Port-forward: `kubectl -n cats-dogs port-forward svc/cats-dogs-api 8000:8000`

## Argo CD Conventions (Part 8)
- App name: `cats-dogs`
- Namespace: `argocd`
- Application manifest: `argocd/application.yaml`
- Source path: `k8s/overlays/dev`
- Repo URL (default): `https://github.com/deepakkt/bits-aiml-mlops-assignment-2.git` (update if forked)
- Sync method: manual trigger initially; use `scripts/dev/argocd_sync_and_wait.sh`
- Sync options: `CreateNamespace=true`
- RBAC default role (local dev): `role:admin` (override with `ARGOCD_RBAC_DEFAULT_ROLE`)
- Smoke test hook: Job `cats-dogs-smoke-test`
  - Hook type: `PostSync`
  - Delete policy: `HookSucceeded,HookFailed`

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

## How To Verify (Part 5)
```bash
./scripts/dev/run_docker.sh
./scripts/dev/smoke_test_local.sh
```

## How To Verify (Part 6)
```bash
git checkout -b ci-test
git commit --allow-empty -m "ci test"
git push origin ci-test
# Open a PR from ci-test -> CI runs tests + docker build
# Merge to main with secrets set -> image pushes to Docker Hub with tag = git SHA
```

## How To Verify (Part 7)
```bash
minikube start

# Build/load image into Minikube (choose one)
eval $(minikube -p minikube docker-env)
docker build -f docker/Dockerfile -t docker.io/local/cats-dogs-classifier:local .

# Or: docker build -f docker/Dockerfile -t docker.io/local/cats-dogs-classifier:local . && minikube image load docker.io/local/cats-dogs-classifier:local

./scripts/dev/deploy_minikube.sh

kubectl -n cats-dogs port-forward svc/cats-dogs-api 8000:8000
curl http://localhost:8000/health
```

## How To Verify (Part 8)
```bash
./scripts/provision/minikube_start.sh
./scripts/provision/argocd_install.sh
./scripts/provision/argocd_bootstrap_app.sh

kubectl -n argocd port-forward svc/argocd-server 8080:443
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 --decode; echo
argocd login localhost:8080 --username admin --password <password> --insecure

./scripts/dev/argocd_sync_and_wait.sh
```

## Next Part Notes
- Add GitOps image update automation in CI (update kustomize tag on main).
- Keep Argo CD hook gating and surface failure in sync logs/CLI.
