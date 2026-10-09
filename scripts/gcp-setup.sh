#!/usr/bin/env bash
# One-time GCP setup. Run in Cloud Shell. Edit PROJECT_ID first.
set -e
PROJECT_ID="your-project-id"
REGION="asia-south1"
REPO="hms-repo"
SA="github-deployer"

gcloud config set project $PROJECT_ID

# 1. Enable APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  monitoring.googleapis.com logging.googleapis.com iam.googleapis.com

# 2. Artifact Registry (Docker)
gcloud artifacts repositories create $REPO --repository-format=docker \
  --location=$REGION --description="Hospital Mgmt images"

# 3. Service account for GitHub Actions
gcloud iam service-accounts create $SA --display-name="GitHub Actions deployer"
SA_EMAIL="$SA@$PROJECT_ID.iam.gserviceaccount.com"
for ROLE in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" --role="$ROLE"
done

# 4. Key -> paste the file content into GitHub secret GCP_SA_KEY, then delete it
gcloud iam service-accounts keys create key.json --iam-account=$SA_EMAIL
echo "Add GitHub secrets: GCP_PROJECT_ID=$PROJECT_ID and GCP_SA_KEY=(contents of key.json)"
