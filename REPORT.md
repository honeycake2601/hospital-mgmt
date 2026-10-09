# Hospital Management System – DevOps Mini-Project Report

**Team members:** (names / roll numbers)
**Course / Institution:** (fill in)
**Repository:** https://github.com/<your-username>/hospital-mgmt
**Live URL (Cloud Run):** https://hms-app-xxxxx-el.a.run.app

---

## 1. Introduction / Project Description
The Hospital Management System (HMS) is a small web application that lets hospital staff register patients, add doctors and book appointments. The project's main purpose is to demonstrate a complete DevOps lifecycle: source control, automated testing, containerization, a CI/CD pipeline, deployment on Google Cloud Run, and monitoring with basic SRE practices.

**Functional features**
- Register and list patients
- Add and list doctors
- Book appointments (validates that the patient and doctor exist)
- Dashboard counters and a `/health` endpoint

## 6. Technologies and Tools Used
| Category | Technology |
|---|---|
| Programming | Python 3.12, Flask, Gunicorn, SQLite |
| Source Control | Git / GitHub |
| Testing | pytest |
| Containerization | Docker |
| CI/CD | GitHub Actions |
| Registry | Google Artifact Registry |
| Deployment | Google Cloud Run |
| Monitoring | Google Cloud Monitoring / Logging |

## 7. Application Architecture
```
 Developer ──push──▶ GitHub Repo ──trigger──▶ GitHub Actions
                                                │
                                   ┌────────────┴─────────────┐
                                   │ CI: install deps + pytest │
                                   └────────────┬─────────────┘
                                                │ (tests pass, main branch)
                                   ┌────────────▼─────────────┐
                                   │ CD: docker build + push   │
                                   └────────────┬─────────────┘
                                                ▼
                                   Google Artifact Registry
                                                │ (image :commit-sha)
                                                ▼
 User ──HTTPS──▶  Google Cloud Run  (hms-app: Flask + Gunicorn + SQLite)
                         │
                         ├──stdout JSON logs──▶ Cloud Logging ──▶ Log-based metric
                         └──────────────────────▶ Cloud Monitoring (uptime check /health, alerts)
```
**Components**
- **Flask app** – REST API (`/api/patients`, `/api/doctors`, `/api/appointments`, `/api/stats`), web UI at `/`, health endpoint `/health`.
- **SQLite** – lightweight embedded DB (file in `/tmp`). *Limitation:* Cloud Run is stateless, so data resets when an instance restarts. In production this would be Cloud SQL / Firestore.
- **GitHub Actions** – runs the CI/CD workflow.
- **Artifact Registry** – stores versioned Docker images.
- **Cloud Run** – serverless container hosting with HTTPS and autoscaling.
- **Cloud Logging / Monitoring** – logs, uptime checks, alerts.

> 📸 *Screenshot: architecture diagram (draw it in draw.io / Lucid and insert here).*

## 8. DevOps Implementation

### 8.1 Develop
The application is a single Flask module (`app.py`) with a minimal HTML/JS front end. Key design choices that support DevOps:
- `create_app()` factory so tests can use an isolated database.
- `/health` endpoint that actually verifies database access (returns **200** or **503**).
- Structured JSON logging with a `severity` field so Cloud Logging classifies entries correctly.
- Configuration through environment variables (`PORT`, `DB_PATH`) – twelve-factor style.

Run locally:
```bash
pip install -r requirements.txt
python app.py        # http://localhost:8080
```
> 📸 *Screenshot: app running locally / UI with sample data.*

### 8.2 Git / GitHub
```bash
git init
git add .
git commit -m "Initial commit: hospital management app"
git branch -M main
git remote add origin https://github.com/<user>/hospital-mgmt.git
git push -u origin main
```
Workflow used: feature changes committed with meaningful messages and pushed to `main`; the pipeline runs on every push and pull request.
> 📸 *Screenshot: GitHub repo page and commit history.*

### 8.3 Build and Testing
`pytest` runs 7 unit tests covering: health check (healthy and unhealthy DB), patient creation/validation, doctor and appointment flow, referential validation (unknown patient → 404), and stats.
```bash
pytest -v
```
> 📸 *Screenshot: pytest output showing 7 passed.*

### 8.4 Docker
`Dockerfile`: slim Python base image, dependencies installed first (layer caching), runs as a **non-root user**, served by Gunicorn on `$PORT`.
```bash
docker build -t hms-app .
docker run -p 8080:8080 hms-app
curl localhost:8080/health
```
> 📸 *Screenshot: `docker build`, `docker images`, container running.*

### 8.5 Package / Register (Artifact Registry)
Created by `scripts/gcp-setup.sh`:
```bash
gcloud artifacts repositories create hms-repo --repository-format=docker --location=asia-south1
```
The pipeline pushes `…/hms-repo/hms-app:<commit-sha>` and `:latest`. Tagging with the commit SHA gives traceability and easy rollback.
> 📸 *Screenshot: Artifact Registry showing the image and its tags.*

### 8.6 Continuous Integration
File: `.github/workflows/ci-cd.yml`, job **test**: checkout → set up Python 3.12 → install dependencies → run pytest. It runs on every push and pull request; a failing test blocks the deploy job.
> 📸 *Screenshot: GitHub Actions run – green test job.*

### 8.7 Google Cloud Deployment
One-time setup: `scripts/gcp-setup.sh` (enables APIs, creates the registry, creates the deploy service account and key). The first deployment (and all later ones) is done by the pipeline using `google-github-actions/deploy-cloudrun`, with `--allow-unauthenticated` so the app is reachable publicly.

GitHub repository secrets required: `GCP_PROJECT_ID`, `GCP_SA_KEY`.
> 📸 *Screenshot: Cloud Run service page (URL, revision, region) and the app open in the browser.*

### 8.8 Continuous Delivery
On every push to `main`, after tests pass, the **deploy** job automatically: authenticates to GCP → builds the image → pushes it to Artifact Registry → deploys a new Cloud Run revision. Cloud Run only routes traffic to the new revision after it passes its startup check, and old revisions are retained so rollback is a one-click operation.
> 📸 *Screenshot: full pipeline (test → deploy) green, and Cloud Run "Revisions" tab.*

## 9. Monitoring and SRE Practices

### 9.1 Google Cloud Logging
The app writes JSON logs to stdout; Cloud Run forwards them to Cloud Logging. Each request is logged (`GET /api/patients -> 200 (3.2 ms)`), and errors are logged with severity `ERROR`.
Useful query (Logs Explorer):
```
resource.type="cloud_run_revision" AND resource.labels.service_name="hms-app" AND severity>=ERROR
```
> 📸 *Screenshot: Logs Explorer with request logs and an ERROR entry.*

### 9.2 Google Cloud Monitoring
- **Cloud Run built-in metrics** dashboard: request count, latency, container instance count, 5xx rate.
- **Uptime check** on `/health` every 1 minute (created by `scripts/monitoring-setup.sh`).
- **Log-based metric** `hms_app_errors` counting ERROR logs.
> 📸 *Screenshot: Cloud Run Metrics tab; Uptime check status.*

### 9.3 Two SRE practices implemented
1. **Health checking + alerting.** `/health` verifies DB connectivity and returns 503 if it fails. An uptime check polls it every minute, and an alert policy (Console → Monitoring → Alerting → Create policy → *Uptime check* `hms-health-check` fails for 2 minutes) emails the team.
2. **Error detection with SLO thinking.** The log-based metric `hms_app_errors` has an alert (threshold: > 3 errors in 5 minutes). We also defined a simple SLO: **99% of requests succeed (non-5xx) over 30 days** (error budget = 1%), observed via the Cloud Run request-count metric split by response-code class.

*(Optional third: Cloud Run `--max-instances=2` limits blast radius/cost; revisions allow instant rollback.)*
> 📸 *Screenshot: alert policies list; the log-based metric chart.*

### 9.4 How health/reliability was observed
Through the uptime-check dashboard (availability %, latency), Cloud Run metrics (5xx ratio, request latency), and Logs Explorer (error details). Generate traffic with:
```bash
for i in $(seq 1 50); do curl -s https://<URL>/api/stats > /dev/null; done
```

## 10. Failure and Recovery
**Scenario:** a bad configuration is deployed that points the database to an unwritable path.

| Stage | What happened |
|---|---|
| **Failure** | Deployed a revision with env var `DB_PATH=/nonexistent/hospital.db`:<br>`gcloud run services update hms-app --region asia-south1 --set-env-vars DB_PATH=/nonexistent/hospital.db`<br>The container starts, but every API call returns **500** and `/health` returns **503**. |
| **Detection** | The uptime check `hms-health-check` failed and the alert policy sent an email; the `hms_app_errors` alert also fired. |
| **Diagnosis** | Logs Explorer (`severity>=ERROR`) showed `Health check failed: OperationalError('unable to open database file')` → configuration problem, not a code bug. Cloud Run → Revisions showed the new env var on the latest revision. |
| **Fix** | Restored the correct configuration (remove the bad variable):<br>`gcloud run services update hms-app --region asia-south1 --remove-env-vars DB_PATH`<br>(Alternative: route 100% traffic back to the previous revision from the Revisions tab.) |
| **Redeployment** | Cloud Run created a new healthy revision; for a code-level fix, a `git commit` + `git push` triggers the pipeline automatically. |
| **Recovery** | `/health` returned 200, the uptime check turned green, the alert auto-closed; error logs stopped. Total downtime ≈ X minutes (fill in from the incident timeline). |

> 📸 *Screenshots: (1) 503 response, (2) alert email/incident, (3) error log, (4) fix command, (5) uptime check recovered.*

## 11. Results
- A working hospital management web app deployed on Cloud Run with a public HTTPS URL.
- 7/7 automated tests passing in CI.
- Fully automated pipeline: push → test → build → registry → deploy (≈ 3–5 minutes).
- Immutable, SHA-tagged images in Artifact Registry enabling rollback.
- Logs, metrics, uptime check and alerts operational; one failure injected, detected, diagnosed and recovered.

**Limitations / future work:** persistent database (Cloud SQL), authentication/roles, Workload Identity Federation instead of a service-account key, staging environment, Terraform for infrastructure.

## 12. Conclusion
The project shows an end-to-end DevOps workflow on GCP for a simple application and illustrates how automation and observability shorten the time to detect and recover from failures.

## Appendix A – Execution Instructions
1. **Clone & run locally**
   ```bash
   git clone https://github.com/<user>/hospital-mgmt && cd hospital-mgmt
   pip install -r requirements.txt && pytest && python app.py
   ```
2. **GCP setup (Cloud Shell):** edit `PROJECT_ID` in `scripts/gcp-setup.sh`, then `bash scripts/gcp-setup.sh`.
3. **GitHub secrets:** add `GCP_PROJECT_ID` and `GCP_SA_KEY` (contents of `key.json`; then delete the key file).
4. **Deploy:** `git push origin main` → watch the *Actions* tab → open the Cloud Run URL.
5. **Monitoring:** edit and run `scripts/monitoring-setup.sh`, then create the two alert policies (section 9.3).
6. **Failure demo:** follow section 10.

## Appendix B – Repository Structure
```
hospital-mgmt/
├── app.py
├── requirements.txt
├── Dockerfile
├── tests/test_app.py
├── .github/workflows/ci-cd.yml
├── scripts/gcp-setup.sh
├── scripts/monitoring-setup.sh
└── REPORT.md
```
