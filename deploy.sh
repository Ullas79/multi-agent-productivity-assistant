#!/bin/bash
# deploy.sh - Builds and deploys the AgentFlow app to Google Cloud Run

set -e

# Default settings
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
SERVICE_NAME="agentflow-app"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
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

echo "2. Building Docker Image via Cloud Build..."
# This builds the image securely in the cloud 
gcloud builds submit --tag $IMAGE_NAME --project=$PROJECT_ID

echo "3. Deploying to Cloud Run..."
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
    --set-env-vars="ALLOYDB_INSTANCE=$ALLOYDB_INSTANCE,GOOGLE_API_KEY=${GOOGLE_API_KEY:-YOUR_API_KEY_HERE}" \
    --project=$PROJECT_ID

echo "✅ App Deployment Complete!"
echo "You can check your live app using the URL above."
