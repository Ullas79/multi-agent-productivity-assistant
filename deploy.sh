#!/bin/bash
# deploy.sh - Builds and deploys the AgentFlow app to Google Cloud Run

set -e

# Default settings
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
SERVICE_NAME="agentflow"
REPO_NAME="agentflow-repo"
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME"
NETWORK="default"
CLUSTER_ID="my-alloydb-cluster"
INSTANCE_ID="my-primary-instance"

# Database Connection String
ALLOYDB_INSTANCE="projects/$PROJECT_ID/locations/$REGION/clusters/$CLUSTER_ID/instances/$INSTANCE_ID"

# Try to load secrets from .env if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "🚀 Deploying to Cloud Run in project: $PROJECT_ID ($REGION)"

echo "1. Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project=$PROJECT_ID

echo "2. Setting up Artifact Registry..."
# Create the repo if it doesn't already exist
gcloud artifacts repositories create $REPO_NAME \
    --repository-format=docker \
    --location=$REGION \
    --description="Docker repository for AgentFlow" \
    --project=$PROJECT_ID || true

echo "3. Building Docker Image via Cloud Build..."
# This builds the image securely in the cloud 
gcloud builds submit --tag $IMAGE_NAME --project=$PROJECT_ID

echo "4. Granting permissions to default compute service account..."
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/aiplatform.user" > /dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/alloydb.client" > /dev/null

echo "5. Deploying to Cloud Run..."
# Notes: 
# - We expose port 8080 (where Streamlit runs).
# - We pass the ALLOYDB connection string directly natively.
# - To connect to AlloyDB seamlessly, we use Direct VPC Egress (--network=$NETWORK).
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --region $REGION \
    --port 8080 \
    --allow-unauthenticated \
    --network $NETWORK \
    --subnet default \
    --vpc-egress private-ranges-only \
    --set-env-vars="ALLOYDB_INSTANCE=$ALLOYDB_INSTANCE,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_REGION=$REGION,DB_USER=postgres,DB_PASSWORD=SuperSecretPassword123\!,ALLOYDB_IAM_AUTH=False" \
    --project=$PROJECT_ID

echo "✅ App Deployment Complete!"
echo "You can check your live app using the URL above."
