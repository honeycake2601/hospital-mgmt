# Hospital Management System – DevOps Mini-Project Report

**Team members:** (names / roll numbers)
**Course / Institution:** (fill in)
**Repository:** https://github.com/honeycake2601/hospital-mgmt
**Live URL (Render):** https://hms-app.onrender.com  *(replace with your URL)*

> **Platform note:** The guidelines suggest Google Cloud. Because Google Cloud requires a payment card, this project uses an equivalent free stack: GitHub Container Registry (in place of Artifact Registry), Render (in place of Cloud Run) and Render Logs/Metrics + UptimeRobot (in place of Cloud Monitoring/Logging). The DevOps workflow is the same.

---

## 1. Introduction / Project Description
The Hospital Management System (HMS) is a small web application for registering patients, adding doctors and booking appointments. The project demonstrates a complete DevOps lifecycle: source control, automated testing, containerization, a CI/CD pipeline, cloud deployment, and monitoring with basic SRE practices.

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
| Registry | GitHub Container Registry (GHCR) |
| Deployment | Render (Docker web service) |
| Monitoring | Render Logs & Metrics, UptimeRobot |

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
                                   GitHub Container Registry (GHCR)
                                                │ (image :commit-sha, :latest)
                                   Deploy Hook ──▼
 User ──HTTPS──▶  Render Web Service  (hms-app: Flask + Gunicorn + SQLite)
                         │
                         ├── stdout JSON logs ──▶ Render Logs
                         ├── CPU/memory/HTTP ───▶ Render Metrics
                         └── GET /health ◀────── Render health check + UptimeRobot (alerts)
```
**Components**
- **Flask app** – REST API (`/api/patients`, `/api/doctors`, `/api/appointments`, `/api/stats`), web UI at `/`, health endpoint `/health`.
- **SQLite** – embedded database. *Limitation:* the container filesystem is temporary, so data resets on restart/redeploy. A production system would use a managed database.
- **GitHub Actions** – runs the CI/CD workflow.
- **GHCR** – stores versioned Docker images.
- **Render** – hosts the container with HTTPS and automatic restarts.
- **UptimeRobot** – external monitor that checks `/health` and sends email alerts.

> 📸 *Screenshot: architecture diagram (draw it in draw.io and insert here).*

## 8. DevOps Implementation

### 8.1 Develop
Single Flask module (`app.py`) with a minimal HTML/JS front end. Design choices that support DevOps:
- `create_app()` factory so tests use an isolated database.
- `/health` endpoint that verifies database access (returns **200** or **503**).
- Structured JSON logs with a `severity` field.
- Configuration through environment variables (`PORT`, `DB_PATH`).

```bash
pip install -r requirements.txt
python app.py        # http://localhost:8080
```
> 📸 *Screenshot: app running locally with sample data.*

### 8.2 Git/GitHub
```bash
git init
git add .
git commit -m "Initial commit: hospital management app"
git branch -M main
git remote add origin https://github.com/honeycake2601/hospital-mgmt.git
git push -u origin main
```
Changes are committed with meaningful messages to `main`; the pipeline runs on every push and pull request.
> 📸 *Screenshot: GitHub repo page and commit history.*

### 8.3 Build and Testing
`pytest` runs 7 unit tests: health check (healthy and unhealthy DB), patient creation/validation, doctor and appointment flow, referential validation (unknown patient → 404), and stats. `pytest.ini` sets the import path so tests run the same locally and in CI.
```bash
pytest -v
```
> 📸 *Screenshot: pytest output showing 7 passed.*

### 8.4 Docker
Slim Python base image, dependencies installed first (layer caching), non-root user, served by Gunicorn on `$PORT`.
```bash
docker build -t hms-app .
docker run -p 8080:8080 hms-app
curl localhost:8080/health
```
> 📸 *Screenshot: `docker build`, `docker images`, running container.*

### 8.5 Package/Register (GitHub Container Registry)
The pipeline logs in to `ghcr.io` with the built-in `GITHUB_TOKEN` and pushes `ghcr.io/honeycake2601/hospital-mgmt:<commit-sha>` and `:latest`. SHA tags give traceability and easy rollback. The package is set to **Public** so Render can pull it without credentials.
> 📸 *Screenshot: repo → Packages → hospital-mgmt showing the tags.*

### 8.6 Continuous Integration
File `.github/workflows/ci-cd.yml`, job **test**: checkout → Python 3.12 → install dependencies → pytest. Runs on every push and pull request; a failing test blocks the deploy job.

*Real issue caught by CI:* the first run failed (exit code 2) because plain `pytest` could not import `app` from the `tests` folder, although it worked locally with `python -m pytest`. Fixed by adding `pytest.ini` (`pythonpath = .`); the next run passed.
> 📸 *Screenshot: failed run, then the green run.*

### 8.7 Cloud Deployment (Render)
1. Render Dashboard → **New → Web Service → Existing image**.
2. Image URL: `ghcr.io/honeycake2601/hospital-mgmt:latest`; Instance type **Free**; Name `hms-app`.
3. Settings → **Health Check Path** = `/health`.
4. Settings → copy the **Deploy Hook** URL and store it as the GitHub secret `RENDER_DEPLOY_HOOK`.
> 📸 *Screenshot: Render service page (URL, status Live, image) and the app in the browser.*

### 8.8 Continuous Delivery
On every push to `main`, after tests pass, the **deploy** job builds and pushes the image to GHCR and then calls the Render deploy hook. Render pulls the new image, starts it, waits for `/health` to pass and only then switches traffic, so a broken release does not replace a working one. Previous deploys remain in Render's history for rollback.
> 📸 *Screenshot: pipeline (test → deploy green) and Render "Events/Deploys" list.*

## 9. Monitoring and SRE Practices

### 9.1 Logging
The app writes JSON logs to stdout, and Render shows them in the service's **Logs** tab. Each request is logged (`GET /api/patients -> 200 (3.2 ms)`), and errors are logged with severity `ERROR`.
> 📸 *Screenshot: Render Logs with request lines and an ERROR entry.*

### 9.2 Monitoring
- **Render Metrics tab:** CPU, memory, HTTP request counts and latency.
- **UptimeRobot:** HTTP(s) monitor on `https://<url>/health` (free plan: checks every 5 minutes) with email alerts on downtime.
> 📸 *Screenshot: Render Metrics; UptimeRobot dashboard.*

### 9.3 Two SRE practices implemented
1. **Health checking and alerting.** `/health` verifies database connectivity and returns 503 on failure. Render uses it for deploy health checks and automatic restart; UptimeRobot polls it externally and emails the team when it fails.
2. **Error detection with an SLO.** Errors are logged at `ERROR` severity and searchable in Render Logs. A simple SLO is defined: **99% of requests succeed (non-5xx) over 30 days** (error budget 1%), observed from the Metrics tab and UptimeRobot uptime percentage.
> 📸 *Screenshot: UptimeRobot alert contact and monitor; Render health check setting.*

### 9.4 How health/reliability was observed
Through the UptimeRobot uptime % and response times, Render's metrics (latency, HTTP status), and Render Logs (error details). Generate traffic with:
```bash
curl https://<url>/api/stats
```

## 10. Failure and Recovery
**Scenario:** a bad configuration points the database to an unwritable path.

| Stage | What happened |
|---|---|
| **Failure** | In Render → Environment, added `DB_PATH=/nonexistent/hospital.db` and saved. The service restarted; every API call returned **500** and `/health` returned **503**. |
| **Detection** | UptimeRobot marked the monitor **Down** and emailed an alert. |
| **Diagnosis** | Render Logs showed `Health check failed: OperationalError('unable to open database file')` → a configuration problem, not a code bug. The Environment tab showed the bad variable. |
| **Fix** | Deleted the `DB_PATH` variable (or rolled back to the previous deploy from the Events tab). |
| **Redeployment** | Render redeployed automatically. For a code-level fix, a `git commit` + `git push` triggers the full pipeline. |
| **Recovery** | `/health` returned 200 again, UptimeRobot showed **Up**, error logs stopped. Downtime ≈ X minutes (fill in from the UptimeRobot log). |

> 📸 *Screenshots: (1) 503 on /health, (2) UptimeRobot Down alert, (3) error log, (4) removing the variable, (5) monitor back Up.*

## 11. Results
- A working hospital management web app deployed on Render with a public HTTPS URL.
- 7/7 automated tests passing in CI; CI caught and helped fix a real import-path issue.
- Fully automated pipeline: push → test → build → registry → deploy.
- Immutable, SHA-tagged images in GHCR enabling rollback.
- Logs, metrics, health checks and alerting operational; one failure injected, detected, diagnosed and recovered.

**Limitations / future work:** persistent managed database, authentication/roles, staging environment, infrastructure-as-code, and a cloud-native stack (e.g., Google Cloud Run + Artifact Registry + Cloud Monitoring) when a paid or credit-backed account is available.

## 12. Conclusion
The project demonstrates an end-to-end DevOps workflow for a simple application and shows how automation and observability shorten the time to detect and recover from failures.

## Appendix A – Execution Instructions
1. `git clone https://github.com/honeycake2601/hospital-mgmt && cd hospital-mgmt`
2. `pip install -r requirements.txt && pytest && python app.py`
3. Push to `main` → GitHub Actions builds and pushes the image to GHCR.
4. Set the GHCR package to Public; create the Render web service from the image; add `RENDER_DEPLOY_HOOK` as a GitHub secret.
5. Add the UptimeRobot monitor on `/health`.
6. Run the failure demo from section 10.

## Appendix B – Repository Structure
```
hospital-mgmt/
├── app.py
├── requirements.txt
├── pytest.ini
├── Dockerfile
├── tests/test_app.py
├── .github/workflows/ci-cd.yml
└── REPORT.md
```
