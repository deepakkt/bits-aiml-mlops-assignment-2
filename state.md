# Project State — Cats vs Dogs MLOps Assignment 2

## Completed Parts
- [x] Part 1 — Repo bootstrap + dev environment + scaffolding
- [ ] Part 2 — Dataset acquisition + split manifests + preprocessing utilities + 1 unit test
- [ ] Part 3 — Baseline model training + evaluation + MLflow logging + save `model.pkl`
- [ ] Part 4 — Inference core + FastAPI service + 1 unit test
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
- Git-LFS rules: `data/raw/**`, `data/processed/**`, `data/*.zip`, `artifacts/model/*.pkl`

## Pinned Dependencies (Part 1)
- pytest==8.3.3 (test runner; minimal scaffold)

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

## How To Verify (Part 1)
```bash
./scripts/dev/create_venv.sh
./scripts/dev/run_tests.sh
```

## Next Part Notes
- Implement Kaggle download script and deterministic split manifests.
- Add preprocessing utility (224×224 RGB) and a unit test using a dummy image.
- Update README/state with dataset handling and split metadata.
