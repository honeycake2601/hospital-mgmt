#!/usr/bin/env bash
# Run AFTER the first deployment. Edit SERVICE_HOST (Cloud Run URL without https://).
set -e
PROJECT_ID="your-project-id"
SERVICE_HOST="hms-app-xxxxx-el.a.run.app"

# Uptime check on /health (SRE practice 1: health checking)
gcloud monitoring uptime create hms-health-check \
  --resource-type=uptime-url \
  --resource-labels=host=$SERVICE_HOST,project_id=$PROJECT_ID \
  --protocol=https --path=/health --period=1 --project=$PROJECT_ID

# Log-based metric counting application errors (SRE practice 2: error detection)
gcloud logging metrics create hms_app_errors \
  --description="HMS application ERROR logs" \
  --log-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="hms-app" AND severity>=ERROR'

echo "Now create alert policies in Console > Monitoring > Alerting (see REPORT.md section 9)."
