## M1 — Model Development & Experiment Tracking (10M)
| Sub-criterion (marks)         | Assignment requirement                                           | Assignment ref | Full-credit evidence I’d expect                                              | Prompt coverage | Status  |
| ----------------------------- | ---------------------------------------------------------------- | -------------- | ---------------------------------------------------------------------------- | --------------- | ------- |
| Data & code versioning (3)    | Git for code; DVC or Git-LFS for dataset + preprocessed tracking |                | `.gitattributes` + `git lfs ls-files`; split manifests committed; no secrets | Parts 1–2       | **Met** |
| Baseline model (3)            | Implement at least one baseline model                            |                | Reproducible training script; baseline clearly described                     | Part 3          | **Met** |
| Serialized model artifact (2) | Save trained model in standard format (e.g., `.pkl`)             |                | `artifacts/model/model.pkl` exists and is loadable by serving code           | Part 3          | **Met** |
| Experiment tracking (2)       | Log runs/params/metrics/artifacts (conf matrix, loss curves)     |                | MLflow contains metrics + images; final run is identifiable                  | Part 3          | **Met** |

## M2 — Model Packaging & Containerization (10M)
| Sub-criterion (marks)               | Assignment requirement                                                             | Assignment ref | Full-credit evidence I’d expect                                                | Prompt coverage | Status  |
| ----------------------------------- | ---------------------------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------------ | --------------- | ------- |
| Inference REST service (4)          | REST API using FastAPI/Flask; endpoints: health + prediction returning probs/label |                | `/health` includes model/version; `/predict` returns label+prob; stable schema | Part 4          | **Met** |
| Env spec + pinned deps (2)          | `requirements.txt` with version pinning                                            |                | Fully pinned, reproducible install                                             | Part 1          | **Met** |
| Containerization + local verify (4) | Dockerfile; build/run locally; verify via curl/Postman                             |                | `docker build/run` instructions + smoke test                                   | Part 5          | **Met** |

## M3 — CI Pipeline for Build, Test & Image Creation (10M)
| Sub-criterion (marks)   | Assignment requirement                                                         | Assignment ref | Full-credit evidence I’d expect                  | Prompt coverage                        | Status  |
| ----------------------- | ------------------------------------------------------------------------------ | -------------- | ------------------------------------------------ | -------------------------------------- | ------- |
| Automated tests (4)     | Unit tests for one preprocessing + one model utility/inference; run via pytest |                | Tests run locally and in CI; small fixtures only | Parts 2 & 4 (tests) + Part 6 (CI runs) | **Met** |
| CI setup (4)            | On every push/MR: checkout, install deps, run tests, build image               |                | Clean workflow file; PR builds don’t push        | Part 6                                 | **Met** |
| Artifact publishing (2) | Push Docker image to a registry                                                |                | SHA-tagged image pushed; documented secrets      | Part 6                                 | **Met** |

## M4 — CD Pipeline & Deployment (10M)
| Sub-criterion (marks)             | Assignment requirement                                           | Assignment ref | Full-credit evidence I’d expect                                                 | Prompt coverage                                                               | Status  |
| --------------------------------- | ---------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |---------|
| Deployment target + manifests (4) | Choose target (e.g., minikube); define Deployment + Service YAML |                | Readiness/liveness probes; reproducible deploy                                  | Part 7                                                                        | **Met** |
| CD / GitOps flow (4)              | Pull new image & deploy/update automatically on main             |                | CI updates manifest image tag; Argo reconciles                                  | Parts 8–9                                                                     | **Met** |
| Smoke tests & fail on failure (2) | Post-deploy smoke test; fail pipeline if smoke tests fail        |                | **Automated gate** that blocks “successful deploy” if `/health`+`/predict` fail | Part 7  | **Met** |

## M5 — Monitoring, Logs & Final Submission (10M)
| Sub-criterion (marks)           | Assignment requirement                                                 | Assignment ref | Full-credit evidence I’d expect                          | Prompt coverage | Status  |
| ------------------------------- | ---------------------------------------------------------------------- | -------------- | -------------------------------------------------------- | --------------- | ------- |
| Monitoring & logging (4)        | Request/response logging (no sensitive); track request count + latency |                | `/metrics` or counters; Grafana dashboard JSON committed | Part 10         | **Met** |
| Post-deploy perf tracking (3)   | Batch of real/simulated requests + true labels                         |                | Script produces CSV + summarized metrics                 | Part 10         | **Met** |
| Deliverables package + demo (3) | Zip of code+configs+model artifacts; <5 min screen recording           |                | `make_submission_zip.sh`; written demo script            | Part 10         | **Met** |
